"""Output-layer tests: the five formats, the JSON envelope, and UTF-8.

Covers ARSENAL-SPEC sections 1 (output contract), 6.1-6.2 (formats + envelope)
and 9 (Windows console encoding). No network is involved: rendering is pure.
"""

from __future__ import annotations

import csv
import io
import json
import re

import pytest

from openalex_mcp.cli.errors import report
from openalex_mcp.cli.parser import FORMATS
from openalex_mcp.cli.render import (
    Output,
    RowWriter,
    build_envelope,
    error_envelope,
    generic_table,
    rows_to_csv,
    rows_to_jsonl,
    rows_to_markdown,
)
from openalex_mcp.exceptions import OpenAlexNotFoundError

# Deliberately ragged: the second row carries a `doi` the first one lacks, so
# every format has to build its columns from the union of keys, not from row 0.
# Accented text is baked in so the UTF-8 round-trip (spec §9) is exercised by
# every format assertion below, not just the one test that names it.
RAGGED_ROWS = [
    {
        "openalex_id": "W1",
        "title": "Investigación sobre redes neuronales en el Perú",
        "cited_by_count": 12,
    },
    {
        "openalex_id": "W2",
        "title": "Ñandú genomics: Côte d'Ivoire cohort",
        "cited_by_count": 0,
        "doi": "10.1000/xyz",
    },
]

ACCENTED = "Investigación sobre redes neuronales en el Perú"
UNION_COLUMNS = ["openalex_id", "title", "cited_by_count", "doi"]


# ─── Every format renders the same rows ───────────────────────────────────────


@pytest.mark.parametrize("fmt", FORMATS)
def test_every_format_renders_every_row(fmt, render_to_text):
    text = render_to_text(fmt, "search-works", {}, RAGGED_ROWS)
    assert "W1" in text
    assert "W2" in text


@pytest.mark.parametrize("fmt", FORMATS)
def test_every_format_renders_an_empty_row_list_without_failing(fmt, render_to_text):
    # An empty result set is a success, not an error (spec §2), so each format
    # must still produce a well-formed (possibly empty) document.
    text = render_to_text(fmt, "search-works", {}, [])
    assert "W1" not in text


def test_parser_offers_exactly_the_five_spec_formats():
    assert list(FORMATS) == ["table", "json", "jsonl", "csv", "md"]


def test_json_format_wraps_rows_in_the_envelope(render_to_text):
    payload = json.loads(render_to_text("json", "search-works", {"a": 1}, RAGGED_ROWS))
    assert payload["rows"] == RAGGED_ROWS
    assert payload["data"] == {"a": 1}


def test_jsonl_format_emits_one_bare_object_per_row(render_to_text):
    lines = render_to_text("jsonl", "search-works", {}, RAGGED_ROWS).splitlines()
    assert len(lines) == len(RAGGED_ROWS)
    assert [json.loads(line) for line in lines] == RAGGED_ROWS
    # jsonl carries no envelope — it is the streaming format.
    assert "ok" not in json.loads(lines[0])


def test_jsonl_format_of_empty_rows_is_an_empty_document(render_to_text):
    assert render_to_text("jsonl", "search-works", {}, []) == ""


def test_csv_header_is_the_union_of_all_row_keys(render_to_text):
    reader = csv.DictReader(io.StringIO(render_to_text("csv", "search-works", {}, RAGGED_ROWS)))
    assert reader.fieldnames == UNION_COLUMNS


def test_csv_leaves_a_ragged_rows_missing_column_empty(render_to_text):
    rows = list(csv.DictReader(io.StringIO(render_to_text("csv", "search-works", {}, RAGGED_ROWS))))
    assert rows[0]["doi"] == ""
    assert rows[1]["doi"] == "10.1000/xyz"


def test_csv_of_empty_rows_is_an_empty_document():
    assert rows_to_csv([]) == ""


def test_markdown_renders_a_github_table_with_union_columns(render_to_text):
    lines = render_to_text("md", "search-works", {}, RAGGED_ROWS).strip().splitlines()
    assert lines[0] == "| " + " | ".join(UNION_COLUMNS) + " |"
    assert set(lines[1].replace(" ", "")) == {"|", "-"}
    assert len(lines) == 2 + len(RAGGED_ROWS)


def test_markdown_of_empty_rows_says_so_instead_of_emitting_a_headerless_table():
    assert rows_to_markdown([]) == "_(no rows)_\n"


def test_markdown_escapes_pipes_so_a_cell_cannot_break_the_table():
    text = rows_to_markdown([{"title": "a | b"}])
    assert r"a \| b" in text


def test_markdown_flattens_newlines_inside_a_cell():
    assert "\n" not in rows_to_markdown([{"title": "a\nb"}]).splitlines()[2]


def test_table_format_prints_a_header_and_one_line_per_row():
    stream = io.StringIO()
    generic_table(RAGGED_ROWS, stream)
    lines = stream.getvalue().splitlines()
    assert lines[0].startswith("OPENALEX_ID")
    assert len(lines) == 2 + len(RAGGED_ROWS)


def test_table_format_of_empty_rows_says_no_results():
    stream = io.StringIO()
    generic_table([], stream)
    assert stream.getvalue().strip() == "(no results)"


def test_nested_values_are_serialized_as_json_not_python_reprs():
    # A Python repr would use single quotes and break any downstream parser.
    row = list(csv.DictReader(io.StringIO(rows_to_csv([{"topics": ["a", "b"], "meta": {"k": 1}}]))))[0]
    assert row["topics"] == '["a", "b"]'
    assert row["meta"] == '{"k": 1}'


# ─── Envelope (spec §1) ───────────────────────────────────────────────────────

REQUIRED_ENVELOPE_KEYS = {
    "ok", "command", "source", "fetched_at", "cached", "count", "meta", "data", "rows",
}


