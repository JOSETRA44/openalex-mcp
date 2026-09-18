"""Persistent-cache behaviour (ARSENAL-SPEC §3 and §6.4).

Every test here runs against a `DiskCache` rooted in `tmp_path` and an
`httpx.MockTransport`: the developer's real `platformdirs` cache directory is
never read, written, or even created.
"""

from __future__ import annotations

import argparse
import importlib
import time

import pytest

from openalex_mcp import cache as cache_mod
from openalex_mcp.cache import (
    DiskCache,
    MemoryCache,
    NullCache,
    build_cache,
    cache_clear,
    cache_stats,
)
from openalex_mcp.client import OpenAlexClient
from openalex_mcp.exceptions import OpenAlexAuthError

# `openalex_mcp.cli.__init__` re-exports a function called `main`, which shadows
# the submodule attribute — import_module is the only way to reach the module.
cli_main = importlib.import_module("openalex_mcp.cli.main")

API_KEY = "oa-secret-key-9f3c2b"

WORKS_PAGE = {
    "meta": {"count": 1, "page": 1, "per_page": 1},
    "results": [
        {
            "id": "https://openalex.org/W1",
            "title": "Investigación sobre el Perú",
            "publication_year": 2024,
            "cited_by_count": 3,
            "open_access": {"is_oa": True},
            "primary_location": {},
            "authorships": [],
        }
    ],
}

SECOND_WORKS_PAGE = {
    "meta": {"count": 1, "page": 1, "per_page": 1},
    "results": [
        {
            "id": "https://openalex.org/W2",
            "title": "Second body",
            "publication_year": 2025,
            "cited_by_count": 9,
            "open_access": {"is_oa": False},
            "primary_location": {},
            "authorships": [],
        }
    ],
}


@pytest.fixture
def frozen_clock(monkeypatch):
    """A movable clock for the cache module, so expiry needs no sleeping."""

    class Clock:
        def __init__(self) -> None:
            self.now = time.time()

        def advance(self, seconds: float) -> None:
            self.now += seconds

    clock = Clock()
    monkeypatch.setattr(cache_mod.time, "time", lambda: clock.now)
    return clock


def _files(cache: DiskCache) -> list:
    return sorted(cache.directory.glob("*.json"))


# ─── Miss writes / hit reads ──────────────────────────────────────────────────


async def test_a_cache_miss_hits_the_network_and_writes_an_entry(
    recording_transport, make_client, disk_cache
):
    transport = recording_transport(WORKS_PAGE)
    async with make_client(transport, cache=disk_cache) as client:
        await client.request("/works", {"per_page": 1})
    assert transport.count == 1
    assert len(_files(disk_cache)) == 1


async def test_a_cache_hit_answers_without_touching_the_network(
    recording_transport, make_client, disk_cache
):
    transport = recording_transport(WORKS_PAGE)
    async with make_client(transport, cache=disk_cache) as client:
        first = await client.request("/works", {"per_page": 1})
        assert client.last_cached is False
        second = await client.request("/works", {"per_page": 1})
    assert transport.count == 1
    assert second == first
    assert client.last_cached is True


async def test_a_cache_hit_survives_process_exit(
    recording_transport, make_client, disk_cache, tmp_path
):
    # This is the whole point of a disk cache: a CLI is a new process each run,
    # so an in-memory cache would never register a single hit.
    transport = recording_transport(WORKS_PAGE)
    async with make_client(transport, cache=disk_cache) as client:
        await client.request("/works", {"per_page": 1})

    fresh_cache = DiskCache(disk_cache.directory)
    async with make_client(transport, cache=fresh_cache) as client:
        body = await client.request("/works", {"per_page": 1})
        assert client.last_cached is True
    assert transport.count == 1
    assert body["results"][0]["id"].endswith("W1")


async def test_different_parameters_do_not_share_a_cache_entry(
    recording_transport, make_client, disk_cache
):
    transport = recording_transport([WORKS_PAGE, SECOND_WORKS_PAGE])
    async with make_client(transport, cache=disk_cache) as client:
        await client.request("/works", {"per_page": 1})
        await client.request("/works", {"per_page": 2})
    assert transport.count == 2
    assert len(_files(disk_cache)) == 2


# ─── Expiry ───────────────────────────────────────────────────────────────────


async def test_an_expired_entry_is_refetched(
    recording_transport, make_client, disk_cache, frozen_clock
):
    transport = recording_transport([WORKS_PAGE, SECOND_WORKS_PAGE])
    async with make_client(transport, cache=disk_cache, cache_ttl=60) as client:
        await client.request("/works", {"per_page": 1})
        frozen_clock.advance(61)
        body = await client.request("/works", {"per_page": 1})
        assert client.last_cached is False
    assert transport.count == 2
    assert body["results"][0]["title"] == "Second body"


