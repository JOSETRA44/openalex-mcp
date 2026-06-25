"""Unit tests for formatter functions — no network required."""

import pytest
from openalex_mcp.formatters import (
    _sg,
    _strip_oa_id,
    _strip_doi,
    format_works_list,
    format_work,
    format_authors_list,
    format_author,
    format_institutions_list,
    format_institution,
    format_sources_list,
    format_source,
    format_group_by,
)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def test_sg_basic():
    assert _sg({"a": 1}, "a") == 1


def test_sg_nested():
    assert _sg({"a": {"b": 2}}, "a", "b") == 2


def test_sg_missing():
    assert _sg({}, "a", default="x") == "x"


def test_sg_none_obj():
    assert _sg(None, "a") is None


def test_sg_list_index():
    assert _sg(["x", "y"], 1) == "y"


def test_strip_oa_id():
    assert _strip_oa_id("https://openalex.org/W2741809807") == "W2741809807"
    assert _strip_oa_id("W2741809807") == "W2741809807"
    assert _strip_oa_id(None) is None


def test_strip_doi():
    assert _strip_doi("https://doi.org/10.1038/s41586") == "10.1038/s41586"
    assert _strip_doi("http://doi.org/10.1234/x") == "10.1234/x"
    assert _strip_doi("10.1234/x") == "10.1234/x"
    assert _strip_doi(None) is None


# ─── Works list ───────────────────────────────────────────────────────────────

_WORKS_LIST_RAW = {
    "meta": {"count": 100, "page": 1, "per_page": 2},
    "results": [
        {
            "id": "https://openalex.org/W2741809807",
            "doi": "https://doi.org/10.1038/s41586-021-03819-2",
            "title": "Highly accurate protein structure prediction with AlphaFold",
            "publication_year": 2021,
            "publication_date": "2021-07-15",
            "type": "article",
            "cited_by_count": 12000,
            "open_access": {"is_oa": True},
            "language": "en",
            "primary_location": {
                "source": {
                    "id": "https://openalex.org/S137773608",
                    "display_name": "Nature",
                }
            },
            "authorships": [
                {"author": {"display_name": "Jumper, J."}},
            ],
        },
        {
            "id": "https://openalex.org/W2012345678",
            "title": "Paper without DOI",
            "publication_year": 2022,
            "type": "preprint",
            "cited_by_count": 5,
            "open_access": {"is_oa": False},
            "primary_location": {},
            "authorships": [],
        },
    ],
}


def test_format_works_list_structure():
    result = format_works_list(_WORKS_LIST_RAW, query="AlphaFold")
    assert result["query"] == "AlphaFold"
    assert result["total_results"] == 100
    assert result["showing"] == 2
    assert len(result["works"]) == 2


def test_format_works_list_first_paper():
    result = format_works_list(_WORKS_LIST_RAW)
    w = result["works"][0]
    assert w["openalex_id"] == "W2741809807"
    assert w["doi"] == "10.1038/s41586-021-03819-2"
    assert w["title"] == "Highly accurate protein structure prediction with AlphaFold"
    assert w["cited_by_count"] == 12000
    assert w["open_access"] is True
    assert w["first_author"] == "Jumper, J."
    assert w["source_name"] == "Nature"


def test_format_works_list_missing_fields():
    result = format_works_list(_WORKS_LIST_RAW)
    w = result["works"][1]
    assert "doi" not in w
    assert "source_name" not in w
    assert "first_author" not in w


# ─── Single work ──────────────────────────────────────────────────────────────

_WORK_RAW = {
    "id": "https://openalex.org/W2741809807",
    "doi": "https://doi.org/10.1038/s41586-021-03819-2",
    "title": "AlphaFold",
    "abstract": "We show that...",
    "publication_year": 2021,
    "publication_date": "2021-07-15",
    "type": "article",
    "cited_by_count": 12000,
    "open_access": {"is_oa": True, "oa_url": "https://example.com/pdf"},
    "language": "en",
    "referenced_works_count": 120,
    "primary_location": {
        "source": {"id": "https://openalex.org/S137773608", "display_name": "Nature"},
        "volume": "596",
        "issue": "7873",
        "pages": "583-589",
    },
    "authorships": [
        {
            "author": {
                "display_name": "Jumper, J.",
                "id": "https://openalex.org/A2208157607",
                "orcid": "0000-0001-6169-6580",
            },
            "institutions": [{"display_name": "DeepMind"}],
        }
    ],
    "keywords": [{"display_name": "protein folding"}, {"display_name": "deep learning"}],
    "topics": [{"display_name": "Structural Biology", "id": "https://openalex.org/T10234"}],
}


def test_format_work_fields():
    w = format_work(_WORK_RAW)
    assert w["openalex_id"] == "W2741809807"
    assert w["doi"] == "10.1038/s41586-021-03819-2"
    assert w["abstract"] == "We show that..."
    assert w["cited_by_count"] == 12000
    assert w["oa_url"] == "https://example.com/pdf"
    assert w["volume"] == "596"
    assert w["pages"] == "583-589"
    assert w["referenced_works_count"] == 120


