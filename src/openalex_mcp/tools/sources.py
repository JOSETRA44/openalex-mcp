"""Tools for searching journals, conferences, and other publication sources in OpenAlex."""

from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR

from ..client import OpenAlexClient
from ..exceptions import OpenAlexAPIError
from ..formatters import format_sources_list, format_source


def register_sources_tools(mcp: FastMCP, client: OpenAlexClient) -> None:

    @mcp.tool(
        name="openalex_search_sources",
        description=(
            "Search journals, conference proceedings, repositories, and other publication venues "
            "in OpenAlex. Returns ISSN, publisher, open-access status, h-index, works count, "
            "and citation count. Use the returned 'openalex_id' in work filters: "
            "'primary_location.source.id:{id}'"
        ),
    )
    async def openalex_search_sources(
        query: str = "",
        filters: str = "",
        source_type: str = "",
        is_oa: bool | None = None,
        per_page: int = 10,
    ) -> dict:
        """
        Parameters:
        - query: Name search (e.g. 'Nature', 'PLOS ONE', 'NeurIPS')
        - filters: Additional comma-separated filter expressions
        - source_type: 'journal', 'repository', 'conference', 'book series', 'ebook platform'
        - is_oa: True to show only open-access sources
        - per_page: Results per page (1–200, default 10)
        """
        per_page = max(1, min(200, per_page))
        params: dict = {"per_page": per_page}
        if query:
            params["search"] = query
        filter_parts = []
        if filters:
            filter_parts.append(filters)
        if source_type:
            filter_parts.append(f"type:{source_type}")
        if is_oa is not None:
            filter_parts.append(f"is_oa:{'true' if is_oa else 'false'}")
        if filter_parts:
            params["filter"] = ",".join(filter_parts)
        try:
            raw = await client.request("/sources", params)
            return format_sources_list(raw, query=query)
        except OpenAlexAPIError as exc:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(exc))) from exc

    @mcp.tool(
        name="openalex_get_source",
        description=(
            "Get full details for a journal, conference, or repository: ISSN, publisher, "
            "open-access status, DOAJ listing, total works, citations, h-index, i10-index, "
            "and top research topics. Accepts OpenAlex Source ID (S-number) or ISSN."
        ),
    )
    async def openalex_get_source(source_id: str) -> dict:
        """
        Parameters:
        - source_id: OpenAlex ID ('S2764455111'), ISSN ('1476-4687'),
                     or full URL ('https://openalex.org/S2764455111')
        """
        ident = source_id.strip()
        if ident.startswith("https://openalex.org/"):
            ident = ident.rsplit("/", 1)[-1]

        if ident.startswith("S") and ident[1:].isdigit():
            path = f"/sources/{ident}"
        elif "-" in ident and len(ident) == 9 and ident.replace("-", "").isdigit():
            # ISSN format: XXXX-XXXX
            path = f"/sources/issn:{ident}"
        else:
            path = f"/sources/{ident}"

        try:
            raw = await client.request(path)
            return format_source(raw)
        except OpenAlexAPIError as exc:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(exc))) from exc
