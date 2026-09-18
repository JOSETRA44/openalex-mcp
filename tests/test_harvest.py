"""Cursor pagination and bulk extraction (ARSENAL-SPEC §5 and §6.6).

Paging is driven by a fake transport / fake page fetcher, so a harvest that
failed to terminate would hang the suite rather than hit the network — every
test here therefore also asserts the loop *stops*.
"""

from __future__ import annotations

import csv
import importlib
import io
import json

import httpx
import pytest

from openalex_mcp.cache import NullCache
from openalex_mcp.cli.harvest import PER_PAGE_MAX, Harvester
from openalex_mcp.cli.render import RowWriter
from openalex_mcp.tools import search_works

cli_main = importlib.import_module("openalex_mcp.cli.main")


def _row(index: int) -> dict:
    return {"openalex_id": f"W{index}", "title": f"Paper {index}", "cited_by_count": index}


class FakePager:
    """Serves `page_count` cursor pages, then reports no next cursor."""

    def __init__(self, page_count: int, page_size: int = 3, total: int | None = None) -> None:
        self.page_count = page_count
        self.page_size = page_size
        self.total = total if total is not None else page_count * page_size
        self.requested: list[tuple[str, int]] = []

    async def __call__(self, cursor: str, per_page: int) -> dict:
        self.requested.append((cursor, per_page))
        index = len(self.requested) - 1
        start = index * self.page_size
        rows = [_row(i) for i in range(start, start + self.page_size)]
        last = index >= self.page_count - 1
        payload = {"total_results": self.total, "works": rows}
        if not last:
            payload["next_cursor"] = f"cursor-{index + 1}"
        return payload


async def collect(harvester: Harvester) -> list[dict]:
    return [item async for item in harvester]


# ─── Termination ──────────────────────────────────────────────────────────────


async def test_paging_stops_when_meta_next_cursor_is_absent():
    pager = FakePager(page_count=3, page_size=4)
    rows = await collect(Harvester(pager, "works", max_rows=1000))
    assert len(rows) == 12
    assert len(pager.requested) == 3


async def test_paging_stops_when_next_cursor_is_explicitly_null():
    calls: list[str] = []

    async def fetch(cursor: str, per_page: int) -> dict:
        calls.append(cursor)
        return {"works": [_row(len(calls))], "next_cursor": None}

    rows = await collect(Harvester(fetch, "works", max_rows=100))
    assert len(rows) == 1
    assert calls == ["*"]


async def test_the_first_page_starts_a_new_scroll():
    pager = FakePager(page_count=1)
    await collect(Harvester(pager, "works", max_rows=10))
    assert pager.requested[0][0] == "*"


async def test_each_page_after_the_first_follows_the_returned_cursor():
    pager = FakePager(page_count=3, page_size=2)
    await collect(Harvester(pager, "works", max_rows=100))
    assert [cursor for cursor, _ in pager.requested] == ["*", "cursor-1", "cursor-2"]


async def test_an_empty_page_terminates_the_harvest():
    async def fetch(cursor: str, per_page: int) -> dict:
        return {"works": [], "next_cursor": "always-more"}

    assert await collect(Harvester(fetch, "works", max_rows=100)) == []


async def test_an_empty_result_set_is_a_successful_zero_row_harvest():
    async def fetch(cursor: str, per_page: int) -> dict:
        return {"total_results": 0, "works": []}

    harvester = Harvester(fetch, "works", max_rows=100)
    assert await collect(harvester) == []
    assert harvester.stats["harvested"] == 0
    assert harvester.stats["truncated"] is False


# ─── --max ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("max_rows", [1, 5, 7, 12])
async def test_max_caps_the_number_of_harvested_rows(max_rows):
    pager = FakePager(page_count=50, page_size=4)
    rows = await collect(Harvester(pager, "works", max_rows=max_rows))
    assert len(rows) == max_rows


async def test_max_zero_makes_no_request_at_all():
    pager = FakePager(page_count=5)
    assert await collect(Harvester(pager, "works", max_rows=0)) == []
    assert pager.requested == []


