"""Pure functions to transform raw OpenAlex JSON into clean AI-friendly dicts."""

from typing import Any


def _sg(obj: Any, *keys: str | int, default: Any = None) -> Any:
    """Safe nested access for dicts and lists."""
    for key in keys:
        if obj is None:
            return default
        try:
            obj = obj[key]
        except (KeyError, IndexError, TypeError):
            return default
    return obj if obj is not None else default


def _strip_oa_id(raw_id: str | None) -> str | None:
    """Convert 'https://openalex.org/W123' → 'W123'."""
    if not raw_id:
        return None
    return raw_id.rsplit("/", 1)[-1]


def _strip_doi(raw: str | None) -> str | None:
    """Normalize DOI: 'https://doi.org/10.x/y' → '10.x/y'."""
    if not raw:
        return None
    raw = raw.strip()
    if raw.startswith("https://doi.org/"):
        return raw[len("https://doi.org/"):]
    if raw.startswith("http://doi.org/"):
        return raw[len("http://doi.org/"):]
    return raw


def _author_name(authorship: dict) -> str | None:
    return _sg(authorship, "author", "display_name")


# ─── Works ────────────────────────────────────────────────────────────────────

def format_works_list(raw: dict, query: str = "") -> dict:
    """Format a /works list response."""
    meta = _sg(raw, "meta") or {}
    results = _sg(raw, "results") or []
    papers = []
    for w in results:
        loc = _sg(w, "primary_location") or {}
        source = _sg(loc, "source") or {}
        authorships = _sg(w, "authorships") or []
        first_author = _author_name(authorships[0]) if authorships else None
        papers.append({
            k: v for k, v in {
                "openalex_id": _strip_oa_id(_sg(w, "id")),
                "doi": _strip_doi(_sg(w, "doi")),
                "title": _sg(w, "title"),
                "first_author": first_author,
                "publication_year": _sg(w, "publication_year"),
                "publication_date": _sg(w, "publication_date"),
                "type": _sg(w, "type"),
                "cited_by_count": _sg(w, "cited_by_count"),
                "open_access": _sg(w, "open_access", "is_oa"),
                "source_name": _sg(source, "display_name"),
                "source_id": _strip_oa_id(_sg(source, "id")),
                "language": _sg(w, "language"),
            }.items() if v is not None
        })
    return {
        "query": query,
        "total_results": _sg(meta, "count", default=0),
        "showing": len(papers),
        "page": _sg(meta, "page", default=1),
        "per_page": _sg(meta, "per_page", default=len(papers)),
        "works": papers,
    }


def format_work(raw: dict) -> dict:
    """Format a single /works/{id} response."""
    loc = _sg(raw, "primary_location") or {}
    source = _sg(loc, "source") or {}
    authorships = _sg(raw, "authorships") or []
    authors = []
    for a in authorships:
        author = _sg(a, "author") or {}
        inst_list = _sg(a, "institutions") or []
        affiliation = _sg(inst_list, 0, "display_name")
        authors.append({
            k: v for k, v in {
                "name": _sg(author, "display_name"),
                "openalex_id": _strip_oa_id(_sg(author, "id")),
                "orcid": _sg(author, "orcid"),
                "affiliation": affiliation,
            }.items() if v is not None
        })
    keywords = [_sg(k, "display_name") for k in (_sg(raw, "keywords") or [])]
    topics = [
        {"name": _sg(t, "display_name"), "id": _strip_oa_id(_sg(t, "id"))}
        for t in (_sg(raw, "topics") or [])[:5]
        if _sg(t, "display_name")
    ]
    return {
        k: v for k, v in {
            "openalex_id": _strip_oa_id(_sg(raw, "id")),
            "doi": _strip_doi(_sg(raw, "doi")),
            "title": _sg(raw, "title"),
            "abstract": _sg(raw, "abstract"),
            "publication_year": _sg(raw, "publication_year"),
            "publication_date": _sg(raw, "publication_date"),
            "type": _sg(raw, "type"),
            "cited_by_count": _sg(raw, "cited_by_count"),
            "open_access": _sg(raw, "open_access", "is_oa"),
            "oa_url": _sg(raw, "open_access", "oa_url"),
            "language": _sg(raw, "language"),
            "authors": authors,
            "keywords": [k for k in keywords if k] or None,
            "topics": topics or None,
            "source_name": _sg(source, "display_name"),
            "source_id": _strip_oa_id(_sg(source, "id")),
            "volume": _sg(loc, "volume"),
            "issue": _sg(loc, "issue"),
            "pages": _sg(loc, "pages"),
            "referenced_works_count": _sg(raw, "referenced_works_count"),
        }.items() if v is not None
    }


# ─── Authors ──────────────────────────────────────────────────────────────────

def format_authors_list(raw: dict, query: str = "") -> dict:
    meta = _sg(raw, "meta") or {}
    results = _sg(raw, "results") or []
    authors = []
    for a in results:
        inst = _sg(a, "last_known_institutions", 0) or {}
        authors.append({
            k: v for k, v in {
                "openalex_id": _strip_oa_id(_sg(a, "id")),
                "name": _sg(a, "display_name"),
                "orcid": _sg(a, "orcid"),
                "works_count": _sg(a, "works_count"),
                "cited_by_count": _sg(a, "cited_by_count"),
                "h_index": _sg(a, "summary_stats", "h_index"),
                "affiliation": _sg(inst, "display_name"),
                "country": _sg(inst, "country_code"),
            }.items() if v is not None
        })
    return {
        "query": query,
        "total_results": _sg(meta, "count", default=0),
        "showing": len(authors),
        "authors": authors,
    }


