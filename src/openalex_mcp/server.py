"""FastMCP entry point for the OpenAlex MCP server."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from .config import get_settings
from .client import OpenAlexClient
from .exceptions import OpenAlexConfigError
from .tools import (
    register_works_tools,
    register_authors_tools,
    register_institutions_tools,
    register_sources_tools,
    register_aggregate_tools,
)
from .resources import register_resources

_INSTRUCTIONS = """
You have access to OpenAlex, the world's largest open scholarly database with 250+ million works,
300+ million authors, 100,000+ institutions, 250,000+ sources, and billions of citation links.

All data is freely available (CC0) — no paywall, no institutional access required.

## Tools available
- openalex_search_works     — keyword + filter search over scholarly works
- openalex_get_work         — full metadata for one work (DOI, OpenAlex ID, PubMed ID)
- openalex_search_authors   — find researchers by name, institution, or metrics
- openalex_get_author       — full author profile (h-index, i10-index, citations by year)
- openalex_search_institutions — find universities and research organizations
- openalex_get_institution  — institution details (country, type, h-index, top topics)
- openalex_search_sources   — find journals, conference proceedings, repositories
- openalex_get_source       — source details (ISSN, publisher, OA status, h-index)
- openalex_aggregate_works  — count/group works by year, type, country, topic, etc.

## Resource available
- openalex://filter-reference — complete filter syntax guide with 100+ examples

## Typical workflows
1. Literature search: openalex_search_works(query="...", filters="publication_year:>2020")
2. Author profile: openalex_search_authors → openalex_get_author
3. Institution output: openalex_search_institutions → openalex_aggregate_works(filters="institutions.id:...")
4. Citation trends: openalex_get_work → openalex_aggregate_works(group_by="publication_year", filters="cites:W...")
5. Journal analysis: openalex_search_sources → openalex_search_works(filters="primary_location.source.id:...")

## Key filter patterns
- `institutions.id:I97018004` — by institution (use openalex_search_institutions to find IDs)
- `publication_year:2020-2024` — year range
- `type:article` — works type
- `open_access.is_oa:true` — open access only
- `cited_by_count:>100` — highly cited papers
- `cites:W2741809807` — papers that cite a specific work
""".strip()


def create_app() -> FastMCP:
    settings = get_settings()
    settings.validate_auth()

    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

    client = OpenAlexClient(settings)

    @asynccontextmanager
    async def lifespan(_app: FastMCP) -> AsyncIterator[None]:
        async with client:
            yield

    mcp = FastMCP(
        "OpenAlex Research Assistant",
        instructions=_INSTRUCTIONS,
        lifespan=lifespan,
    )

    register_works_tools(mcp, client)
    register_authors_tools(mcp, client)
    register_institutions_tools(mcp, client)
    register_sources_tools(mcp, client)
    register_aggregate_tools(mcp, client)
    register_resources(mcp)

    return mcp


def main() -> None:
    load_dotenv()
    try:
        app = create_app()
    except OpenAlexConfigError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc
    app.run(transport="stdio")
