"""Aggregation tool: group works by year, type, institution, topic, etc."""

from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR

from ..client import OpenAlexClient
from ..exceptions import OpenAlexAPIError
from ..formatters import format_group_by

VALID_GROUP_FIELDS = {
    "publication_year",
    "type",
    "open_access.status",
    "language",
    "institutions.id",
    "institutions.country_code",
    "topics.id",
    "primary_location.source.id",
    "authorships.author.id",
    "is_oa",
    "has_doi",
    "has_abstract",
}


class InvalidGroupByError(ValueError):
    """Raised when group_by is not one of VALID_GROUP_FIELDS."""


async def aggregate_works(
    client: OpenAlexClient,
    group_by: str,
    filters: str = "",
    query: str = "",
) -> dict:
    """Aggregate (count/group) works by a field. Shared by the MCP tool and the CLI.

    - group_by: Field to group by, see VALID_GROUP_FIELDS.
    - filters: Comma-separated filters to scope the aggregation.
      Examples: 'institutions.id:I97018004', 'publication_year:2015-2024',
                'type:article', 'language:es'
    - query: Optional full-text search to scope the aggregation
    """
    if group_by not in VALID_GROUP_FIELDS:
        raise InvalidGroupByError(
            f"Invalid group_by value '{group_by}'. "
            f"Valid options: {', '.join(sorted(VALID_GROUP_FIELDS))}"
        )
    params: dict = {"group_by": group_by, "per_page": 200}
    if filters:
        params["filter"] = filters
    if query:
        params["search"] = query
    raw = await client.request("/works", params)
    return format_group_by(raw, group_field=group_by)


def register_aggregate_tools(mcp: FastMCP, client: OpenAlexClient) -> None:

    @mcp.tool(
        name="openalex_aggregate_works",
        description=(
            "Aggregate (count/group) works by a field to get distribution statistics. "
            "Useful for: annual publication trends, breakdown by type or language, "
            "top institutions by output, open-access percentage, topic distribution. "
            "Returns a list of {key, label, count} groups sorted by count descending. "
            "Combine with 'filters' to scope the analysis (same syntax as openalex_search_works)."
        ),
    )
    async def openalex_aggregate_works(
        group_by: str,
        filters: str = "",
        query: str = "",
    ) -> dict:
        """
        Parameters:
        - group_by: Field to group by. Options:
            'publication_year'             — annual output trends
            'type'                         — article / book / dataset / preprint ...
            'open_access.status'           — gold / green / bronze / closed
            'language'                     — en / es / zh / fr ...
            'institutions.id'              — top institutions
            'institutions.country_code'    — country breakdown
            'topics.id'                    — top research topics
            'primary_location.source.id'   — top journals
            'is_oa'                        — open access yes/no
            'has_doi'                      — DOI availability
        - filters: Comma-separated filters to scope the aggregation.
          Examples: 'institutions.id:I97018004', 'publication_year:2015-2024',
                    'type:article', 'language:es'
        - query: Optional full-text search to scope the aggregation
        """
        try:
            return await aggregate_works(client, group_by, filters, query)
        except InvalidGroupByError as exc:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(exc))) from exc
        except OpenAlexAPIError as exc:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(exc))) from exc