def format_author(raw: dict) -> dict:
    inst = _sg(raw, "last_known_institutions", 0) or {}
    topics = [
        {"name": _sg(t, "display_name"), "id": _strip_oa_id(_sg(t, "id"))}
        for t in (_sg(raw, "topics") or [])[:5]
        if _sg(t, "display_name")
    ]
    counts_by_year = {
        str(_sg(y, "year")): _sg(y, "cited_by_count")
        for y in (_sg(raw, "counts_by_year") or [])
        if _sg(y, "year") is not None
    }
    return {
        k: v for k, v in {
            "openalex_id": _strip_oa_id(_sg(raw, "id")),
            "name": _sg(raw, "display_name"),
            "orcid": _sg(raw, "orcid"),
            "works_count": _sg(raw, "works_count"),
            "cited_by_count": _sg(raw, "cited_by_count"),
            "h_index": _sg(raw, "summary_stats", "h_index"),
            "i10_index": _sg(raw, "summary_stats", "i10_index"),
            "affiliation": _sg(inst, "display_name"),
            "affiliation_id": _strip_oa_id(_sg(inst, "id")),
            "country": _sg(inst, "country_code"),
            "topics": topics or None,
            "citations_by_year": counts_by_year or None,
        }.items() if v is not None
    }


# ─── Institutions ─────────────────────────────────────────────────────────────

def format_institutions_list(raw: dict, query: str = "") -> dict:
    meta = _sg(raw, "meta") or {}
    results = _sg(raw, "results") or []
    institutions = []
    for i in results:
        institutions.append({
            k: v for k, v in {
                "openalex_id": _strip_oa_id(_sg(i, "id")),
                "name": _sg(i, "display_name"),
                "ror": _sg(i, "ror"),
                "country_code": _sg(i, "country_code"),
                "type": _sg(i, "type"),
                "works_count": _sg(i, "works_count"),
                "cited_by_count": _sg(i, "cited_by_count"),
                "homepage": _sg(i, "homepage_url"),
            }.items() if v is not None
        })
    return {
        "query": query,
        "total_results": _sg(meta, "count", default=0),
        "showing": len(institutions),
        "institutions": institutions,
    }


def format_institution(raw: dict) -> dict:
    topics = [
        {"name": _sg(t, "display_name"), "id": _strip_oa_id(_sg(t, "id"))}
        for t in (_sg(raw, "topics") or [])[:10]
        if _sg(t, "display_name")
    ]
    return {
        k: v for k, v in {
            "openalex_id": _strip_oa_id(_sg(raw, "id")),
            "name": _sg(raw, "display_name"),
            "ror": _sg(raw, "ror"),
            "country_code": _sg(raw, "country_code"),
            "type": _sg(raw, "type"),
            "homepage": _sg(raw, "homepage_url"),
            "works_count": _sg(raw, "works_count"),
            "cited_by_count": _sg(raw, "cited_by_count"),
            "h_index": _sg(raw, "summary_stats", "h_index"),
            "topics": topics or None,
            "image_url": _sg(raw, "image_url"),
        }.items() if v is not None
    }


# ─── Sources ──────────────────────────────────────────────────────────────────

def format_sources_list(raw: dict, query: str = "") -> dict:
    meta = _sg(raw, "meta") or {}
    results = _sg(raw, "results") or []
    sources = []
    for s in results:
        sources.append({
            k: v for k, v in {
                "openalex_id": _strip_oa_id(_sg(s, "id")),
                "name": _sg(s, "display_name"),
                "issn_l": _sg(s, "issn_l"),
                "type": _sg(s, "type"),
                "is_oa": _sg(s, "is_oa"),
                "works_count": _sg(s, "works_count"),
                "cited_by_count": _sg(s, "cited_by_count"),
                "h_index": _sg(s, "summary_stats", "h_index"),
                "publisher": _sg(s, "host_organization_name"),
                "homepage": _sg(s, "homepage_url"),
            }.items() if v is not None
        })
    return {
        "query": query,
        "total_results": _sg(meta, "count", default=0),
        "showing": len(sources),
        "sources": sources,
    }


def format_source(raw: dict) -> dict:
    topics = [
        {"name": _sg(t, "display_name"), "id": _strip_oa_id(_sg(t, "id"))}
        for t in (_sg(raw, "topics") or [])[:10]
        if _sg(t, "display_name")
    ]
    return {
        k: v for k, v in {
            "openalex_id": _strip_oa_id(_sg(raw, "id")),
            "name": _sg(raw, "display_name"),
            "issn_l": _sg(raw, "issn_l"),
            "issn": _sg(raw, "issn"),
            "type": _sg(raw, "type"),
            "is_oa": _sg(raw, "is_oa"),
            "is_in_doaj": _sg(raw, "is_in_doaj"),
            "works_count": _sg(raw, "works_count"),
            "cited_by_count": _sg(raw, "cited_by_count"),
            "h_index": _sg(raw, "summary_stats", "h_index"),
            "i10_index": _sg(raw, "summary_stats", "i10_index"),
            "publisher": _sg(raw, "host_organization_name"),
            "homepage": _sg(raw, "homepage_url"),
            "topics": topics or None,
        }.items() if v is not None
    }


# ─── Aggregation ──────────────────────────────────────────────────────────────

def format_group_by(raw: dict, group_field: str) -> dict:
    groups = _sg(raw, "group_by") or []
    meta = _sg(raw, "meta") or {}
    items = [
        {
            "key": _sg(g, "key"),
            "label": _sg(g, "key_display_name") or _sg(g, "key"),
            "count": _sg(g, "count"),
        }
        for g in groups
        if _sg(g, "key") is not None
    ]
    return {
        "group_by": group_field,
        "total_groups": _sg(meta, "count", default=len(items)),
        "groups": items,
    }
