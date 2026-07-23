"""Human-readable console rendering for CLI results.

The MCP server hands its formatted dicts straight to an LLM, so it never needs
this layer — this module exists only so a human staring at a terminal gets
readable tables instead of raw JSON. Pass --json to any command to skip it.
"""

import json
import os
import shutil
import sys
from typing import Any, Callable

_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")

RESET = "\033[0m" if _COLOR else ""
BOLD = "\033[1m" if _COLOR else ""
DIM = "\033[2m" if _COLOR else ""
CYAN = "\033[36m" if _COLOR else ""


def _terminal_width() -> int:
    return shutil.get_terminal_size(fallback=(100, 24)).columns


def _truncate(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    # Plain ASCII ellipsis — Windows consoles default to cp1252 and mangle "…".
    return text[: max(0, width - 3)].rstrip() + "..."


def _table(rows: list[dict], columns: list[tuple[str, str, int]]) -> None:
    """Render rows as a simple fixed-width table.

    columns: list of (header, key, max_width). The last column stretches
    to fill remaining terminal width.
    """
    if not rows:
        print(f"{DIM}(no results){RESET}")
        return

    term_width = _terminal_width()
    fixed_width = sum(w for _, _, w in columns[:-1]) + 2 * (len(columns) - 1)
    last_header, last_key, last_min = columns[-1]
    last_width = max(last_min, term_width - fixed_width - 1)
    widths = [w for _, _, w in columns[:-1]] + [last_width]
    headers = [h for h, _, _ in columns]

    header_line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(f"{BOLD}{header_line}{RESET}")
    print(DIM + "-" * min(term_width, len(header_line)) + RESET)

    for row in rows:
        cells = []
        for (header, key, _), width in zip(columns, widths):
            value = row.get(key)
            text = "" if value is None else str(value)
            cells.append(_truncate(text, width).ljust(width))
        print("  ".join(cells))


def _kv_block(data: dict, skip: set[str] = frozenset()) -> None:
    for key, value in data.items():
        if key in skip or value is None:
            continue
        label = key.replace("_", " ")
        if isinstance(value, list):
            if not value:
                continue
            print(f"{BOLD}{label}:{RESET}")
            for item in value:
                if isinstance(item, dict):
                    line = " · ".join(f"{k}: {v}" for k, v in item.items() if v is not None)
                    print(f"  - {line}")
                else:
                    print(f"  - {item}")
        elif isinstance(value, dict):
            print(f"{BOLD}{label}:{RESET}")
            for k, v in value.items():
                print(f"  {k}: {v}")
        else:
            print(f"{BOLD}{label}:{RESET} {value}")


def print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _summary(data: dict) -> None:
    total = data.get("total_results")
    showing = data.get("showing")
    if total is not None:
        print(f"{CYAN}{showing} of {total} results{RESET}\n")


def print_works_list(data: dict) -> None:
    _summary(data)
    _table(
        data.get("works", []),
        [
            ("ID", "openalex_id", 12),
            ("YEAR", "publication_year", 6),
            ("CITES", "cited_by_count", 6),
            ("OA", "open_access", 5),
            ("AUTHOR", "first_author", 20),
            ("TITLE", "title", 40),
        ],
    )


def print_work(data: dict) -> None:
    _kv_block(data)


def print_authors_list(data: dict) -> None:
    _summary(data)
    _table(
        data.get("authors", []),
        [
            ("ID", "openalex_id", 12),
            ("H-IDX", "h_index", 6),
            ("WORKS", "works_count", 6),
            ("CITES", "cited_by_count", 8),
            ("AFFILIATION", "affiliation", 25),
            ("NAME", "name", 30),
        ],
    )


def print_author(data: dict) -> None:
    _kv_block(data)


def print_institutions_list(data: dict) -> None:
    _summary(data)
    _table(
        data.get("institutions", []),
        [
            ("ID", "openalex_id", 12),
            ("COUNTRY", "country_code", 8),
            ("TYPE", "type", 12),
            ("WORKS", "works_count", 8),
            ("NAME", "name", 35),
        ],
    )


def print_institution(data: dict) -> None:
    _kv_block(data)


def print_sources_list(data: dict) -> None:
    _summary(data)
    _table(
        data.get("sources", []),
        [
            ("ID", "openalex_id", 12),
            ("TYPE", "type", 12),
            ("OA", "is_oa", 5),
            ("WORKS", "works_count", 8),
            ("NAME", "name", 35),
        ],
    )


def print_source(data: dict) -> None:
    _kv_block(data)


def print_group_by(data: dict) -> None:
    print(f"{CYAN}Grouped by: {data.get('group_by')} ({data.get('total_groups')} groups){RESET}\n")
    _table(
        data.get("groups", []),
        [
            ("KEY", "key", 20),
            ("COUNT", "count", 10),
            ("LABEL", "label", 40),
        ],
    )


def print_filter_guide(text: str) -> None:
    print(text)


PRINTERS: dict[str, Callable[[Any], None]] = {
    "search-works": print_works_list,
    "get-work": print_work,
    "search-authors": print_authors_list,
    "get-author": print_author,
    "search-institutions": print_institutions_list,
    "get-institution": print_institution,
    "search-sources": print_sources_list,
    "get-source": print_source,
    "aggregate-works": print_group_by,
}
