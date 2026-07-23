"""Tools for searching and retrieving author profiles from OpenAlex."""

from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR

from ..client import OpenAlexClient
from ..exceptions import OpenAlexAPIError
from ..formatters import format_authors_list, format_author


async def search_authors(
    client: OpenAlexClient,
    query: str = "",
    filters: str = "",
    sort: str = "cited_by_count:desc",
    per_page: int = 10,
) -> dict:
    """Search researchers/authors. Shared by the MCP tool and the CLI.

    - query: Name search (e.g. 'Geoffrey Hinton', 'Hinton')
    - filters: Comma-separated filters.
      Examples: 'last_known_institutions.id:I97018004', 'orcid:0000-0002-XXXX',
                'works_count:>50', 'cited_by_count:>1000', 'has_orcid:true'
    - sort: 'cited_by_count:desc', 'works_count:desc', 'h_index:desc'
    - per_page: Results per page (1-200, default 10)
    """
    per_page = max(1, min(200, per_page))
    params: dict = {"per_page": per_page}
    if query:
        params["search"] = query
    if filters:
        params["filter"] = filters
    if sort:
        params["sort"] = sort
    raw = await client.request("/authors", params)
    return format_authors_list(raw, query=query or filters)


def _author_path(author_id: str) -> str:
    ident = author_id.strip()
    if ident.startswith("https://openalex.org/"):
        ident = ident.rsplit("/", 1)[-1]

    if ident.startswith("A") and ident[1:].isdigit():
        return f"/authors/{ident}"
    if ident.startswith("0000-"):
        return f"/authors/orcid:{ident}"
    return f"/authors/{ident}"


async def get_author(client: OpenAlexClient, author_id: str) -> dict:
    """Retrieve the full profile for a researcher. Shared by the MCP tool and the CLI.

    - author_id: OpenAlex Author ID ('A2208157607'), ORCID ('0000-0002-1825-0097'),
                 or full URL ('https://openalex.org/A2208157607')
    """
    raw = await client.request(_author_path(author_id))
    return format_author(raw)


def register_authors_tools(mcp: FastMCP, client: OpenAlexClient) -> None:

    @mcp.tool(
        name="openalex_search_authors",
        description=(
            "Search researchers/authors in OpenAlex by name or filter by institution, ORCID, "
            "citation count, etc. Returns OpenAlex ID, name, ORCID, h-index, works count, "
            "cited-by count, and current affiliation. Use openalex_get_author for full profile."
        ),
    )
    async def openalex_search_authors(
        query: str = "",
        filters: str = "",
        sort: str = "cited_by_count:desc",
        per_page: int = 10,
    ) -> dict:
        """
        Parameters:
        - query: Name search (e.g. 'Geoffrey Hinton', 'Hinton')
        - filters: Comma-separated filters.
          Examples: 'last_known_institutions.id:I97018004', 'orcid:0000-0002-XXXX',
                    'works_count:>50', 'cited_by_count:>1000', 'has_orcid:true'
        - sort: 'cited_by_count:desc', 'works_count:desc', 'h_index:desc'
        - per_page: Results per page (1–200, default 10)
        """
        try:
            return await search_authors(client, query, filters, sort, per_page)
        except OpenAlexAPIError as exc:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(exc))) from exc

    @mcp.tool(
        name="openalex_get_author",
        description=(
            "Retrieve the full profile for a researcher: name, ORCID, h-index, i10-index, "
            "works count, total citations, last known affiliation, top research topics, "
            "and year-by-year citation counts. "
            "Accepts an OpenAlex Author ID (A-number) or ORCID."
        ),
    )
    async def openalex_get_author(author_id: str) -> dict:
        """
        Parameters:
        - author_id: OpenAlex Author ID ('A2208157607'), ORCID ('0000-0002-1825-0097'),
                     or full URL ('https://openalex.org/A2208157607')
        """
        try:
            return await get_author(client, author_id)
        except OpenAlexAPIError as exc:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(exc))) from exc