async def test_the_last_page_only_asks_for_the_remaining_budget():
    # A `--max 25` harvest should cost 25 records on its final page, not 200.
    pager = FakePager(page_count=50, page_size=10)
    await collect(Harvester(pager, "works", max_rows=25, per_page=10))
    assert [size for _, size in pager.requested] == [10, 10, 5]


async def test_per_page_is_clamped_to_the_openalex_maximum():
    pager = FakePager(page_count=1, page_size=1)
    await collect(Harvester(pager, "works", max_rows=10_000, per_page=5_000))
    assert pager.requested[0][1] == PER_PAGE_MAX


async def test_stats_report_truncation_when_max_was_reached():
    pager = FakePager(page_count=50, page_size=4)
    harvester = Harvester(pager, "works", max_rows=6)
    await collect(harvester)
    assert harvester.stats["truncated"] is True
    assert harvester.stats["harvested"] == 6


async def test_stats_report_no_truncation_when_the_set_was_exhausted():
    harvester = Harvester(FakePager(page_count=2, page_size=3), "works", max_rows=1000)
    await collect(harvester)
    assert harvester.stats["truncated"] is False
    assert harvester.stats["pages"] == 2
    assert harvester.stats["total"] == 6


# ─── Duplicates ───────────────────────────────────────────────────────────────


async def test_a_record_repeated_across_pages_is_emitted_only_once():
    # OpenAlex can repeat a record across cursor pages when the index shifts
    # mid-scroll; a harvest that emitted it twice would corrupt any count.
    pages = [
        {"works": [_row(1), _row(2)], "next_cursor": "c1"},
        {"works": [_row(2), _row(3)], "next_cursor": None},
    ]

    async def fetch(cursor: str, per_page: int) -> dict:
        return pages[0] if cursor == "*" else pages[1]

    harvester = Harvester(fetch, "works", max_rows=100)
    rows = await collect(harvester)
    ids = [r["openalex_id"] for r in rows]
    assert ids == ["W1", "W2", "W3"]
    assert len(ids) == len(set(ids))
    assert harvester.stats["duplicates_skipped"] == 1


async def test_a_duplicate_does_not_consume_the_max_budget():
    pages = [
        {"works": [_row(1), _row(1), _row(2)], "next_cursor": None},
    ]

    async def fetch(cursor: str, per_page: int) -> dict:
        return pages[0]

    rows = await collect(Harvester(fetch, "works", max_rows=2))
    assert [r["openalex_id"] for r in rows] == ["W1", "W2"]


async def test_records_without_an_id_are_deduped_by_content():
    async def fetch(cursor: str, per_page: int) -> dict:
        return {"works": [{"key": "2024", "count": 5}, {"key": "2024", "count": 5}]}

    assert len(await collect(Harvester(fetch, "works", max_rows=100))) == 1


async def test_progress_goes_through_the_supplied_callback_once_per_page():
    messages: list[str] = []
    await collect(
        Harvester(FakePager(page_count=3, page_size=2), "works", max_rows=100, progress=messages.append)
    )
    assert len(messages) == 3
    assert all("page" in m for m in messages)


# ─── Streaming a harvest ──────────────────────────────────────────────────────


async def test_a_harvest_streams_one_jsonl_line_per_row():
    stream = io.StringIO()
    writer = RowWriter("jsonl", stream)
    async for item in Harvester(FakePager(page_count=2, page_size=3), "works", max_rows=100):
        writer.write(item)
    ids = [json.loads(line)["openalex_id"] for line in stream.getvalue().splitlines()]
    assert ids == [f"W{i}" for i in range(6)]


# ─── End to end over a mock HTTP transport ────────────────────────────────────


class PaginatedTransport:
    """A fake OpenAlex `/works` endpoint that scrolls with `cursor`."""

    def __init__(self, pages: int, page_size: int) -> None:
        self.pages = pages
        self.page_size = page_size
        self.cursors: list[str | None] = []
        self.transport = httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        cursor = request.url.params.get("cursor")
        self.cursors.append(cursor)
        index = 0 if cursor in (None, "*") else int(cursor.split("-")[1])
        start = index * self.page_size
        results = [
            {
                "id": f"https://openalex.org/W{i}",
                "title": f"Investigación {i} — Perú",
                "publication_year": 2024,
                "cited_by_count": i,
                "primary_location": {},
                "authorships": [],
            }
            for i in range(start, start + self.page_size)
        ]
        meta = {"count": self.pages * self.page_size, "per_page": self.page_size}
        if index < self.pages - 1:
            meta["next_cursor"] = f"cursor-{index + 1}"
        return httpx.Response(200, json={"meta": meta, "results": results})


