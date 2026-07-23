"""Tools for searching and retrieving institution data from OpenAlex."""

from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR

from ..client import OpenAlexClient
from ..exceptions import OpenAlexAPIError
from ..formatters import format_institutions_list, format_institution


async def search_institutions(
    client: OpenAlexClient,
    query: str = "",
    country_code: str = "",
    institution_type: str = "",
    per_page: int = 10,
) -> dict:
    """Search universities, research institutes, and other organizations. Shared by the MCP tool and the CLI.

    - query: Name search (e.g. 'MIT', 'Harvard', 'UNAM')
    - country_code: ISO 2-letter country code (e.g. 'US', 'GB', 'PE', 'MX', 'DE')
    - institution_type: 'education', 'healthcare', 'company', 'government',
                        'nonprofit', 'facility', 'archive', 'other'
    - per_page: Results per page (1-200, default 10)
    """
    per_page = max(1, min(200, per_page))
    params: dict = {"per_page": per_page}
    if query:
        params["search"] = query
    filter_parts = []
    if country_code:
        filter_parts.append(f"country_code:{country_code.upper()}")
    if institution_type:
        filter_parts.append(f"type:{institution_type}")
    if filter_parts:
        params["filter"] = ",".join(filter_parts)
    raw = await client.request("/institutions", params)
    return format_institutions_list(raw, query=query)


def _institution_path(institution_id: str) -> str:
    ident = institution_id.strip()
    if ident.startswith("https://openalex.org/"):
        ident = ident.rsplit("/", 1)[-1]

    if ident.startswith("I") and ident[1:].isdigit():
        return f"/institutions/{ident}"
    if "ror.org" in ident:
        return f"/institutions/ror:{ident}"
    return f"/institutions/{ident}"


async def get_institution(client: OpenAlexClient, institution_id: str) -> dict:
    """Retrieve full details for a university or research institution. Shared by the MCP tool and the CLI.

    - institution_id: OpenAlex ID ('I97018004'), ROR ID ('https://ror.org/00f54p054'),
                      or full URL ('https://openalex.org/I97018004')
    """
    raw = await client.request(_institution_path(institution_id))
    return format_institution(raw)


def register_institutions_tools(mcp: FastMCP, client: OpenAlexClient) -> None:

    @mcp.tool(
        name="openalex_search_institutions",
        description=(
            "Search universities, research institutes, hospitals, and other organizations in OpenAlex. "
            "Returns the OpenAlex institution ID (needed for work filters), ROR ID, name, country, "
            "type, and publication/citation counts. "
            "Use the returned 'openalex_id' in openalex_search_works filter: "
            "'institutions.id:{id}'"
        ),
    )
    async def openalex_search_institutions(
        query: str = "",
        country_code: str = "",
        institution_type: str = "",
        per_page: int = 10,
    ) -> dict:
        """
        Parameters:
        - query: Name search (e.g. 'MIT', 'Harvard', 'UNAM')
        - country_code: ISO 2-letter country code (e.g. 'US', 'GB', 'PE', 'MX', 'DE')
        - institution_type: 'education', 'healthcare', 'company', 'government',
                            'nonprofit', 'facility', 'archive', 'other'
        - per_page: Results per page (1–200, default 10)
        """
        try:
            return await search_institutions(client, query, country_code, institution_type, per_page)
        except OpenAlexAPIError as exc:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(exc))) from exc

    @mcp.tool(
        name="openalex_get_institution",
        description=(
            "Retrieve full details for a university or research institution: name, country, type, "
            "ROR ID, total works, total citations, h-index, homepage URL, and top research topics. "
            "Accepts an OpenAlex Institution ID (I-number) or ROR ID."
        ),
    )
    async def openalex_get_institution(institution_id: str) -> dict:
        """
        Parameters:
        - institution_id: OpenAlex ID ('I97018004'), ROR ID ('https://ror.org/00f54p054'),
                          or full URL ('https://openalex.org/I97018004')
        """
        try:
            return await get_institution(client, institution_id)
        except OpenAlexAPIError as exc:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(exc))) from exc
