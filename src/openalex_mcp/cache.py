"""Pluggable cache backends for the OpenAlex client.

The MCP server is a long-lived process, so an in-memory dict is all it needs.
The CLI is the opposite: a fresh process per invocation, so an in-memory cache
would never see a single hit. Hence the disk backend — it is what makes a
repeated research query (or a re-run of a failed harvest) instant.

Both backends satisfy the same ``CacheBackend`` protocol, so ``OpenAlexClient``
neither knows nor cares which one it was handed.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import platformdirs

APP_NAME = "openalex-mcp"


@runtime_checkable
class CacheBackend(Protocol):
    """Minimal contract every cache backend must satisfy."""

    def get(self, key: str) -> Any | None:
        """Return the cached value for ``key``, or ``None`` if missing/expired."""
        ...

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Store ``value`` under ``key`` for ``ttl`` seconds (no-op if ttl <= 0)."""
        ...


class MemoryCache:
    """In-process cache. Fast, ephemeral — used by the long-lived MCP server."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry and time.time() < entry["expires"]:
            return entry["body"]
        return None

    def set(self, key: str, value: Any, ttl: int) -> None:
        if ttl > 0:
            self._store[key] = {"body": value, "expires": time.time() + ttl}

    def clear(self) -> None:
        self._store.clear()


class NullCache:
    """Backend for ``--no-cache``: reads nothing, writes nothing."""

    def get(self, key: str) -> Any | None:
        return None

    def set(self, key: str, value: Any, ttl: int) -> None:
        return None


class DiskCache:
    """Filesystem cache. Persists between processes — used by the CLI.

    One small JSON file per entry, named by the SHA-256 of its key. The record
    carries provenance (``fetched_at``, ``status``) alongside the body so that
    ``cache stats`` can report on it without re-deriving anything, and so a
    human poking at the cache directory can tell what a file holds.
    """

    def __init__(self, cache_dir: str | Path) -> None:
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    @property
    def directory(self) -> Path:
        return self._dir

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self._dir / f"{digest}.json"

    def get(self, key: str) -> Any | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if time.time() >= entry.get("expires", 0):
            # Expired — clean it up opportunistically so stats stay honest.
            path.unlink(missing_ok=True)
            return None
        return entry.get("body")

    def set(self, key: str, value: Any, ttl: int) -> None:
        if ttl <= 0:
            return
        now = time.time()
        entry = {
            "fetched_at": _iso(now),
            "expires_at": _iso(now + ttl),
            "expires": now + ttl,
            "status": 200,
            "body": value,
        }
        try:
            self._path(key).write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
        except (OSError, TypeError):
            # Caching is best-effort; never let a cache write break a query.
            pass


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cache_dir() -> Path:
    """Per-user cache directory for this project (XDG / AppData / ~/Library)."""
    # appauthor=False keeps Windows from nesting <app>/<app>/Cache.
    return Path(platformdirs.user_cache_dir(APP_NAME, appauthor=False))


def build_cache(backend: str, directory: str | Path | None = None) -> CacheBackend:
    """Factory: return the cache backend named by ``backend``."""
    if backend == "disk":
        return DiskCache(directory or cache_dir())
    if backend == "none":
        return NullCache()
    return MemoryCache()


def cache_stats(directory: str | Path | None = None) -> dict[str, Any]:
    """Summarize the disk cache: entry counts, bytes on disk, oldest/newest."""
    path = Path(directory or cache_dir())
    entries = sorted(path.glob("*.json")) if path.exists() else []
    now = time.time()
    live = expired = 0
    size = 0
    oldest: float | None = None
    newest: float | None = None
    for f in entries:
        try:
            size += f.stat().st_size
            record = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        expires = record.get("expires", 0)
        if now < expires:
            live += 1
        else:
            expired += 1
        mtime = f.stat().st_mtime
        oldest = mtime if oldest is None else min(oldest, mtime)
        newest = mtime if newest is None else max(newest, mtime)
    return {
        "path": str(path),
        "exists": path.exists(),
        "entries": live + expired,
        "live": live,
        "expired": expired,
        "size_bytes": size,
        "oldest": _iso(oldest) if oldest else None,
        "newest": _iso(newest) if newest else None,
    }


def cache_clear(directory: str | Path | None = None) -> dict[str, Any]:
    """Delete every cached entry; returns how many files were removed."""
    path = Path(directory or cache_dir())
    if not path.exists():
        return {"path": str(path), "removed": 0}
    removed = len(list(path.glob("*.json")))
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    return {"path": str(path), "removed": removed}