def test_format_work_authors():
    w = format_work(_WORK_RAW)
    assert len(w["authors"]) == 1
    a = w["authors"][0]
    assert a["name"] == "Jumper, J."
    assert a["openalex_id"] == "A2208157607"
    assert a["orcid"] == "0000-0001-6169-6580"
    assert a["affiliation"] == "DeepMind"


def test_format_work_keywords():
    w = format_work(_WORK_RAW)
    assert "protein folding" in w["keywords"]


def test_format_work_topics():
    w = format_work(_WORK_RAW)
    assert w["topics"][0]["name"] == "Structural Biology"
    assert w["topics"][0]["id"] == "T10234"


# ─── Authors ──────────────────────────────────────────────────────────────────

_AUTHORS_RAW = {
    "meta": {"count": 5, "page": 1, "per_page": 5},
    "results": [
        {
            "id": "https://openalex.org/A2208157607",
            "display_name": "Geoffrey Hinton",
            "orcid": "0000-0001-6169-6580",
            "works_count": 220,
            "cited_by_count": 350000,
            "summary_stats": {"h_index": 105},
            "last_known_institutions": [
                {"display_name": "Google DeepMind", "country_code": "US"}
            ],
        }
    ],
}


def test_format_authors_list():
    result = format_authors_list(_AUTHORS_RAW, query="Hinton")
    assert result["total_results"] == 5
    a = result["authors"][0]
    assert a["openalex_id"] == "A2208157607"
    assert a["name"] == "Geoffrey Hinton"
    assert a["h_index"] == 105
    assert a["affiliation"] == "Google DeepMind"


_AUTHOR_RAW = {
    "id": "https://openalex.org/A2208157607",
    "display_name": "Geoffrey Hinton",
    "orcid": "0000-0001-6169-6580",
    "works_count": 220,
    "cited_by_count": 350000,
    "summary_stats": {"h_index": 105, "i10_index": 180},
    "last_known_institutions": [{"display_name": "Google DeepMind", "id": "https://openalex.org/I123", "country_code": "US"}],
    "topics": [{"display_name": "Machine Learning", "id": "https://openalex.org/T10234"}],
    "counts_by_year": [
        {"year": 2023, "cited_by_count": 20000},
        {"year": 2022, "cited_by_count": 18000},
    ],
}


def test_format_author_full():
    a = format_author(_AUTHOR_RAW)
    assert a["name"] == "Geoffrey Hinton"
    assert a["h_index"] == 105
    assert a["i10_index"] == 180
    assert a["citations_by_year"]["2023"] == 20000
    assert a["topics"][0]["name"] == "Machine Learning"
    assert a["affiliation_id"] == "I123"


# ─── Institutions ─────────────────────────────────────────────────────────────

_INST_LIST_RAW = {
    "meta": {"count": 1, "page": 1, "per_page": 1},
    "results": [
        {
            "id": "https://openalex.org/I97018004",
            "display_name": "Stanford University",
            "ror": "https://ror.org/00f54p054",
            "country_code": "US",
            "type": "education",
            "works_count": 250000,
            "cited_by_count": 5000000,
            "homepage_url": "https://stanford.edu",
        }
    ],
}


def test_format_institutions_list():
    result = format_institutions_list(_INST_LIST_RAW, query="Stanford")
    assert result["total_results"] == 1
    i = result["institutions"][0]
    assert i["openalex_id"] == "I97018004"
    assert i["name"] == "Stanford University"
    assert i["country_code"] == "US"
    assert i["type"] == "education"


# ─── Sources ──────────────────────────────────────────────────────────────────

_SOURCE_LIST_RAW = {
    "meta": {"count": 1, "page": 1, "per_page": 1},
    "results": [
        {
            "id": "https://openalex.org/S137773608",
            "display_name": "Nature",
            "issn_l": "0028-0836",
            "type": "journal",
            "is_oa": False,
            "works_count": 90000,
            "cited_by_count": 10000000,
            "summary_stats": {"h_index": 1400},
            "host_organization_name": "Springer Nature",
        }
    ],
}


def test_format_sources_list():
    result = format_sources_list(_SOURCE_LIST_RAW, query="Nature")
    assert result["total_results"] == 1
    s = result["sources"][0]
    assert s["openalex_id"] == "S137773608"
    assert s["name"] == "Nature"
    assert s["issn_l"] == "0028-0836"
    assert s["h_index"] == 1400
    assert s["publisher"] == "Springer Nature"


# ─── Group By ─────────────────────────────────────────────────────────────────

_GROUP_BY_RAW = {
    "meta": {"count": 3},
    "group_by": [
        {"key": "2023", "key_display_name": "2023", "count": 1500},
        {"key": "2022", "key_display_name": "2022", "count": 1400},
        {"key": "2021", "key_display_name": "2021", "count": 1200},
    ],
}


def test_format_group_by():
    result = format_group_by(_GROUP_BY_RAW, group_field="publication_year")
    assert result["group_by"] == "publication_year"
    assert result["total_groups"] == 3
    assert result["groups"][0]["key"] == "2023"
    assert result["groups"][0]["count"] == 1500
