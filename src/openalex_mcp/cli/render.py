"""Unified output layer: envelope construction and the five render formats.

Rule that everything here serves: **stdout is data, stderr is commentary**. A
caller doing `openalex ... -f jsonl | jq` must never receive a progress line or
a "wrote N rows" note on stdout, so `note()` is the only thing that writes to
stderr and nothing else ever does.
"""

from __future__ import annotations

import contextlib
import csv
import io
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, TextIO

from .. import cli_output as legacy

SOURCE = "openalex"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_envelope(
    command: str,
    data: Any,
    rows: list[dict],
    cached: bool = False,
    meta: dict | None = None,
) -> dict[str, Any]:
    """The success envelope every `--format json` response is wrapped in."""
    return {
        "ok": True,
        "command": command,
        "source": SOURCE,
        "fetched_at": utc_now(),
        "cached": cached,
        "count": len(rows),
        "meta": meta or {},
        "data": data if isinstance(data, dict) else {},
        "rows": rows,
    }


def _columns(rows: list[dict]) -> list[str]:
    """Union of keys across rows, first-seen order — rows are often ragged."""
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    return columns


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def rows_to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_columns(rows), extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _cell(v) for k, v in row.items()})
    return buf.getvalue()


def rows_to_markdown(rows: list[dict]) -> str:
    if not rows:
        return "_(no rows)_\n"
    columns = _columns(rows)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        # Pipes would break the table; escape them rather than drop content.
        cells = [_cell(row.get(c)).replace("|", "\\|").replace("\n", " ") for c in columns]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def rows_to_jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def generic_table(rows: list[dict], stream: TextIO) -> None:
    """Fallback table for rows with no bespoke printer (harvests, describe)."""
    with contextlib.redirect_stdout(stream):
        if not rows:
            print("(no results)")
            return
        columns = _columns(rows)
        widths = [
            min(40, max(len(c), *(len(_cell(r.get(c))) for r in rows)))
            for c in columns
        ]
        header = "  ".join(c.upper()[:w].ljust(w) for c, w in zip(columns, widths))
        print(header)
        print("-" * len(header))
        for row in rows:
            print("  ".join(_cell(row.get(c))[:w].ljust(w) for c, w in zip(columns, widths)))


class RowWriter:
    """Incremental row writer — the streaming half of `--all`.

    jsonl and csv can be emitted row by row, which is what keeps an unbounded
    harvest from being buffered in memory. CSV pays for that by locking its
    header to the first row's keys; later rows are projected onto those columns.
    """

    def __init__(self, fmt: str, stream: TextIO) -> None:
        self._fmt = fmt
        self._stream = stream
        self._writer: csv.DictWriter | None = None
        self.count = 0

    def write(self, row: dict) -> None:
        if self._fmt == "jsonl":
            self._stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        elif self._fmt == "csv":
            if self._writer is None:
                self._writer = csv.DictWriter(
                    self._stream, fieldnames=list(row), extrasaction="ignore", lineterminator="\n"
                )
                self._writer.writeheader()
            self._writer.writerow({k: _cell(v) for k, v in row.items()})
        self.count += 1


class Output:
    """Owns the destination stream, the format, and the stderr note channel."""

    def __init__(self, fmt: str, output: str | None, quiet: bool, no_color: bool) -> None:
        self.fmt = fmt
        self.path = output
        self.quiet = quiet
        # Colour is only ever meaningful for the human `table` format on a tty.
        self.color = (
            not no_color
            and not os.environ.get("NO_COLOR")
            and output is None
            and fmt == "table"
            and sys.stdout.isatty()
        )
        legacy.set_color(self.color)
        self._handle: TextIO | None = None

    def __enter__(self) -> "Output":
        self._handle = open(self.path, "w", encoding="utf-8", newline="") if self.path else None
        return self

    def __exit__(self, *_: Any) -> None:
        if self._handle:
            self._handle.close()
            self._handle = None

    @property
    def stream(self) -> TextIO:
        return self._handle or sys.stdout

    def note(self, message: str) -> None:
        """Progress/warnings — stderr only, silenced by --quiet."""
        if not self.quiet:
            print(message, file=sys.stderr, flush=True)

    def write_text(self, text: str) -> None:
        self.stream.write(text)
        if text and not text.endswith("\n"):
            self.stream.write("\n")

    def render(
        self,
        command: str,
        data: Any,
        rows: list[dict],
        cached: bool = False,
        meta: dict | None = None,
        table_printer: Any = None,
    ) -> None:
        """Render one complete (non-streamed) result in the selected format."""
        if self.fmt == "json":
            self.write_text(json.dumps(
                build_envelope(command, data, rows, cached, meta), indent=2, ensure_ascii=False
            ))
        elif self.fmt == "jsonl":
            self.write_text(rows_to_jsonl(rows))
        elif self.fmt == "csv":
            self.write_text(rows_to_csv(rows))
        elif self.fmt == "md":
            self.write_text(rows_to_markdown(rows))
        else:
            if table_printer is not None:
                with contextlib.redirect_stdout(self.stream):
                    table_printer(data)
            else:
                generic_table(rows, self.stream)
        if self.path:
            self.note(f"Wrote {len(rows)} rows -> {self.path}")


def error_envelope(command: str, code: str, message: str, hint: str) -> dict[str, Any]:
    """The failure envelope — same top-level `ok`/`command` shape as success."""
    return {
        "ok": False,
        "command": command,
        "source": SOURCE,
        "fetched_at": utc_now(),
        "error": {"code": code, "message": message, "hint": hint},
    }
