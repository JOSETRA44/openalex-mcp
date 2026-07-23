"""Command-line interface for OpenAlex.

Every subcommand calls the exact same tool functions the MCP server exposes
(src/openalex_mcp/tools/*.py) — there is no separate request-building or
response-parsing logic here. Adding a new capability to the MCP server (a new
core function + register_*_tools entry) is the only thing needed before it
can also be wired up as a subcommand below.
"""

import argparse
import asyncio
import sys

from dotenv import load_dotenv

from . import __version__
from .client import OpenAlexClient
from .config import OpenAlexSettings
from .exceptions import OpenAlexAPIError, OpenAlexConfigError
from .resources.filter_guide import FILTER_GUIDE
from .tools import (
    VALID_GROUP_FIELDS,
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
from . import cli_output as out


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openalex",
        description=(
            "Query the OpenAlex scholarly database (250M+ works, 300M+ authors, "
            "100K+ institutions, 250K+ sources) from the terminal."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--json", action="store_true", help="Print raw JSON instead of a table")
    parser.add_argument("--api-key", help="OpenAlex API key (overrides OPENALEX_API_KEY)")
    parser.add_argument("--email", help="Contact email for the polite pool (overrides OPENALEX_EMAIL)")

    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p = sub.add_parser("search-works", help="Search scholarly works (articles, books, datasets, preprints)")
    p.add_argument("query", nargs="?", default="", help="Free-text search (title + abstract)")
    p.add_argument("-f", "--filters", default="", help="Comma-separated filters, e.g. 'publication_year:>2020,type:article'")
    p.add_argument("-s", "--sort", default="relevance_score:desc", help="e.g. 'cited_by_count:desc', 'publication_date:desc'")
    p.add_argument("-n", "--per-page", type=int, default=10, help="Results per page (1-200, default 10)")
    p.add_argument("-p", "--page", type=int, default=1, help="Page number (default 1)")

    p = sub.add_parser("get-work", help="Full metadata for one work")
    p.add_argument("identifier", help="OpenAlex ID (W...), DOI, or 'pmid:12345678'")

    p = sub.add_parser("search-authors", help="Search researchers by name, institution, ORCID, etc.")
    p.add_argument("query", nargs="?", default="", help="Name search, e.g. 'Geoffrey Hinton'")
    p.add_argument("-f", "--filters", default="", help="Comma-separated filters, e.g. 'works_count:>50'")
    p.add_argument("-s", "--sort", default="cited_by_count:desc", help="e.g. 'works_count:desc', 'h_index:desc'")
    p.add_argument("-n", "--per-page", type=int, default=10, help="Results per page (1-200, default 10)")

    p = sub.add_parser("get-author", help="Full profile for one researcher")
    p.add_argument("author_id", help="OpenAlex Author ID (A...) or ORCID")

    p = sub.add_parser("search-institutions", help="Search universities, hospitals, and other organizations")
    p.add_argument("query", nargs="?", default="", help="Name search, e.g. 'MIT'")
    p.add_argument("-c", "--country", default="", help="ISO 2-letter country code, e.g. 'US'")
    p.add_argument("-t", "--type", default="", dest="institution_type",
                    help="education | healthcare | company | government | nonprofit | facility | archive | other")
    p.add_argument("-n", "--per-page", type=int, default=10, help="Results per page (1-200, default 10)")

    p = sub.add_parser("get-institution", help="Full details for one institution")
    p.add_argument("institution_id", help="OpenAlex ID (I...) or ROR ID")

    p = sub.add_parser("search-sources", help="Search journals, conferences, and repositories")
    p.add_argument("query", nargs="?", default="", help="Name search, e.g. 'Nature'")
    p.add_argument("-f", "--filters", default="", help="Additional comma-separated filters")
    p.add_argument("-t", "--type", default="", dest="source_type",
                    help="journal | repository | conference | book series | ebook platform")
    oa = p.add_mutually_exclusive_group()
    oa.add_argument("--oa", dest="is_oa", action="store_true", default=None, help="Only open-access sources")
    oa.add_argument("--no-oa", dest="is_oa", action="store_false", help="Only closed-access sources")
    p.add_argument("-n", "--per-page", type=int, default=10, help="Results per page (1-200, default 10)")

    p = sub.add_parser("get-source", help="Full details for one journal/conference/repository")
    p.add_argument("source_id", help="OpenAlex ID (S...) or ISSN")

    p = sub.add_parser("aggregate-works", help="Count/group works by year, type, institution, topic, etc.")
    p.add_argument("group_by", choices=sorted(VALID_GROUP_FIELDS), help="Field to group by")
    p.add_argument("-f", "--filters", default="", help="Comma-separated filters to scope the aggregation")
    p.add_argument("-q", "--query", default="", help="Optional full-text search to scope the aggregation")

    sub.add_parser("filter-guide", help="Print the full OpenAlex filter syntax reference")

    return parser


async def _run(args: argparse.Namespace) -> dict | None:
    if args.command == "filter-guide":
        return None

    overrides: dict = {}
    if args.api_key:
        overrides["api_key"] = args.api_key
    if args.email:
        overrides["email"] = args.email
    settings = OpenAlexSettings(**overrides)
    settings.validate_auth()

    async with OpenAlexClient(settings) as client:
        if args.command == "search-works":
            return await search_works(client, args.query, args.filters, args.sort, args.per_page, args.page)
        if args.command == "get-work":
            return await get_work(client, args.identifier)
        if args.command == "search-authors":
            return await search_authors(client, args.query, args.filters, args.sort, args.per_page)
        if args.command == "get-author":
            return await get_author(client, args.author_id)
        if args.command == "search-institutions":
            return await search_institutions(client, args.query, args.country, args.institution_type, args.per_page)
        if args.command == "get-institution":
            return await get_institution(client, args.institution_id)
        if args.command == "search-sources":
            return await search_sources(client, args.query, args.filters, args.source_type, args.is_oa, args.per_page)
        if args.command == "get-source":
            return await get_source(client, args.source_id)
        if args.command == "aggregate-works":
            return await aggregate_works(client, args.group_by, args.filters, args.query)

    raise AssertionError(f"Unhandled command: {args.command}")


def main() -> None:
    # Windows consoles default to cp1252, which can't encode every character
    # OpenAlex returns (accented names, typographic dashes, etc.). Replace
    # rather than crash the whole command over a display glyph.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass

    load_dotenv()
    parser = _build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        raise SystemExit(1)

    if args.command == "filter-guide":
        if args.json:
            out.print_json({"filter_guide": FILTER_GUIDE})
        else:
            out.print_filter_guide(FILTER_GUIDE)
        return

    try:
        result = asyncio.run(_run(args))
    except OpenAlexConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    except OpenAlexAPIError as exc:
        print(f"OpenAlex API error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except KeyboardInterrupt:
        raise SystemExit(130) from None

    if args.json:
        out.print_json(result)
    else:
        out.PRINTERS[args.command](result)


if __name__ == "__main__":
    main()
