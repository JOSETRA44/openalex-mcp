"""Shared fixtures for the `openalex` CLI test suite.

Every fixture here exists for one reason: keeping the suite hermetic. The repo
ships a real `.env` with an OpenAlex API key and the CLI's default cache lives
in the developer's own `platformdirs` cache directory — a test that reads either
of those would pass or fail depending on the machine it ran on.
"""

from __future__ import annotations

from typing import Any, Callable

import httpx
import pytest

from openalex_mcp.cache import DiskCache
from openalex_mcp.cli.render import Output
from openalex_mcp.client import OpenAlexClient
from openalex_mcp.config import OpenAlexSettings


@pytest.fixture(autouse=True)
def hermetic_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip ambient OpenAlex configuration and force colour off.

    `Output` consults NO_COLOR, and `OpenAlexSettings` reads OPENALEX_* — both
    would otherwise make assertions depend on the developer's shell.
    """
    for var in (
        "OPENALEX_API_KEY",
        "OPENALEX_EMAIL",
        "OPENALEX_CACHE_TTL",
        "OPENALEX_MAX_RETRIES",
        "LOG_LEVEL",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NO_COLOR", "1")


@pytest.fixture
def make_settings() -> Callable[..., OpenAlexSettings]:
    """Build settings from explicit values only — never from `.env`.

    Passing every field explicitly matters: pydantic-settings gives init kwargs
    the highest priority, so this is what stops the repo's `.env` API key from
    bleeding into a test.
    """

    def _make(**overrides: Any) -> OpenAlexSettings:
        base: dict[str, Any] = {
            "api_key": None,
            "email": "tests@example.com",
            "cache_ttl": 300,
            "max_retries": 0,
            "log_level": "INFO",
        }
        base.update(overrides)
        return OpenAlexSettings(**base)

    return _make


class RecordingTransport:
    """An `httpx.MockTransport` that remembers what it was asked for.

    Tests assert on `calls` to prove a cache hit skipped the network entirely —
    the count is the only observable difference between a hit and a miss.
    """

    def __init__(self, responses: list[dict] | dict, status: int = 200) -> None:
        self._responses = responses if isinstance(responses, list) else [responses]
        self._status = status
        self.calls: list[httpx.URL] = []
        self.transport = httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        index = min(len(self.calls), len(self._responses) - 1)
        self.calls.append(request.url)
        return httpx.Response(self._status, json=self._responses[index])

    @property
    def count(self) -> int:
        return len(self.calls)


@pytest.fixture
def recording_transport() -> Callable[..., RecordingTransport]:
    def _make(responses: list[dict] | dict, status: int = 200) -> RecordingTransport:
        return RecordingTransport(responses, status)

    return _make


@pytest.fixture
def make_client(make_settings) -> Callable[..., OpenAlexClient]:
    """An `OpenAlexClient` wired to a mock transport and a throwaway cache dir."""

    def _make(
        transport: RecordingTransport,
        cache=None,
        refresh: bool = False,
        **setting_overrides: Any,
    ) -> OpenAlexClient:
        return OpenAlexClient(
            make_settings(**setting_overrides),
            cache=cache,
            refresh=refresh,
            transport=transport.transport,
        )

    return _make


@pytest.fixture
def disk_cache(tmp_path) -> DiskCache:
    """A DiskCache rooted in tmp_path — never the user's real cache directory."""
    return DiskCache(tmp_path / "cache")


@pytest.fixture
def render_to_text(tmp_path) -> Callable[..., str]:
    """Render one result through the real `Output` and return what was written.

    Rendering to a file rather than capturing stdout keeps the assertion on the
    data channel only: `Output.note` writes to stderr and must not appear here.
    """

    def _render(
        fmt: str,
        command: str,
        data: Any,
        rows: list[dict],
        **kwargs: Any,
    ) -> str:
        path = tmp_path / f"out-{fmt}-{command}.txt"
        with Output(fmt, str(path), quiet=True, no_color=True) as out:
            out.render(command, data, rows, **kwargs)
        return path.read_text(encoding="utf-8")

    return _render
