"""`describe` — the manifest that lets an agent learn this CLI without docs.

Everything here is *derived* from the argparse parser: names, help strings,
types, defaults and choices are read back off the registered actions. Nothing
is transcribed by hand, so a subcommand cannot exist and be undiscoverable at
the same time. Only the two things argparse cannot know — the row schema and
the worked examples — come from side tables (`rows.ROW_FIELDS`, `EXAMPLES`).
"""

from __future__ import annotations

import argparse
from typing import Any

from .. import __version__
from ..client import BASE_URL
from .errors import EXIT_CODES
from .parser import FORMATS, GLOBAL_DEFAULTS, LOCAL_COMMANDS, build_parser
from .rows import ROW_FIELDS

# Copy-pasteable invocations, one or two per command. A test parses every one
# of these through the real parser, so a stale example fails the build.
EXAMPLES: dict[str, list[str]] = {
    "search-works": [
        "openalex search-works 'graph neural networks' -f jsonl --all --max 500",
        "openalex search-works --filters 'publication_year:2024,type:article' -n 200 -f csv -o works.csv",
    ],
    "get-work": [
        "openalex get-work 10.1038/s41586-021-03819-2 -f json",
        "openalex get-work W2741809807 -f md",
    ],
    "search-authors": [
        "openalex search-authors 'Geoffrey Hinton' -n 5 -f json",
        "openalex search-authors --filters 'last_known_institutions.id:I97018004' --all --max 1000 -f jsonl",
    ],
    "get-author": ["openalex get-author A5023888391 -f json"],
    "search-institutions": [
        "openalex search-institutions --country PE --type education --all --max 300 -f csv -o pe_unis.csv",
    ],
    "get-institution": ["openalex get-institution I97018004 -f json"],
    "search-sources": [
        "openalex search-sources Nature --type journal --oa -f md",
    ],
    "get-source": ["openalex get-source 1476-4687 -f json"],
    "aggregate-works": [
        "openalex aggregate-works publication_year --filters 'institutions.id:I97018004' -f csv",
        "openalex aggregate-works institutions.country_code --query 'machine learning' -f json",
    ],
    "filter-guide": ["openalex filter-guide"],
    "describe": ["openalex describe --json", "openalex describe search-works --json"],
    "cache": ["openalex cache stats -f json", "openalex cache clear"],
    "config": ["openalex config --test -f json"],
    "completion": ["openalex completion bash"],
}


def _type_name(action: argparse.Action) -> str:
    if isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction)):
        return "boolean"
    if action.type is int:
        return "integer"
    if action.choices:
        return "enum"
    return "string"


# argparse hides these from --help; the manifest still has to explain them,
# since a hidden flag an agent cannot discover is a flag it will never use.
_HIDDEN_HELP = {"json": "Legacy alias for --format json (hidden from --help)"}

# GLOBAL_DEFAULTS stores format=None so parse_args can tell "unset" from an
# explicit choice; what an agent needs to read is the effective default.
_DEFAULT_DISPLAY = {"format": "table"}


def _describe_action(action: argparse.Action) -> dict[str, Any]:
    hidden = (action.help or "") == argparse.SUPPRESS
    help_text = _HIDDEN_HELP.get(action.dest, "(hidden)") if hidden else (action.help or "")
    default = action.default
    if default is argparse.SUPPRESS:
        # Global flags carry SUPPRESS so subparsers cannot clobber them;
        # their real defaults live in GLOBAL_DEFAULTS.
        default = _DEFAULT_DISPLAY.get(action.dest, GLOBAL_DEFAULTS.get(action.dest))
    entry: dict[str, Any] = {
        "name": action.option_strings[0] if action.option_strings else action.dest,
        "type": _type_name(action),
        "required": bool(action.required) if action.option_strings else action.nargs not in ("?", "*"),
        "default": default,
        "help": help_text,
    }
    if hidden:
        entry["hidden"] = True
    if action.option_strings:
        entry["aliases"] = action.option_strings
        entry["repeatable"] = action.nargs in ("*", "+")
    if action.choices:
        entry["choices"] = list(action.choices)
    return entry


def _subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    raise AssertionError("parser registers no subcommands")


def build_manifest(command: str = "") -> dict[str, Any]:
    """Walk the parser and return the machine-readable manifest."""
    parser = build_parser()
    sub = _subparsers(parser)
    summaries = {a.dest: (a.help or "") for a in sub._choices_actions}

    commands: list[dict[str, Any]] = []
    for name, subparser in sub.choices.items():
        if command and name != command:
            continue
        arguments, options = [], []
        for action in subparser._actions:
            if isinstance(action, argparse._HelpAction):
                continue
            # Global flags are documented once at the top level, not per command.
            if action.dest in GLOBAL_DEFAULTS and action.option_strings:
                continue
            (arguments if not action.option_strings else options).append(_describe_action(action))
        commands.append({
            "name": name,
            "summary": summaries.get(name, ""),
            "arguments": arguments,
            "options": options,
            "row_fields": ROW_FIELDS.get(name, []),
            "supports_all": any(a.dest == "fetch_all" for a in subparser._actions),
            # Spec §4: a command answered from local state is never reported as
            # `cached`; a caller that cannot tell it apart from a network
            # command would read that as a broken cache.
            "network": name not in LOCAL_COMMANDS,
            "examples": EXAMPLES.get(name, []),
        })

    globals_ = [
        _describe_action(a)
        for a in parser._actions
        if a.option_strings and a.dest in GLOBAL_DEFAULTS
    ]

    return {
        "name": parser.prog,
        "version": __version__,
        "source": {"api": "OpenAlex", "base_url": BASE_URL, "auth": "optional"},
        "formats": list(FORMATS),
        "exit_codes": EXIT_CODES,
        "globals": globals_,
        "commands": commands,
    }


def render_human(manifest: dict[str, Any]) -> str:
    """Compact human summary — the `describe` output without --format json."""
    lines = [
        f"{manifest['name']} {manifest['version']} - "
        f"{manifest['source']['api']} ({manifest['source']['base_url']})",
        f"formats: {', '.join(manifest['formats'])}",
        f"exit codes: {', '.join(f'{k}={v}' for k, v in manifest['exit_codes'].items())}",
        "",
        "commands:",
    ]
    for cmd in manifest["commands"]:
        bulk = "  [--all]" if cmd["supports_all"] else ""
        lines.append(f"  {cmd['name']:<22}{cmd['summary']}{bulk}")
        if cmd["row_fields"]:
            lines.append(f"    rows: {', '.join(cmd['row_fields'])}")
        for example in cmd["examples"]:
            lines.append(f"    $ {example}")
    lines.append("")
    lines.append("globals: " + ", ".join(g["name"] for g in manifest["globals"]))
    return "\n".join(lines) + "\n"