async def test_an_expired_entry_is_deleted_from_disk(
    recording_transport, make_client, disk_cache, frozen_clock
):
    transport = recording_transport(WORKS_PAGE)
    cache = disk_cache
    cache.set("some-key", {"a": 1}, ttl=30)
    assert len(_files(cache)) == 1
    frozen_clock.advance(31)
    assert cache.get("some-key") is None
    assert _files(cache) == []


def test_a_non_positive_ttl_writes_nothing(disk_cache):
    disk_cache.set("k", {"a": 1}, ttl=0)
    assert _files(disk_cache) == []


# ─── --refresh ────────────────────────────────────────────────────────────────


async def test_refresh_bypasses_a_live_cache_entry(
    recording_transport, make_client, disk_cache
):
    transport = recording_transport([WORKS_PAGE, SECOND_WORKS_PAGE])
    async with make_client(transport, cache=disk_cache) as client:
        await client.request("/works", {"per_page": 1})

    async with make_client(transport, cache=DiskCache(disk_cache.directory), refresh=True) as client:
        body = await client.request("/works", {"per_page": 1})
        assert client.last_cached is False
    assert transport.count == 2
    assert body["results"][0]["title"] == "Second body"


async def test_refresh_also_rewrites_the_cache_for_the_next_run(
    recording_transport, make_client, disk_cache
):
    # `--refresh` means "refetch and rewrite", not "don't cache". The proof is
    # that a later non-refresh run sees the *new* body without a request.
    transport = recording_transport([WORKS_PAGE, SECOND_WORKS_PAGE])
    async with make_client(transport, cache=disk_cache) as client:
        await client.request("/works", {"per_page": 1})
    async with make_client(transport, cache=DiskCache(disk_cache.directory), refresh=True) as client:
        await client.request("/works", {"per_page": 1})

    async with make_client(transport, cache=DiskCache(disk_cache.directory)) as client:
        body = await client.request("/works", {"per_page": 1})
        assert client.last_cached is True
    assert transport.count == 2
    assert body["results"][0]["title"] == "Second body"


# ─── --no-cache ───────────────────────────────────────────────────────────────


async def test_no_cache_never_reads_an_existing_entry(
    recording_transport, make_client, disk_cache
):
    transport = recording_transport([WORKS_PAGE, SECOND_WORKS_PAGE])
    async with make_client(transport, cache=disk_cache) as client:
        await client.request("/works", {"per_page": 1})
    entries_before = len(_files(disk_cache))

    async with make_client(transport, cache=NullCache()) as client:
        body = await client.request("/works", {"per_page": 1})
        assert client.last_cached is False
    assert transport.count == 2
    assert body["results"][0]["title"] == "Second body"
    assert len(_files(disk_cache)) == entries_before


async def test_no_cache_never_writes_an_entry(
    recording_transport, make_client, disk_cache
):
    transport = recording_transport(WORKS_PAGE)
    async with make_client(transport, cache=NullCache()) as client:
        await client.request("/works", {"per_page": 1})
        await client.request("/works", {"per_page": 1})
    assert transport.count == 2
    assert _files(disk_cache) == []


def test_null_cache_is_inert():
    cache = NullCache()
    cache.set("k", {"a": 1}, ttl=999)
    assert cache.get("k") is None


# ─── CLI flag wiring ──────────────────────────────────────────────────────────


def _args(**overrides) -> argparse.Namespace:
    base = {"no_cache": False, "refresh": False, "api_key": None, "email": None}
    base.update(overrides)
    return argparse.Namespace(**base)


@pytest.mark.parametrize(
    "no_cache, expected_backend",
    [(False, "disk"), (True, "none")],
)
def test_no_cache_flag_selects_the_null_backend(
    monkeypatch, make_settings, no_cache, expected_backend
):
    # Asserted through a spy rather than by calling build_cache for real: the
    # "disk" branch would create the developer's actual cache directory.
    chosen: list[str] = []
    monkeypatch.setattr(
        cli_main, "build_cache", lambda backend: chosen.append(backend) or NullCache()
    )
    cli_main._make_client(_args(no_cache=no_cache), make_settings())
    assert chosen == [expected_backend]


def test_refresh_flag_reaches_the_client(monkeypatch, make_settings):
    monkeypatch.setattr(cli_main, "build_cache", lambda backend: NullCache())
    client = cli_main._make_client(_args(refresh=True), make_settings())
    assert client._refresh is True


@pytest.mark.parametrize(
    "backend, expected",
    [("disk", DiskCache), ("none", NullCache), ("memory", MemoryCache)],
)
def test_build_cache_returns_the_named_backend(backend, expected, tmp_path):
    assert isinstance(build_cache(backend, tmp_path), expected)


# ─── Secrets never reach the cache (spec §3) ──────────────────────────────────


