"""Static MCP resource: OpenAlex filter syntax reference."""

from mcp.server.fastmcp import FastMCP

FILTER_GUIDE = """# OpenAlex Filter & Query Syntax Reference

## Base URL
`https://api.openalex.org/{entity}?filter=...&search=...&sort=...&per_page=N&page=N`

## Entities
`/works` · `/authors` · `/institutions` · `/sources` · `/topics` · `/publishers` · `/funders`

---

## Filter Syntax

Filters are comma-separated `field:value` expressions:
```
filter=type:article,publication_year:2020-2024,open_access.is_oa:true
```

### Operators
| Operator | Meaning | Example |
|----------|---------|---------|
| `:`      | equals  | `type:article` |
| `!:`     | not equals | `!type:book` |
| `>` `<` `>=` `<=` | numeric comparison | `cited_by_count:>100` |
| `X-Y`   | range   | `publication_year:2018-2023` |
| `.search:` | text search within field | `title.search:machine learning` |

---

## Works Filters (`/works`)

### Content
| Filter | Type | Example |
|--------|------|---------|
| `title.search:` | text | `title.search:cancer immunotherapy` |
| `abstract.search:` | text | `abstract.search:neural network` |
| `fulltext.search:` | text | `fulltext.search:carbon capture` |
| `keyword.search:` | text | `keyword.search:climate change` |

### Identifiers
| Filter | Example |
|--------|---------|
| `doi:` | `doi:10.1038/s41586-021-03819-2` |
| `pmid:` | `pmid:34512593` |
| `openalex:` | `openalex:W2741809807` |

### Classification
| Filter | Values |
|--------|--------|
| `type:` | `article`, `book`, `dataset`, `preprint`, `dissertation`, `book-chapter`, `review`, `paratext`, `other` |
| `language:` | ISO 639-1 code: `en`, `es`, `zh`, `fr`, `de`, `pt`, `ar`, `ru`, `ja` |
| `publication_year:` | year or range: `2023`, `2018-2023`, `>2020` |

### Access & Availability
| Filter | Example |
|--------|---------|
| `open_access.is_oa:` | `open_access.is_oa:true` |
| `open_access.status:` | `gold`, `green`, `bronze`, `hybrid`, `closed` |
| `has_doi:` | `has_doi:true` |
| `has_abstract:` | `has_abstract:true` |
| `has_fulltext:` | `has_fulltext:true` |

### Authors & Institutions
| Filter | Example |
|--------|---------|
| `author.id:` | `author.id:A2208157607` |
| `author.orcid:` | `author.orcid:0000-0002-1825-0097` |
| `institutions.id:` | `institutions.id:I97018004` |
| `institutions.country_code:` | `institutions.country_code:US` |
| `institutions.type:` | `institutions.type:education` |
| `authorships.author.id:` | (same as author.id) |

### Topics & Concepts
| Filter | Example |
|--------|---------|
| `topics.id:` | `topics.id:T10234` |
| `concepts.id:` | `concepts.id:C41008148` (deprecated, use topics) |
| `primary_topic.id:` | `primary_topic.id:T10234` |

### Publication Venue
| Filter | Example |
|--------|---------|
| `primary_location.source.id:` | `primary_location.source.id:S2764455111` |
| `primary_location.source.issn:` | `primary_location.source.issn:0028-0836` |
| `journal.id:` | shorthand for source |

### Impact
| Filter | Example |
|--------|---------|
| `cited_by_count:` | `cited_by_count:>100`, `cited_by_count:50-500` |
| `referenced_works_count:` | `referenced_works_count:>20` |

---

## Authors Filters (`/authors`)

| Filter | Example |
|--------|---------|
| `display_name.search:` | `display_name.search:Hinton` |
| `last_known_institutions.id:` | `last_known_institutions.id:I97018004` |
| `last_known_institutions.country_code:` | `last_known_institutions.country_code:US` |
| `orcid:` | `orcid:0000-0002-1825-0097` |
| `has_orcid:` | `has_orcid:true` |
| `works_count:` | `works_count:>50` |
| `cited_by_count:` | `cited_by_count:>1000` |

---

## Institutions Filters (`/institutions`)

| Filter | Example |
|--------|---------|
| `display_name.search:` | `display_name.search:Stanford` |
| `country_code:` | `country_code:PE` |
| `type:` | `type:education` |
| `ror:` | `ror:00f54p054` |
| `works_count:` | `works_count:>1000` |

Institution types: `education`, `healthcare`, `company`, `government`, `nonprofit`, `facility`, `archive`, `other`

---

## Sources Filters (`/sources`)

| Filter | Example |
|--------|---------|
| `display_name.search:` | `display_name.search:Nature` |
| `issn:` | `issn:0028-0836` |
| `type:` | `type:journal` |
| `is_oa:` | `is_oa:true` |
| `is_in_doaj:` | `is_in_doaj:true` |
| `host_organization.id:` | `host_organization.id:P4310320595` |

---

## Sorting

`sort=field:direction` where direction is `asc` or `desc`.

### Works sort fields
- `cited_by_count:desc` — most-cited first
- `publication_date:desc` — newest first
- `relevance_score:desc` — most relevant (only with `search=`)
- `publication_year:asc`

### Authors sort fields
- `cited_by_count:desc`
- `works_count:desc`
- `h_index:desc` (summary_stats.h_index)

---

## Group By (Aggregation)

Add `group_by=field` to count records by a category:

```
/works?filter=institutions.id:I97018004&group_by=publication_year
→ [{"key":"2023","count":1234}, {"key":"2022","count":1156}, ...]
```

### Valid group_by fields for /works
- `publication_year` — annual trends
- `type` — article/book/dataset breakdown
- `open_access.status` — gold/green/bronze/closed
- `language` — language distribution
- `institutions.id` — top contributing institutions
- `institutions.country_code` — country breakdown
- `topics.id` — top research areas
- `primary_location.source.id` — top journals
- `is_oa` — open access yes/no split
- `has_doi` — DOI coverage

---

## Pagination

| Param | Description | Default |
|-------|-------------|---------|
| `per_page` | Results per page | 25 |
| `page` | Page number (1-indexed) | 1 |
| `cursor` | Cursor for deep pagination (use meta.next_cursor) | — |

Max `per_page`: 200 for list; use cursor for >10,000 results.

---

## Logical Operators

Multiple values for the same field → pipe-separated OR:
```
filter=institutions.country_code:US|GB|CA
```

Exclude values with `!`:
```
filter=!type:book,type:article
```

Combine multiple fields with comma (implicit AND):
```
filter=type:article,language:en,open_access.is_oa:true,publication_year:>2020
```

---

## Common Query Patterns

```bash
# Recent open-access ML papers
/works?search=machine+learning&filter=open_access.is_oa:true,publication_year:>2021&sort=cited_by_count:desc

# All works from an institution in 2023
/works?filter=institutions.id:I97018004,publication_year:2023&sort=cited_by_count:desc

# Top-cited authors at a university
/authors?filter=last_known_institutions.id:I97018004&sort=cited_by_count:desc

# Annual publication trend for a topic
/works?search=CRISPR&group_by=publication_year

# Open journals in a field
/sources?search=bioinformatics&filter=type:journal,is_oa:true&sort=cited_by_count:desc

# Papers citing a specific work
/works?filter=cites:W2741809807&sort=cited_by_count:desc
```
"""


def register_resources(mcp: FastMCP) -> None:
    @mcp.resource("openalex://filter-reference")
    def filter_reference() -> str:
        """Complete OpenAlex filter syntax, operators, and query examples."""
        return FILTER_GUIDE
