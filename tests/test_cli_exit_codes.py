"""Exception → exit-code mapping (ARSENAL-SPEC §2 and §6.3).

Agents branch on the process exit status before they parse anything, so these
tests assert the *mapping*, never the wording of a message. Each case is driven
through the real exception type the client raises, not a stand-in.
"""

from __future__ import annotations

import argparse
import io
import json

import pytest

from openalex_mcp.cli import run
from openalex_mcp.cli.errors import EXIT_BY_CODE, EXIT_CODES, classify, report
from openalex_mcp.exceptions import (
    OpenAlexAPIError,
    OpenAlexAuthError,
    OpenAlexConfigError,
    OpenAlexNetworkError,
    OpenAlexNotFoundError,
    OpenAlexRateLimitError,
)
from openalex_mcp.tools import InvalidGroupByError

# The spec's table, transcribed once. If the CLI's table drifts from it, the
# manifest an agent reads becomes a lie about what the process will return.
SPEC_EXIT_CODES = {
    "0": "ok",
    "1": "api",
    "2": "usage",
    "3": "not_found",
    "4": "auth",
    "5": "rate_limit",
    "6": "network",
}


def test_published_exit_code_table_matches_the_spec():
    assert EXIT_CODES == SPEC_EXIT_CODES


def test_every_documented_code_has_an_exit_status():
    for status, code in SPEC_EXIT_CODES.items():
        assert EXIT_BY_CODE[code] == int(status)


# ─── One case per exit code ───────────────────────────────────────────────────


def test_api_error_exits_1():
    code, status, _hint = classify(OpenAlexAPIError("bad filter", status_code=400))
    assert (code, status) == ("api", 1)


def test_invalid_group_by_is_a_usage_error_and_exits_2():
    code, status, _hint = classify(InvalidGroupByError("no such field"))
    assert (code, status) == ("usage", 2)


def test_argparse_error_exits_2():
    code, status, _hint = classify(argparse.ArgumentError(None, "unrecognized"))
    assert (code, status) == ("usage", 2)


def test_not_found_exits_3():
    code, status, _hint = classify(OpenAlexNotFoundError("no such work", status_code=404))
    assert (code, status) == ("not_found", 3)


def test_auth_error_exits_4():
    code, status, _hint = classify(OpenAlexAuthError("401", status_code=401))
    assert (code, status) == ("auth", 4)


def test_missing_configuration_is_an_auth_error_and_exits_4():
    code, status, _hint = classify(OpenAlexConfigError("no key configured"))
    assert (code, status) == ("auth", 4)


def test_rate_limit_exits_5():
    code, status, _hint = classify(OpenAlexRateLimitError("429", status_code=429))
    assert (code, status) == ("rate_limit", 5)


def test_network_failure_exits_6():
    code, status, _hint = classify(OpenAlexNetworkError("connection refused"))
    assert (code, status) == ("network", 6)


def test_unknown_exception_is_internal_and_exits_1():
    code, status, _hint = classify(RuntimeError("something else"))
    assert (code, status) == ("internal", 1)


# ─── Subclass ordering ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "exc, expected",
    [
        (OpenAlexAuthError("x", status_code=401), "auth"),
        (OpenAlexNotFoundError("x", status_code=404), "not_found"),
        (OpenAlexRateLimitError("x", status_code=429), "rate_limit"),
        (OpenAlexNetworkError("x"), "network"),
    ],
)
def test_api_error_subclasses_keep_their_specific_code(exc, expected):
    # Every one of these subclasses OpenAlexAPIError; a naive isinstance chain
    # would collapse all four into "api" and exit 1 for a 404.
    assert classify(exc)[0] == expected


# ─── Hints (spec §1: every error tells the caller what to do next) ────────────


@pytest.mark.parametrize(
    "exc",
    [
        OpenAlexAPIError("x", status_code=400),
        OpenAlexAuthError("x", status_code=401),
        OpenAlexNotFoundError("x", status_code=404),
        OpenAlexRateLimitError("x", status_code=429),
        OpenAlexNetworkError("x"),
        OpenAlexConfigError("x"),
        InvalidGroupByError("x"),
        argparse.ArgumentError(None, "x"),
        RuntimeError("x"),
    ],
)
def test_every_classified_failure_carries_a_non_empty_hint(exc):
    assert classify(exc)[2].strip()


# ─── report() returns the same status it classifies ───────────────────────────


@pytest.mark.parametrize(
    "exc, status",
    [
        (OpenAlexAPIError("x", status_code=500), 1),
        (InvalidGroupByError("x"), 2),
        (OpenAlexNotFoundError("x", status_code=404), 3),
        (OpenAlexAuthError("x", status_code=403), 4),
        (OpenAlexRateLimitError("x", status_code=429), 5),
        (OpenAlexNetworkError("x"), 6),
    ],
)
def test_report_returns_the_mapped_exit_status(exc, status, capsys):
    assert report(exc, "search-works", "table") == status


def test_report_writes_the_error_envelope_to_the_data_stream_in_json_mode():
    stream = io.StringIO()
    report(OpenAlexNetworkError("dns failure"), "search-works", "json", stream)
    envelope = json.loads(stream.getvalue())
    assert envelope["ok"] is False
    assert envelope["command"] == "search-works"
    assert envelope["error"]["code"] == "network"


def test_report_writes_a_single_line_envelope_in_jsonl_mode():
    stream = io.StringIO()
    report(OpenAlexNetworkError("dns failure"), "search-works", "jsonl", stream)
    assert len(stream.getvalue().strip().splitlines()) == 1


def test_report_always_puts_a_human_one_liner_on_stderr(capsys):
    report(OpenAlexNotFoundError("gone", status_code=404), "get-work", "table")
    captured = capsys.readouterr()
    assert captured.err.startswith("openalex: not_found:")
    assert captured.out == ""


# ─── End to end through the real entry point ──────────────────────────────────


def test_a_successful_local_command_exits_0(tmp_path):
    assert run(["filter-guide", "-q", "-o", str(tmp_path / "guide.txt")]) == 0


def test_invoking_with_no_command_exits_2(capsys):
    assert run([]) == 2


def test_describing_an_unknown_command_exits_2(capsys):
    assert run(["describe", "no-such-command", "-q"]) == 2


@pytest.mark.parametrize("argv", [["--nope"], ["search-works", "-f", "bogus"], ["cache", "nope"]])
def test_argparse_rejects_bad_usage_with_status_2(argv):
    # argparse exits the process itself, before `run` can build an envelope.
    with pytest.raises(SystemExit) as excinfo:
        run(argv)
    assert excinfo.value.code == 2
