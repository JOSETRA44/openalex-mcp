"""`describe` manifest tests (ARSENAL-SPEC §4 and §6.5).

The manifest is the only thing an agent reads before driving this CLI, so the
expectations below are *derived from the argparse parser itself*: registering a
new subcommand without teaching `describe` about it must fail the suite, and a
manifest example that no longer parses must fail it too.
"""

from __future__ import annotations

import argparse
import json
import shlex

import pytest

from openalex_mcp import __version__
from openalex_mcp.cli import run
from openalex_mcp.cli.describe import EXAMPLES, build_manifest, render_human
from openalex_mcp.cli.errors import EXIT_CODES
from openalex_mcp.cli.parser import (
    FORMATS,
    LOCAL_COMMANDS,
    PAGINATED_COMMANDS,
    SUBCOMMANDS,
    build_parser,
    parse_args,
)
from openalex_mcp.cli.rows import ROW_FIELDS


def registered_subcommands() -> set[str]:
    """The set of subcommands argparse actually knows about — the ground truth."""
    parser = build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    raise AssertionError("parser registers no subcommands")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return build_manifest()


def command_names(manifest: dict) -> set[str]:
    return {c["name"] for c in manifest["commands"]}


# ─── Coverage of the command surface ──────────────────────────────────────────


def test_manifest_lists_every_subcommand_the_parser_registers(manifest):
    assert command_names(manifest) == registered_subcommands()


def test_manifest_invents_no_command_the_parser_does_not_have(manifest):
    for name in command_names(manifest):
        assert name in registered_subcommands()


def test_completion_subcommand_list_matches_the_parser(manifest):
    # `SUBCOMMANDS` feeds the shell-completion script; drifting from the parser
    # would silently stop completing a real command.
    assert set(SUBCOMMANDS) == registered_subcommands()


def test_every_command_carries_a_summary(manifest):
    for command in manifest["commands"]:
        assert command["summary"].strip(), command["name"]


def test_every_command_declares_its_argument_and_option_lists(manifest):
    for command in manifest["commands"]:
        assert isinstance(command["arguments"], list)
        assert isinstance(command["options"], list)


def test_supports_all_is_true_exactly_for_the_paginated_commands(manifest):
    flagged = {c["name"] for c in manifest["commands"] if c["supports_all"]}
    assert flagged == set(PAGINATED_COMMANDS)


def test_every_command_says_whether_it_touches_the_network(manifest):
    # Spec §4: a command answered from local state is correctly never reported
    # as `cached`, and a caller that cannot tell the two apart reads that as a
    # broken cache.
    offline = {c["name"] for c in manifest["commands"] if not c["network"]}
    assert offline == set(LOCAL_COMMANDS)


def test_row_fields_are_published_for_every_row_producing_command(manifest):
    for command in manifest["commands"]:
        assert command["row_fields"] == ROW_FIELDS.get(command["name"], [])


def test_search_works_publishes_the_columns_a_csv_extraction_will_get(manifest):
    entry = next(c for c in manifest["commands"] if c["name"] == "search-works")
    assert entry["row_fields"][:3] == ["openalex_id", "title", "first_author"]


# ─── Top-level manifest fields ────────────────────────────────────────────────


def test_manifest_declares_all_five_formats(manifest):
    assert manifest["formats"] == ["table", "json", "jsonl", "csv", "md"]
    assert manifest["formats"] == list(FORMATS)


def test_manifest_documents_all_seven_exit_codes(manifest):
    assert manifest["exit_codes"] == EXIT_CODES
    assert sorted(manifest["exit_codes"]) == ["0", "1", "2", "3", "4", "5", "6"]


def test_manifest_identifies_the_cli_and_its_upstream(manifest):
    assert manifest["name"] == "openalex"
    assert manifest["version"] == __version__
    assert manifest["source"]["base_url"] == "https://api.openalex.org"


def test_manifest_documents_the_global_flags(manifest):
    names = {g["name"] for g in manifest["globals"]}
    assert {"-f", "-o", "-q", "--no-color", "--refresh", "--no-cache"} <= names


def test_manifest_documents_the_hidden_legacy_json_alias(manifest):
    entry = next(g for g in manifest["globals"] if g["name"] == "--json")
    # A hidden flag an agent cannot discover is a flag it will never use.
    assert entry["hidden"] is True
    assert entry["help"].strip()


def test_manifest_reports_the_effective_default_format_not_the_sentinel(manifest):
    entry = next(g for g in manifest["globals"] if g["name"] == "-f")
    assert entry["default"] == "table"
    assert entry["choices"] == list(FORMATS)


def test_manifest_is_json_serializable(manifest):
    assert json.loads(json.dumps(manifest)) == manifest


# ─── Examples (spec §6.5) ─────────────────────────────────────────────────────


def all_examples() -> list[str]:
    return [example for examples in EXAMPLES.values() for example in examples]


def test_every_command_ships_at_least_one_example(manifest):
    for command in manifest["commands"]:
        assert command["examples"], command["name"]


@pytest.mark.parametrize("example", all_examples(), ids=lambda e: e[:60])
def test_every_documented_example_parses_through_the_real_parser(example):
    tokens = shlex.split(example)
    assert tokens[0] == "openalex"
    try:
        args = parse_args(tokens[1:], build_parser())
    except SystemExit as exc:  # argparse rejected it
        pytest.fail(f"example does not parse: {example} (exit {exc.code})")
    assert args.command == tokens[1]


def test_examples_only_reference_registered_commands():
    assert set(EXAMPLES) <= registered_subcommands()


def test_an_example_using_the_legacy_json_alias_resolves_to_format_json():
    assert parse_args(["describe", "--json"]).format == "json"


# ─── Single-command manifests ─────────────────────────────────────────────────


def test_describing_one_command_returns_only_that_command():
    single = build_manifest("search-works")
    assert command_names(single) == {"search-works"}


def test_describing_an_unknown_command_returns_no_commands():
    assert build_manifest("no-such-command")["commands"] == []


@pytest.mark.parametrize("name", sorted(registered_subcommands()))
def test_every_command_can_be_described_individually(name):
    assert command_names(build_manifest(name)) == {name}


# ─── Human rendering and the CLI path ─────────────────────────────────────────


def test_human_describe_mentions_every_command(manifest):
    text = render_human(manifest)
    for name in command_names(manifest):
        assert name in text


def test_describe_json_prints_the_bare_manifest_not_an_envelope(tmp_path):
    path = tmp_path / "manifest.json"
    assert run(["describe", "--json", "-q", "-o", str(path)]) == 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    # An agent bootstrapping off `describe --json` should not have to know
    # about the envelope before it knows the CLI.
    assert "ok" not in payload
    assert command_names(payload) == registered_subcommands()


def test_describe_table_output_is_human_readable(tmp_path):
    path = tmp_path / "manifest.txt"
    assert run(["describe", "-q", "-o", str(path)]) == 0
    assert "commands:" in path.read_text(encoding="utf-8")
