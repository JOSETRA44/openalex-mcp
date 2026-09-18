"""Flat, tabular projection of each command's result.

The envelope carries two views of the same answer: ``data`` (the nested dict the
MCP tools already return) and ``rows`` (this module). Rows must stay flat —
they feed CSV and Markdown, where a nested author list would render as a Python
repr — so single-entity commands drop their nested blocks and keep the scalars.
"""

from __future__ import annotations

from typing import Any

# Row keys per command, in display order. `describe` publishes these as
# `row_fields` so an agent can plan a --format csv extraction without a probe
# request. A row may omit a key when OpenAlex had no value for it.
ROW_FIELDS: dict[str, list[str]] = {
    "search-works": [
        "openalex_id", "title", "first_author", "publication_year", "publication_date",
        "type", "cited_by_count", "open_access", "source_name", "source_id", "doi", "language",
    ],
    "get-work": [
        "openalex_id", "title", "publication_year", "publication_date", "type",
        "cited_by_count", "open_access", "oa_url", "source_name", "source_id",
        "doi", "language", "volume", "issue", "pages", "referenced_works_count", "author_count",
    ],
    "search-authors": [
        "openalex_id", "name", "orcid", "works_count", "cited_by_count",
        "h_index", "affiliation", "country",
    ],
    "get-author": [
        "openalex_id", "name", "orcid", "works_count", "cited_by_count",
        "h_index", "i10_index", "affiliation", "affiliation_id", "country",
    ],
    "search-institutions": [
        "openalex_id", "name", "ror", "country_code", "type",
        "works_count", "cited_by_count", "homepage",
    ],
    "get-institution": [
        "openalex_id", "name", "ror", "country_code", "type",
        "works_count", "cited_by_count", "h_index", "homepage",
    ],
    "search-sources": [
        "openalex_id", "name", "issn_l", "type", "is_oa",
        "works_count", "cited_by_count", "h_index", "publisher", "homepage",
    ],
    "get-source": [
        "openalex_id", "name", "issn_l", "type", "is_oa", "is_in_doaj",
        "works_count", "cited_by_count", "h_index", "i10_index", "publisher", "homepage",
    ],
    "aggregate-works": ["key", "label", "count"],
    "config": ["auth_mode", "api_key_masked", "email", "cache_ttl", "max_retries", "log_level"],
    "cache": ["path", "entries", "live", "expired", "size_bytes", "oldest", "newest"],
    "describe": ["name", "summary", "supports_all", "row_fields"],
    "filter-guide": [],
    "completion": [],
}

# Where the list of rows lives inside each list-shaped result.
_LIST_KEYS = {
    "search-works": "works",
    "search-authors": "authors",
    "search-institutions": "institutions",
    "search-sources": "sources",
    "aggregate-works": "groups",
}


def _scalars(entity: dict, fields: list[str]) -> dict[str, Any]:
    """Keep only the requested scalar fields that the entity actually has."""
    return {k: entity[k] for k in fields if k in entity and entity[k] is not None}


def project(command: str, data: Any) -> list[dict[str, Any]]:
    """Return the flat rows for ``command``'s result ``data``."""
    if not isinstance(data, dict):
        return []

    list_key = _LIST_KEYS.get(command)
    if list_key is not None:
        fields = ROW_FIELDS[command]
        return [_scalars(item, fields) for item in data.get(list_key, [])]

    if command == "get-work":
        row = _scalars(data, ROW_FIELDS[command])
        # Authors are the one nested block worth summarizing numerically —
        # a CSV consumer still wants to know how big the byline is.
        row["author_count"] = len(data.get("authors") or [])
        return [row]

    if command in ("get-author", "get-institution", "get-source", "config"):
        return [_scalars(data, ROW_FIELDS[command])]

    if command == "cache":
        return [_scalars(data, ROW_FIELDS[command])] if data else []

    if command == "describe":
        return [
            {
                "name": c["name"],
                "summary": c["summary"],
                "supports_all": c["supports_all"],
                "row_fields": ",".join(c["row_fields"]),
            }
            for c in data.get("commands", [])
        ]

    return []


def meta_for(command: str, data: Any) -> dict[str, Any]:
    """Pagination / quota facts the API gave us, for the envelope's ``meta``."""
    if not isinstance(data, dict):
        return {}
    meta: dict[str, Any] = {}
    if "total_results" in data:
        meta["total"] = data["total_results"]
    if "page" in data:
        meta["page"] = data["page"]
    if "per_page" in data:
        meta["per_page"] = data["per_page"]
    if "next_cursor" in data:
        meta["next_cursor"] = data["next_cursor"]
    if command == "aggregate-works":
        meta["total_groups"] = data.get("total_groups")
        meta["group_by"] = data.get("group_by")
    return meta
