"""Argparse definition for the `openalex` CLI.

This is the single source of truth for the command surface: `describe` walks
this parser to build its machine-readable manifest, so a new subcommand becomes
discoverable to agents the moment it is registered here — no second list to
keep in sync.

Global flags live on a parent parser that is attached both to the root parser
and to every subparser. That is what lets `openalex -f json search-works X` and
`openalex search-works X -f json` mean the same thing. The parent's defaults are
SUPPRESS so a subparser never clobbers a value the root already parsed.
"""

from __future__ import annotations

import argparse

from .. import __version__
from ..tools import VALID_GROUP_FIELDS

FORMATS = ("table", "json", "jsonl", "csv", "md")

# Commands that never touch the network — handled before any client/auth setup.
LOCAL_COMMANDS = frozenset({"filter-guide", "completion", "describe", "cache"})

# Commands backed by a cursor-paginated endpoint, hence `--all` / `--max`.
PAGINATED_COMMANDS = frozenset(
    {"search-works", "search-authors", "search-institutions", "search-sources"}
)

SUBCOMMANDS = [
    "search-works", "get-work", "search-authors", "get-author",
    "search-institutions", "get-institution", "search-sources", "get-source",
    "aggregate-works", "filter-guide", "describe", "cache", "config", "completion",
]

# Defaults for the global flags. They cannot live on the parser itself: the
# parent is attached twice, so whichever copy parses last would reset the other.
GLOBAL_DEFAULTS: dict[str, object] = {
    "format": None,
    "output": None,
    "quiet": False,
    "no_color": False,
    "refresh": False,
    "no_cache": False,
    "json": False,
    "api_key": None,
    "email": None,
}


def _global_options() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    g = parent.add_argument_group("global options")
    g.add_argument("-f", "--format", choices=FORMATS, default=argparse.SUPPRESS,
                   help="Output format (default: table)")
    g.add_argument("-o", "--output", metavar="FILE", default=argparse.SUPPRESS,
                   help="Write output to FILE instead of stdout")
    g.add_argument("-q", "--quiet", action="store_true", default=argparse.SUPPRESS,
                   help="Suppress progress and notes on stderr")
    g.add_argument("--no-color", action="store_true", default=argparse.SUPPRESS,
                   help="Disable ANSI colour (also honours NO_COLOR)")
    g.add_argument("--refresh", action="store_true", default=argparse.SUPPRESS,
                   help="Ignore the cache, refetch, and rewrite it")
    g.add_argument("--no-cache", action="store_true", default=argparse.SUPPRESS,
                   help="Neither read nor write the cache")
    g.add_argument("--api-key", default=argparse.SUPPRESS,
                   help="OpenAlex API key (overrides OPENALEX_API_KEY)")
    g.add_argument("--email", default=argparse.SUPPRESS,
                   help="Contact email for the polite pool (overrides OPENALEX_EMAIL)")
    # Legacy flag, kept working as a hidden alias for --format json.
    g.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                   help=argparse.SUPPRESS)
    return parent


def _add_bulk_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--all", action="store_true", dest="fetch_all",
                   help="Page through the whole result set with cursor pagination")
    p.add_argument("--max", type=int, default=1000, dest="max_rows", metavar="N",
                   help="Hard ceiling on harvested rows (default 1000)")


