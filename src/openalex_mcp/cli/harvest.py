"""Bulk extraction over OpenAlex cursor pagination.

OpenAlex caps `page`-based paging at 10 000 records, so anything resembling a
real harvest has to scroll with `cursor=*` and follow `meta.next_cursor`. This
module owns that loop and nothing else — the per-endpoint request building
still happens in `tools/*.py`, shared with the MCP server.

Rows are yielded one at a time rather than accumulated, so `-f jsonl --all`
streams and stays flat in memory regardless of `--max`.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Awaitable, Callable

# OpenAlex refuses per_page above 200 on every entity endpoint.
PER_PAGE_MAX = 200

FetchPage = Callable[[str, int], Awaitable[dict]]


class Harvester:
    """Scrolls one cursor-paginated endpoint until exhausted or capped.

    ``fetch(cursor, per_page)`` must call the shared tool function and return
    its formatted dict; ``list_key`` names the list inside that dict.
    """

    def __init__(
        self,
        fetch: FetchPage,
        list_key: str,
        max_rows: int = 1000,
        per_page: int = PER_PAGE_MAX,
        progress: Callable[[str], None] | None = None,
    ) -> None:
        self._fetch = fetch
        self._list_key = list_key
        self._max_rows = max(0, max_rows)
        self._per_page = max(1, min(PER_PAGE_MAX, per_page))
        self._progress = progress or (lambda _msg: None)
        self.total: int | None = None
        self.pages = 0
        self.emitted = 0
        self.duplicates = 0

    async def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        cursor: str | None = "*"
        seen: set[str] = set()

        while cursor and self.emitted < self._max_rows:
            # Never ask for more than the remaining budget: the last page of a
            # `--max 25` harvest should cost 25 records, not 200.
            page_size = min(self._per_page, self._max_rows - self.emitted)
            result = await self._fetch(cursor, page_size)
            self.pages += 1
            if self.total is None:
                self.total = result.get("total_results")

            items = result.get(self._list_key) or []
            if not items:
                break

            for item in items:
                key = _identity(item)
                if key in seen:
                    # OpenAlex can repeat a record across cursor pages when the
                    # index shifts mid-scroll; the caller must never see it twice.
                    self.duplicates += 1
                    continue
                seen.add(key)
                self.emitted += 1
                yield item
                if self.emitted >= self._max_rows:
                    break

            cursor = result.get("next_cursor")
            self._progress(
                f"  page {self.pages}: {self.emitted}"
                + (f"/{self.total}" if self.total is not None else "")
                + " rows"
            )

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "pages": self.pages,
            "harvested": self.emitted,
            "duplicates_skipped": self.duplicates,
            "truncated": self.emitted >= self._max_rows,
        }


def _identity(item: dict) -> str:
    """Stable dedupe key: the OpenAlex ID, falling back to the whole record."""
    return str(item.get("openalex_id") or sorted(item.items()))
