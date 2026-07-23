from .works import register_works_tools, search_works, get_work
from .authors import register_authors_tools, search_authors, get_author
from .institutions import register_institutions_tools, search_institutions, get_institution
from .sources import register_sources_tools, search_sources, get_source
from .aggregate import register_aggregate_tools, aggregate_works, InvalidGroupByError, VALID_GROUP_FIELDS

__all__ = [
    "register_works_tools",
    "register_authors_tools",
    "register_institutions_tools",
    "register_sources_tools",
    "register_aggregate_tools",
    # Core tool functions — shared by the MCP server and the CLI.
    "search_works",
    "get_work",
    "search_authors",
    "get_author",
    "search_institutions",
    "get_institution",
    "search_sources",
    "get_source",
    "aggregate_works",
    "InvalidGroupByError",
    "VALID_GROUP_FIELDS",
]