def build_parser() -> argparse.ArgumentParser:
    common = _global_options()
    parser = argparse.ArgumentParser(
        prog="openalex",
        parents=[common],
        description=(
            "Query the OpenAlex scholarly database (250M+ works, 300M+ authors, "
            "100K+ institutions, 250K+ sources) from the terminal."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", metavar="<command>")

    def add(name: str, help_text: str) -> argparse.ArgumentParser:
        return sub.add_parser(name, help=help_text, parents=[common])

    p = add("search-works", "Search scholarly works (articles, books, datasets, preprints)")
    p.add_argument("query", nargs="?", default="", help="Free-text search (title + abstract)")
    p.add_argument("--filters", default="", help="Comma-separated filters, e.g. 'publication_year:>2020,type:article'")
    p.add_argument("-s", "--sort", default="relevance_score:desc", help="e.g. 'cited_by_count:desc', 'publication_date:desc'")
    p.add_argument("-n", "--per-page", type=int, default=10, help="Results per page (1-200, default 10)")
    p.add_argument("-p", "--page", type=int, default=1, help="Page number (default 1)")
    _add_bulk_flags(p)

    p = add("get-work", "Full metadata for one work")
    p.add_argument("identifier", help="OpenAlex ID (W...), DOI, or 'pmid:12345678'")

    p = add("search-authors", "Search researchers by name, institution, ORCID, etc.")
    p.add_argument("query", nargs="?", default="", help="Name search, e.g. 'Geoffrey Hinton'")
    p.add_argument("--filters", default="", help="Comma-separated filters, e.g. 'works_count:>50'")
    p.add_argument("-s", "--sort", default="cited_by_count:desc", help="e.g. 'works_count:desc', 'h_index:desc'")
    p.add_argument("-n", "--per-page", type=int, default=10, help="Results per page (1-200, default 10)")
    _add_bulk_flags(p)

    p = add("get-author", "Full profile for one researcher")
    p.add_argument("author_id", help="OpenAlex Author ID (A...) or ORCID")

    p = add("search-institutions", "Search universities, hospitals, and other organizations")
    p.add_argument("query", nargs="?", default="", help="Name search, e.g. 'MIT'")
    p.add_argument("-c", "--country", default="", help="ISO 2-letter country code, e.g. 'US'")
    p.add_argument("-t", "--type", default="", dest="institution_type",
                   help="education | healthcare | company | government | nonprofit | facility | archive | other")
    p.add_argument("-n", "--per-page", type=int, default=10, help="Results per page (1-200, default 10)")
    _add_bulk_flags(p)

    p = add("get-institution", "Full details for one institution")
    p.add_argument("institution_id", help="OpenAlex ID (I...) or ROR ID")

    p = add("search-sources", "Search journals, conferences, and repositories")
    p.add_argument("query", nargs="?", default="", help="Name search, e.g. 'Nature'")
    p.add_argument("--filters", default="", help="Additional comma-separated filters")
    p.add_argument("-t", "--type", default="", dest="source_type",
                   help="journal | repository | conference | book series | ebook platform")
    oa = p.add_mutually_exclusive_group()
    oa.add_argument("--oa", dest="is_oa", action="store_true", default=None, help="Only open-access sources")
    oa.add_argument("--no-oa", dest="is_oa", action="store_false", help="Only closed-access sources")
    p.add_argument("-n", "--per-page", type=int, default=10, help="Results per page (1-200, default 10)")
    _add_bulk_flags(p)

    p = add("get-source", "Full details for one journal/conference/repository")
    p.add_argument("source_id", help="OpenAlex ID (S...) or ISSN")

    p = add("aggregate-works", "Count/group works by year, type, institution, topic, etc.")
    p.add_argument("group_by", choices=sorted(VALID_GROUP_FIELDS), help="Field to group by")
    p.add_argument("--filters", default="", help="Comma-separated filters to scope the aggregation")
    p.add_argument("--query", default="", help="Optional full-text search to scope the aggregation")

    add("filter-guide", "Print the full OpenAlex filter syntax reference")

    p = add("describe", "Print a machine-readable manifest of every command (for agents)")
    p.add_argument("subject", nargs="?", default="", metavar="COMMAND",
                   help="Describe only this command")

    p = add("cache", "Inspect or clear the persistent on-disk response cache")
    p.add_argument("action", choices=["stats", "clear", "path"], help="What to do with the cache")

    p = add("config", "Show resolved settings and check whether OpenAlex auth is configured")
    p.add_argument("--test", action="store_true", help="Make a live request to confirm the key/email actually works")

    p = add("completion", "Print a shell completion script")
    p.add_argument("shell", choices=["bash", "zsh", "powershell"])

    return parser


def parse_args(
    argv: list[str] | None = None,
    parser: argparse.ArgumentParser | None = None,
) -> argparse.Namespace:
    """Parse ``argv`` and backfill the SUPPRESS-ed global defaults."""
    args = (parser or build_parser()).parse_args(argv)
    for name, default in GLOBAL_DEFAULTS.items():
        if not hasattr(args, name):
            setattr(args, name, default)
    # --json survives as a hidden alias; an explicit --format always wins.
    if args.format is None:
        args.format = "json" if args.json else "table"
    return args
