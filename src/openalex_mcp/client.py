"""Async HTTP client for the OpenAlex API with pluggable caching and rate limiting."""

import asyncio
import hashlib
import logging
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from .cache import CacheBackend, MemoryCache
from .config import OpenAlexSettings
from .exceptions import (
    OpenAlexAPIError,
    OpenAlexAuthError,
    OpenAlexNetworkError,
    OpenAlexNotFoundError,
    OpenAlexRateLimitError,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openalex.org"

# Query params that identify the caller. They must never reach the cache key
# (two users sharing a machine would otherwise get separate cache entries for
# identical questions) and must never be written into a cache file.
_AUTH_PARAMS = ("api_key", "mailto")


class _RateLimitState:
    """Tracks the current API rate-limit window from response headers."""

    def __init__(self) -> None:
        self.limit: int | None = None
        self.remaining: int | None = None
        self.reset_at: float | None = None  # Unix timestamp

    def update(self, headers: httpx.Headers) -> None:
        try:
            if "X-Rate-Limit-Limit" in headers:
                self.limit = int(headers["X-Rate-Limit-Limit"])
            if "X-Rate-Limit-Remaining" in headers:
                self.remaining = int(headers["X-Rate-Limit-Remaining"])
            if "X-Rate-Limit-Reset" in headers:
                self.reset_at = float(headers["X-Rate-Limit-Reset"])
        except (ValueError, KeyError):
            pass

    def as_meta(self) -> dict[str, Any]:
        """Rate-limit facts worth surfacing in the CLI's ``meta`` block."""
        return {
            k: v
            for k, v in {
                "rate_limit": self.limit,
                "rate_limit_remaining": self.remaining,
            }.items()
            if v is not None
        }

    async def wait_if_needed(self) -> None:
        if self.remaining is not None and self.remaining <= 0 and self.reset_at:
            wait = max(0.0, self.reset_at - time.time()) + 0.5
            logger.warning("Rate limit reached. Sleeping %.1fs until reset.", wait)
            await asyncio.sleep(wait)


class OpenAlexClient:
    """Async client for the OpenAlex REST API.

    ``cache`` defaults to an in-memory backend (right for the MCP server); the
    CLI hands in a DiskCache so results survive process exit. ``refresh``
    bypasses reads while still writing, which is what ``--refresh`` means.
    """

    def __init__(
        self,
        settings: OpenAlexSettings,
        cache: CacheBackend | None = None,
        refresh: bool = False,
        transport: httpx.BaseTransport | httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._cache: CacheBackend = cache if cache is not None else MemoryCache()
        self._refresh = refresh
        self._transport = transport
        self._rl = _RateLimitState()
        self._http: httpx.AsyncClient | None = None
        # True when the most recent request() was served from cache. The CLI
        # reports this as `cached` in the JSON envelope.
        self.last_cached: bool = False
        self.any_cached: bool = False

    async def __aenter__(self) -> "OpenAlexClient":
        self._http = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=30.0,
            transport=self._transport,
            headers={"User-Agent": "openalex-mcp/0.2.0 (https://github.com/JOSETRA44/openalex-mcp)"},
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    @property
    def rate_limit_meta(self) -> dict[str, Any]:
        return self._rl.as_meta()

    def _auth_params(self) -> dict[str, str]:
        """Return the auth query parameter(s) for this request."""
        params: dict[str, str] = {}
        if self._settings.api_key:
            params["api_key"] = self._settings.api_key
        elif self._settings.email:
            # Polite pool: identified by email (slower but no key needed)
            params["mailto"] = self._settings.email
        return params

    @staticmethod
    def _cache_key(path: str, params: dict, method: str = "GET") -> str:
        safe = {k: v for k, v in params.items() if k not in _AUTH_PARAMS}
        raw = f"{method} {BASE_URL}{path}?{urlencode(sorted(safe.items()))}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def request(self, path: str, params: dict | None = None) -> dict:
        """Execute a GET request against the OpenAlex API."""
        assert self._http is not None, "Client must be used as async context manager"

        params = {k: v for k, v in (params or {}).items() if v is not None}
        cache_key = self._cache_key(path, params)

        self.last_cached = False
        if not self._refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit: %s", path)
                self.last_cached = True
                self.any_cached = True
                return cached

        await self._rl.wait_if_needed()

        full_params = {**params, **self._auth_params()}

        for attempt in range(self._settings.max_retries + 1):
            try:
                resp = await self._http.get(path, params=full_params)
            except httpx.TimeoutException as exc:
                raise OpenAlexNetworkError("Request timed out after 30s") from exc
            except httpx.RequestError as exc:
                raise OpenAlexNetworkError(f"Network error: {exc}") from exc

            self._rl.update(resp.headers)

            if resp.status_code == 200:
                data = resp.json()
                # Only 2xx bodies are cached — never an auth failure or an error.
                self._cache.set(cache_key, data, self._settings.cache_ttl)
                return data

            if resp.status_code == 401:
                raise OpenAlexAuthError(
                    "OpenAlex authentication failed (401). Check your OPENALEX_API_KEY.",
                    status_code=401,
                )
            if resp.status_code == 403:
                raise OpenAlexAuthError(
                    "OpenAlex access forbidden (403). Verify your API key has access to this endpoint.",
                    status_code=403,
                )
            if resp.status_code == 404:
                raise OpenAlexNotFoundError(
                    f"Not found in OpenAlex: {path}",
                    status_code=404,
                )
            if resp.status_code == 429:
                if attempt < self._settings.max_retries:
                    retry_after = float(resp.headers.get("Retry-After", 2 ** attempt))
                    logger.warning("429 rate limit (attempt %d). Waiting %.1fs.", attempt + 1, retry_after)
                    await asyncio.sleep(retry_after)
                    continue
                raise OpenAlexRateLimitError(
                    "OpenAlex rate limit exceeded after all retries.",
                    status_code=429,
                )

            # Try to surface OpenAlex error message
            try:
                detail = resp.json().get("error", resp.text[:200])
            except Exception:
                detail = resp.text[:200]
            raise OpenAlexAPIError(
                f"OpenAlex API error {resp.status_code}: {detail}",
                status_code=resp.status_code,
            )

        raise OpenAlexRateLimitError("OpenAlex rate limit exceeded after all retries.", status_code=429)
