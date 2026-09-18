"""CLI entry point: argument dispatch, cache wiring, and exit-code handling.

Every subcommand calls the exact same tool functions the MCP server exposes
(``openalex_mcp/tools/*.py``) — there is no separate request-building or
response-parsing logic here. Adding a capability to the server (a new core
function + register_*_tools entry) is the only thing needed before it can be
wired up as a subcommand in ``parser.py``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any, Awaitable, Callable

from dotenv import load_dotenv

from .. import cli_output as legacy
from .. import completion
from ..cache import build_cache, cache_clear, cache_dir, cache_stats
from ..client import OpenAlexClient
from ..config import OpenAlexSettings
from ..exceptions import OpenAlexAPIError
from ..resources.filter_guide import FILTER_GUIDE
from ..tools import (
    aggregate_works,
    get_author,
    get_institution,
    get_source,
    get_work,
    search_authors,
    search_institutions,
    search_sources,
    search_works,
)
from . import describe as describe_mod
from . import rows as rows_mod
from .errors import report
from .harvest import Harvester
from .parser import LOCAL_COMMANDS, SUBCOMMANDS, build_parser, parse_args
from .render import Output, RowWriter

# Which list each harvestable command scrolls, and how to ask for one page of it.
_HARVEST_LIST_KEYS = {
    "search-works": "works",
    "search-authors": "authors",
    "search-institutions": "institutions",
    "search-sources": "sources",
}


def _resolve_settings(args: argparse.Namespace) -> OpenAlexSettings:
    overrides: dict[str, Any] = {}
    if args.api_key:
        overrides["api_key"] = args.api_key
    if args.email:
        overrides["email"] = args.email
    return OpenAlexSettings(**overrides)


def _mask(secret: str) -> str:
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}...{secret[-4:]}"


def _make_client(args: argparse.Namespace, settings: OpenAlexSettings) -> OpenAlexClient:
    """CLI defaults to the disk backend — a per-invocation memory cache is dead weight."""
    backend = "none" if args.no_cache else "disk"
    return OpenAlexClient(settings, cache=build_cache(backend), refresh=args.refresh)


# ─── Local commands (no network, no auth) ─────────────────────────────────────

def _run_local(args: argparse.Namespace, out: Output) -> int:
    command = args.command

    if command == "completion":
        out.write_text(completion.generate(args.shell, "openalex", SUBCOMMANDS))
        return 0

    if command == "filter-guide":
        data = {"filter_guide": FILTER_GUIDE}
        if out.fmt == "table":
            out.write_text(FILTER_GUIDE)
            return 0
        out.render(command, data, [], meta={})
        return 0

    if command == "describe":
        manifest = describe_mod.build_manifest(args.subject)
        if args.subject and not manifest["commands"]:
            raise SystemExit(_unknown_subject(args.subject, out))
        if out.fmt == "table":
            out.write_text(describe_mod.render_human(manifest))
            return 0
        if out.fmt == "json":
            # The manifest is published bare, not enveloped: spec §4 fixes its
            # top-level shape, and an agent bootstrapping off `describe --json`
            # should not have to know about the envelope before it knows the CLI.
            out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
            return 0
        out.render(command, manifest, rows_mod.project(command, manifest), meta={})
        return 0

    if command == "cache":
        return _run_cache(args, out)

    raise AssertionError(f"Unhandled local command: {command}")


def _unknown_subject(subject: str, out: Output) -> int:
    print(f"openalex: usage: no such command '{subject}'", file=sys.stderr)
    return 2


def _run_cache(args: argparse.Namespace, out: Output) -> int:
    if args.action == "path":
        data = {"path": str(cache_dir())}
        if out.fmt == "table":
            out.write_text(data["path"])
            return 0
        out.render("cache", data, [data], meta={})
        return 0

    data = cache_clear() if args.action == "clear" else cache_stats()
    out.render("cache", data, rows_mod.project("cache", data), meta={})
    return 0


# ─── Network commands ─────────────────────────────────────────────────────────

async def _run_config(args: argparse.Namespace) -> dict:
    settings = _resolve_settings(args)
    auth_mode = "api_key" if settings.api_key else "email" if settings.email else "none"
    result: dict[str, Any] = {
        "auth_mode": auth_mode,
        "api_key_masked": _mask(settings.api_key) if settings.api_key else None,
        "email": settings.email,
        "cache_ttl": settings.cache_ttl,
        "max_retries": settings.max_retries,
        "log_level": settings.log_level,
        "cache_dir": str(cache_dir()),
    }
    if args.test:
        if auth_mode == "none":
            result["test"] = {"ok": False, "detail": "no OPENALEX_API_KEY or OPENALEX_EMAIL configured"}
        else:
            try:
                async with _make_client(args, settings) as client:
                    await client.request("/works", {"per_page": 1})
                result["test"] = {"ok": True, "detail": "GET /works succeeded"}
            except OpenAlexAPIError as exc:
                result["test"] = {"ok": False, "detail": str(exc)}
    return result


async def _run_single(args: argparse.Namespace, client: OpenAlexClient) -> dict:
    """One request per command — the non-`--all` path."""
    command = args.command
    if command == "search-works":
        return await search_works(client, args.query, args.filters, args.sort, args.per_page, args.page)
    if command == "get-work":
        return await get_work(client, args.identifier)
    if command == "search-authors":
        return await search_authors(client, args.query, args.filters, args.sort, args.per_page)
    if command == "get-author":
        return await get_author(client, args.author_id)
    if command == "search-institutions":
        return await search_institutions(client, args.query, args.country, args.institution_type, args.per_page)
    if command == "get-institution":
        return await get_institution(client, args.institution_id)
    if command == "search-sources":
        return await search_sources(client, args.query, args.filters, args.source_type, args.is_oa, args.per_page)
    if command == "get-source":
        return await get_source(client, args.source_id)
    if command == "aggregate-works":
        return await aggregate_works(client, args.group_by, args.filters, args.query)
    raise AssertionError(f"Unhandled command: {command}")


def _page_fetcher(args: argparse.Namespace, client: OpenAlexClient) -> Callable[[str, int], Awaitable[dict]]:
    command = args.command
    if command == "search-works":
        return lambda cursor, n: search_works(client, args.query, args.filters, args.sort, n, 1, cursor)
    if command == "search-authors":
        return lambda cursor, n: search_authors(client, args.query, args.filters, args.sort, n, cursor)
    if command == "search-institutions":
        return lambda cursor, n: search_institutions(
            client, args.query, args.country, args.institution_type, n, cursor
        )
    if command == "search-sources":
        return lambda cursor, n: search_sources(
            client, args.query, args.filters, args.source_type, args.is_oa, n, cursor
        )
    raise AssertionError(f"Command does not support --all: {command}")


async def _run_harvest(args: argparse.Namespace, client: OpenAlexClient, out: Output) -> int:
    command = args.command
    harvester = Harvester(
        _page_fetcher(args, client),
        _HARVEST_LIST_KEYS[command],
        max_rows=args.max_rows,
        per_page=max(args.per_page, 200) if args.per_page else 200,
        progress=out.note,
    )
    fields = rows_mod.ROW_FIELDS[command]
    out.note(f"Harvesting {command} (max {args.max_rows} rows)...")

    streaming = out.fmt in ("jsonl", "csv")
    writer = RowWriter(out.fmt, out.stream) if streaming else None
    buffered: list[dict] = []

    async for item in harvester:
        row = {k: item[k] for k in fields if k in item and item[k] is not None}
        if writer is not None:
            writer.write(row)
        else:
            buffered.append(row)

    stats = harvester.stats
    out.note(f"Done: {stats['harvested']} rows in {stats['pages']} page(s).")
    if stats["truncated"]:
        out.note(f"Stopped at --max {args.max_rows}; more rows remain.")

    if writer is None:
        meta = {**stats, **client.rate_limit_meta}
        out.render(command, {"harvest": stats}, buffered, client.any_cached, meta)
    elif out.path:
        out.note(f"Wrote {writer.count} rows -> {out.path}")
    return 0


async def _run_network(args: argparse.Namespace, out: Output) -> int:
    if args.command == "config":
        data = await _run_config(args)
        out.render("config", data, rows_mod.project("config", data), meta={},
                   table_printer=legacy.PRINTERS.get("config"))
        return 0

    settings = _resolve_settings(args)
    warning = settings.auth_warning()
    if warning:
        print(warning, file=sys.stderr)

    async with _make_client(args, settings) as client:
        if getattr(args, "fetch_all", False):
            return await _run_harvest(args, client, out)

        data = await _run_single(args, client)
        rows = rows_mod.project(args.command, data)
        meta = {**rows_mod.meta_for(args.command, data), **client.rate_limit_meta}
        out.render(args.command, data, rows, client.last_cached, meta,
                   table_printer=legacy.PRINTERS.get(args.command))
        return 0


# ─── Entry point ──────────────────────────────────────────────────────────────

def run(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parse_args(argv, parser)

    if not args.command:
        parser.print_help(sys.stderr)
        return 2

    with Output(args.format, args.output, args.quiet, args.no_color) as out:
        try:
            if args.command in LOCAL_COMMANDS:
                return _run_local(args, out)
            return asyncio.run(_run_network(args, out))
        except SystemExit as exc:  # raised by _run_local for an unknown subject
            return int(exc.code or 0)
        except KeyboardInterrupt:
            print("openalex: interrupted", file=sys.stderr)
            return 130
        except Exception as exc:  # noqa: BLE001 - every failure gets an envelope
            return report(exc, args.command, out.fmt, out.stream)


def main() -> None:
    # Windows consoles default to cp1252, which can't encode every character
    # OpenAlex returns (accented names, typographic dashes, etc.). Replace
    # rather than crash the whole command over a display glyph. When stdout is
    # redirected there is no console to appease, so force UTF-8: a piped
    # `-f jsonl` must not lose characters on its way to jq.
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream.isatty():
                stream.reconfigure(errors="replace")
            else:
                stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
    raise SystemExit(run())


if __name__ == "__main__":
    main()
