"""Tools for searching and retrieving scholarly works from OpenAlex."""

from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR

from ..client import OpenAlexClient
from ..exceptions import OpenAlexAPIError
from ..formatters import format_works_list, format_work


def register_works_tools(mcp: FastMCP, client: OpenAlexClient) -> None:

    @mcp.tool(
        name="openalex_search_works",
        description=(
            "Search scholarly works (articles, books, datasets, preprints, theses) in OpenAlex. "
            "Use 'query' for full-text keyword search. Use 'filters' to narrow by year, type, "
            "institution, open access, citation count, etc. "
            "Filter syntax: 'publication_year:2020-2024,type:article,open_access.is_oa:true'. "
            "Sort options: 'cited_by_count:desc', 'publication_date:desc', 'relevance_score:desc'. "
            "Returns title, DOI, authors, year, citation count, open-access status."
        ),
    )
    async def openalex_search_works(
        query: str = "",
        filters: str = "",
        sort: str = "relevance_score:desc",
        per_page: int = 10,
        page: int = 1,
    ) -> dict:
        """
        Parameters:
        - query: Free-text search (title + abstract). Leave empty to use filters only.
        - filters: Comma-separated OpenAlex filter expressions.
          Examples: 'publication_year:>2020', 'type:article', 'institutions.id:I97018004',
                    'open_access.is_oa:true', 'cited_by_count:>100', 'language:en'
        - sort: Sort order. Options: 'cited_by_count:desc', 'publication_date:desc',
                'relevance_score:desc' (only with query), 'cited_by_count:asc'
        - per_page: Results per page (1–200, default 10)
        - page: Page number for pagination (default 1)
        """
        per_page = max(1, min(200, per_page))
        params: dict = {"per_page": per_page, "page": page}
        if query:
            params["search"] = query
        if filters:
            params["filter"] = filters
        if sort and sort != "relevance_score:desc" or not query:
            params["sort"] = sort if sort else "cited_by_count:desc"
        elif query:
            params["sort"] = sort
        try:
            raw = await client.request("/works", params)
            return format_works_list(raw, query=query or filters)
        except OpenAlexAPIError as exc:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(exc))) from exc

    @mcp.tool(
        name="openalex_get_work",
        description=(
            "Retrieve full metadata for a single scholarly work. Accepts an OpenAlex ID (W-number), "
            "DOI (bare '10.x/y' or full URL), PubMed ID ('pmid:12345678'), or MAG ID. "
            "Returns title, abstract, all authors with affiliations, topics, citation count, "
            "open-access URL, referenced works count, and more."
        ),
    )
    async def openalex_get_work(identifier: str) -> dict:
        """
        Parameters:
        - identifier: One of:
            - OpenAlex ID: 'W2741809807' or 'https://openalex.org/W2741809807'
            - DOI: '10.1038/s41586-021-03819-2' or 'https://doi.org/10.1038/...'
            - PubMed ID: 'pmid:34512593'
        """
        ident = identifier.strip()
        # Normalize DOI → openalex doi: path
        if ident.startswith("https://doi.org/"):
            ident = ident[len("https://doi.org/"):]
        if ident.startswith("http://doi.org/"):
            ident = ident[len("http://doi.org/"):]

        if ident.startswith("W") and ident[1:].isdigit():
            path = f"/works/{ident}"
        elif ident.startswith("https://openalex.org/"):
            path = f"/works/{ident.rsplit('/', 1)[-1]}"
        elif ident.lower().startswith("pmid:"):
            path = f"/works/pmid:{ident[5:]}"
        else:
            # Assume DOI
            from urllib.parse import quote
            path = f"/works/https://doi.org/{quote(ident, safe='/:@!$&()*+,;=')}"

        try:
            raw = await client.request(path)
            return format_work(raw)
        except OpenAlexAPIError as exc:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(exc))) from exc