def test_cache_key_ignores_the_api_key_and_mailto_parameters():
    # Two people sharing a machine ask the same question; if the key material
    # included their credentials they would each pay for a separate miss, and
    # the secret would end up derivable from the cache layout.
    anonymous = OpenAlexClient._cache_key("/works", {"per_page": 1, "search": "x"})
    identified = OpenAlexClient._cache_key(
        "/works",
        {"per_page": 1, "search": "x", "api_key": API_KEY, "mailto": "a@example.com"},
    )
    assert anonymous == identified


def test_cache_key_is_a_sha256_digest_not_the_raw_url():
    key = OpenAlexClient._cache_key("/works", {"search": "x"})
    assert len(key) == 64
    assert all(c in "0123456789abcdef" for c in key)
    assert "works" not in key


def test_cache_key_distinguishes_paths_and_params():
    assert OpenAlexClient._cache_key("/works", {}) != OpenAlexClient._cache_key("/authors", {})
    assert OpenAlexClient._cache_key("/works", {"page": 1}) != OpenAlexClient._cache_key(
        "/works", {"page": 2}
    )


async def test_the_api_key_is_never_written_into_a_cache_file(
    recording_transport, make_client, disk_cache
):
    transport = recording_transport(WORKS_PAGE)
    async with make_client(transport, cache=disk_cache, api_key=API_KEY) as client:
        await client.request("/works", {"per_page": 1})

    written = _files(disk_cache)
    assert written, "expected the successful response to be cached"
    for path in written:
        raw = path.read_text(encoding="utf-8")
        assert API_KEY not in raw
        assert API_KEY not in path.name


async def test_the_api_key_is_still_sent_on_the_wire(
    recording_transport, make_client, disk_cache
):
    # Guards the test above from passing for the wrong reason (auth silently
    # dropped rather than merely excluded from the cache).
    transport = recording_transport(WORKS_PAGE)
    async with make_client(transport, cache=disk_cache, api_key=API_KEY) as client:
        await client.request("/works", {"per_page": 1})
    assert f"api_key={API_KEY}" in str(transport.calls[0])


async def test_an_auth_failure_is_never_cached(
    recording_transport, make_client, disk_cache
):
    transport = recording_transport({"error": "Invalid API key"}, status=401)
    async with make_client(transport, cache=disk_cache, api_key=API_KEY) as client:
        with pytest.raises(OpenAlexAuthError):
            await client.request("/works", {"per_page": 1})
    assert _files(disk_cache) == []


async def test_an_api_error_is_never_cached(
    recording_transport, make_client, disk_cache
):
    transport = recording_transport({"error": "Invalid filter"}, status=400)
    async with make_client(transport, cache=disk_cache) as client:
        with pytest.raises(Exception):
            await client.request("/works", {"per_page": 1})
    assert _files(disk_cache) == []


# ─── `cache` subcommand helpers ───────────────────────────────────────────────


def test_cache_stats_counts_live_and_expired_entries(disk_cache, frozen_clock):
    disk_cache.set("live", {"a": 1}, ttl=600)
    disk_cache.set("stale", {"a": 2}, ttl=10)
    frozen_clock.advance(11)
    stats = cache_stats(disk_cache.directory)
    assert stats["entries"] == 2
    assert stats["live"] == 1
    assert stats["expired"] == 1
    assert stats["size_bytes"] > 0


def test_cache_stats_on_a_missing_directory_reports_zero(tmp_path):
    stats = cache_stats(tmp_path / "never-created")
    assert stats["exists"] is False
    assert stats["entries"] == 0


def test_cache_clear_removes_every_entry_and_reports_the_count(disk_cache):
    disk_cache.set("a", {"x": 1}, ttl=600)
    disk_cache.set("b", {"x": 2}, ttl=600)
    result = cache_clear(disk_cache.directory)
    assert result["removed"] == 2
    assert _files(disk_cache) == []


def test_a_corrupt_cache_file_is_treated_as_a_miss(disk_cache):
    disk_cache.set("k", {"a": 1}, ttl=600)
    _files(disk_cache)[0].write_text("{not json", encoding="utf-8")
    assert disk_cache.get("k") is None


def test_cached_bodies_keep_their_accented_text(disk_cache):
    disk_cache.set("k", {"title": "Investigación sobre el Perú"}, ttl=600)
    assert disk_cache.get("k")["title"] == "Investigación sobre el Perú"
    assert "Investigación" in _files(disk_cache)[0].read_text(encoding="utf-8")


def test_memory_cache_expires_entries(frozen_clock):
    cache = MemoryCache()
    cache.set("k", {"a": 1}, ttl=10)
    assert cache.get("k") == {"a": 1}
    frozen_clock.advance(11)
    assert cache.get("k") is None