async def test_a_real_cursor_harvest_terminates_and_never_repeats_a_row(
    make_settings, tmp_path
):
    from openalex_mcp.client import OpenAlexClient

    transport = PaginatedTransport(pages=4, page_size=5)
    settings = make_settings()
    async with OpenAlexClient(settings, cache=NullCache(), transport=transport.transport) as client:
        harvester = Harvester(
            lambda cursor, n: search_works(client, "neural", per_page=n, cursor=cursor),
            "works",
            max_rows=1000,
        )
        rows = [item async for item in harvester]

    ids = [r["openalex_id"] for r in rows]
    assert len(ids) == 20
    assert len(set(ids)) == 20
    assert transport.cursors == ["*", "cursor-1", "cursor-2", "cursor-3"]


async def test_a_real_cursor_harvest_honours_max(make_settings):
    from openalex_mcp.client import OpenAlexClient

    transport = PaginatedTransport(pages=10, page_size=5)
    async with OpenAlexClient(
        make_settings(), cache=NullCache(), transport=transport.transport
    ) as client:
        harvester = Harvester(
            lambda cursor, n: search_works(client, "neural", per_page=n, cursor=cursor),
            "works",
            max_rows=7,
            per_page=5,
        )
        rows = [item async for item in harvester]
    assert len(rows) == 7
    assert harvester.stats["truncated"] is True


def test_the_cli_all_flag_streams_a_csv_harvest_to_a_file(
    monkeypatch, make_settings, tmp_path
):
    """Full `openalex search-works --all` path, with the network faked out."""
    transport = PaginatedTransport(pages=3, page_size=4)
    real_client = cli_main.OpenAlexClient

    monkeypatch.setattr(cli_main, "build_cache", lambda backend: NullCache())
    monkeypatch.setattr(
        cli_main,
        "OpenAlexClient",
        lambda settings, cache=None, refresh=False: real_client(
            settings, cache=cache, refresh=refresh, transport=transport.transport
        ),
    )

    out = tmp_path / "harvest.csv"
    status = cli_main.run([
        "search-works", "neural networks",
        "--all", "--max", "10",
        "--email", "tests@example.com",
        "--no-cache", "-q",
        "-f", "csv", "-o", str(out),
    ])

    assert status == 0
    rows = list(csv.DictReader(io.StringIO(out.read_text(encoding="utf-8"))))
    assert len(rows) == 10
    assert [r["openalex_id"] for r in rows] == [f"W{i}" for i in range(10)]
    # Accented text must survive the streamed file write (spec §9).
    assert "Investigación" in rows[0]["title"]


def test_the_cli_all_flag_reports_the_harvest_in_the_json_envelope(
    monkeypatch, tmp_path
):
    transport = PaginatedTransport(pages=2, page_size=3)
    real_client = cli_main.OpenAlexClient
    monkeypatch.setattr(cli_main, "build_cache", lambda backend: NullCache())
    monkeypatch.setattr(
        cli_main,
        "OpenAlexClient",
        lambda settings, cache=None, refresh=False: real_client(
            settings, cache=cache, refresh=refresh, transport=transport.transport
        ),
    )

    out = tmp_path / "harvest.json"
    status = cli_main.run([
        "search-works", "neural",
        "--all", "--max", "100",
        "--email", "tests@example.com",
        "--no-cache", "-q",
        "-f", "json", "-o", str(out),
    ])

    assert status == 0
    envelope = json.loads(out.read_text(encoding="utf-8"))
    assert envelope["ok"] is True
    assert envelope["count"] == len(envelope["rows"]) == 6
    assert envelope["meta"]["pages"] == 2
    assert envelope["meta"]["truncated"] is False
