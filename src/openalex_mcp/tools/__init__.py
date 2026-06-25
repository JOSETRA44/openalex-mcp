from .works import register_works_tools
from .authors import register_authors_tools
from .institutions import register_institutions_tools
from .sources import register_sources_tools
from .aggregate import register_aggregate_tools

__all__ = [
    "register_works_tools",
    "register_authors_tools",
    "register_institutions_tools",
    "register_sources_tools",
    "register_aggregate_tools",
]
