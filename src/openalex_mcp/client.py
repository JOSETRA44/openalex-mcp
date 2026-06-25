"""Async HTTP client for the OpenAlex API with TTL caching and rate limiting."""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

from .config import OpenAlexSettings
from .exceptions import (
    OpenAlexAPIError,
    OpenAlexAuthError,
    OpenAlexNotFoundError,
    OpenAlexRateLimitError,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openalex.org"


class _TTLCache:
    """In-memory cache with per-entry expiry."""

    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._store: dict[str, tuple[Any, datetime]] = {}

    def get(self, key: str) -> Any | None:
        if key not in self._store:
            return None
        value, expires_at = self._store[key]
        if datetime.utcnow() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if self._ttl.total_seconds() > 0:
            self._store[key] = (value, datetime.utcnow() + self._ttl)

    def clear(self) -> None:
        self._store.clear()


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

    async def wait_if_needed(self) -> None:
        if self.remaining is not None and self.remaining <= 0 and self.reset_at:
            wait = max(0.0, self.reset_at - time.time()) + 0.5
            logger.warning("Rate limit reached. Sleeping %.1fs until reset.", wait)
            await asyncio.sleep(wait)


class OpenAlexClient:
    """Async client for the OpenAlex REST API."""

    def __init__(self, settings: OpenAlexSettings) -> None:
        self._settings = settings
        self._cache = _TTLCache(settings.cache_ttl)
        self._rl = _RateLimitState()
        self._http: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "OpenAlexClient":
        self._http = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=30.0,
            headers={"User-Agent": "openalex-mcp/0.1.0 (https://github.com/JOSETRA44/openalex-mcp)"},
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

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
    def _cache_key(path: str, params: dict) -> str:
        # Exclude auth params from the cache key so they don't leak
        safe = {k: v for k, v in params.items() if k not in ("api_key", "mailto")}
        raw = f"{path}?{urlencode(sorted(safe.items()))}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def request(self, path: str, params: dict | None = None) -> dict:
        """Execute a GET request against the OpenAlex API."""
        assert self._http is not None, "Client must be used as async context manager"

        params = {k: v for k, v in (params or {}).items() if v is not None}
        cache_key = self._cache_key(path, params)

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache hit: %s", path)
            return cached

        await self._rl.wait_if_needed()

        full_params = {**params, **self._auth_params()}

        for attempt in range(self._settings.max_retries + 1):
            try:
                resp = await self._http.get(path, params=full_params)
            except httpx.TimeoutException:
                raise OpenAlexAPIError("Request timed out after 30s")
            except httpx.RequestError as exc:
                raise OpenAlexAPIError(f"Network error: {exc}") from exc

            self._rl.update(resp.headers)

            if resp.status_code == 200:
                data = resp.json()
                self._cache.set(cache_key, data)
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