def test_success_envelope_has_every_required_key():
    envelope = build_envelope("search-works", {"x": 1}, RAGGED_ROWS)
    assert REQUIRED_ENVELOPE_KEYS <= set(envelope)


def test_success_envelope_identifies_its_source():
    assert build_envelope("search-works", {}, [])["source"] == "openalex"


def test_success_envelope_marks_the_outcome_ok():
    assert build_envelope("search-works", {}, [])["ok"] is True


@pytest.mark.parametrize("row_count", [0, 1, 2, 25])
def test_envelope_count_always_equals_the_number_of_rows(row_count):
    rows = [{"openalex_id": f"W{i}"} for i in range(row_count)]
    assert build_envelope("search-works", {}, rows)["count"] == len(rows)


def test_envelope_fetched_at_is_utc_iso8601():
    assert re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
        build_envelope("search-works", {}, [])["fetched_at"],
    )


@pytest.mark.parametrize("cached", [True, False])
def test_envelope_reports_whether_the_answer_came_from_cache(cached):
    assert build_envelope("search-works", {}, [], cached=cached)["cached"] is cached


def test_envelope_data_is_an_object_even_when_the_payload_is_a_list():
    # `data` is typed as an object in the spec; a list payload would break any
    # consumer doing `envelope.data.something`.
    assert build_envelope("search-works", [1, 2, 3], [])["data"] == {}


def test_envelope_meta_carries_pagination_facts():
    meta = {"page": 1, "per_page": 10, "total": 41233}
    assert build_envelope("search-works", {}, [], meta=meta)["meta"] == meta


def test_json_render_produces_a_parseable_envelope(render_to_text):
    payload = json.loads(render_to_text("json", "get-work", {"title": "x"}, RAGGED_ROWS))
    assert payload["command"] == "get-work"
    assert payload["count"] == len(payload["rows"]) == 2


# ─── Error envelope (spec §1) ─────────────────────────────────────────────────


def test_error_envelope_has_the_required_shape():
    envelope = error_envelope("get-work", "not_found", "missing", "try another id")
    assert envelope["ok"] is False
    assert envelope["command"] == "get-work"
    assert envelope["error"] == {
        "code": "not_found",
        "message": "missing",
        "hint": "try another id",
    }


def test_error_envelope_names_its_source():
    # An agent fanning one question across several CLIs collects the failures
    # together; a failure that cannot say which tool produced it is unusable.
    assert error_envelope("get-work", "api", "m", "h")["source"] == "openalex"


def test_error_envelope_always_carries_an_actionable_hint():
    stream = io.StringIO()
    report(OpenAlexNotFoundError("no such work", status_code=404), "get-work", "json", stream)
    error = json.loads(stream.getvalue())["error"]
    assert error["hint"].strip()
    assert error["code"] == "not_found"


def test_error_in_table_mode_writes_nothing_to_the_data_stream():
    # Human mode gets the one-liner on stderr only; stdout stays clean.
    stream = io.StringIO()
    report(OpenAlexNotFoundError("nope", status_code=404), "get-work", "table", stream)
    assert stream.getvalue() == ""


# ─── UTF-8 round trip (spec §9) ───────────────────────────────────────────────


@pytest.mark.parametrize("fmt", FORMATS)
def test_accented_text_survives_every_format(fmt, render_to_text):
    # `table` clips cells at 40 characters, so this asserts on substrings short
    # enough to survive that; the untruncated round trip is checked below.
    text = render_to_text(fmt, "search-works", {}, RAGGED_ROWS)
    assert "Investigación" in text
    assert "Ñandú genomics: Côte d'Ivoire" in text


@pytest.mark.parametrize("fmt", ["json", "jsonl", "csv", "md"])
def test_accented_text_survives_untruncated_in_every_machine_format(fmt, render_to_text):
    assert ACCENTED in render_to_text(fmt, "search-works", {}, RAGGED_ROWS)


def test_json_does_not_escape_non_ascii_into_unicode_sequences():
    assert "Perú" in json.dumps(build_envelope("c", {}, RAGGED_ROWS), ensure_ascii=False)
    assert "Per\\u00fa" not in rows_to_jsonl(RAGGED_ROWS)


def test_output_file_is_written_as_utf8_regardless_of_console_encoding(tmp_path):
    path = tmp_path / "accented.jsonl"
    with Output("jsonl", str(path), quiet=True, no_color=True) as out:
        out.render("search-works", {}, RAGGED_ROWS)
    assert ACCENTED in path.read_bytes().decode("utf-8")


# ─── Streaming writer (spec §5) ───────────────────────────────────────────────


def test_row_writer_streams_one_jsonl_line_per_row():
    stream = io.StringIO()
    writer = RowWriter("jsonl", stream)
    for row in RAGGED_ROWS:
        writer.write(row)
    assert writer.count == 2
    assert [json.loads(l) for l in stream.getvalue().splitlines()] == RAGGED_ROWS


def test_row_writer_streams_csv_with_a_header_from_the_first_row():
    stream = io.StringIO()
    writer = RowWriter("csv", stream)
    for row in RAGGED_ROWS:
        writer.write(row)
    rows = list(csv.DictReader(io.StringIO(stream.getvalue())))
    # Streaming cannot see later rows, so the header is locked to row 0 and the
    # extra `doi` of row 1 is dropped rather than corrupting the column count.
    assert rows[0]["openalex_id"] == "W1"
    assert "doi" not in rows[1]
    assert len(rows) == 2


def test_row_writer_preserves_accented_text_when_streaming():
    stream = io.StringIO()
    RowWriter("jsonl", stream).write(RAGGED_ROWS[0])
    assert ACCENTED in stream.getvalue()
