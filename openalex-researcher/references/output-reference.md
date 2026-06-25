# OpenAlex MCP Output Field Reference

## `openalex_search_works` Output

```json
{
  "query": "the search query or filter string",
  "total_results": 48219,
  "showing": 10,
  "page": 1,
  "per_page": 10,
  "works": [ ...see Work Summary Object below... ]
}
```

### Work Summary Object (in search results)

| Field | Type | Description |
|-------|------|-------------|
| `openalex_id` | string | OpenAlex ID (e.g. "W2741809807") |
| `doi` | string? | DOI without "https://doi.org/" prefix |
| `title` | string | Full work title |
| `first_author` | string? | "Surname, Initials" of first author |
| `publication_year` | int | Year of publication |
| `publication_date` | string? | ISO date "YYYY-MM-DD" |
| `type` | string | article / preprint / book / dataset / dissertation / book-chapter |
| `cited_by_count` | int | Number of works citing this one |
| `open_access` | bool | Whether freely readable online |
| `source_name` | string? | Journal/venue name |
| `source_id` | string? | OpenAlex Source ID ("S...") |
| `language` | string? | ISO 639-1 language code (en/es/zh...) |

**Notes:**
- Absent fields are omitted (not null) to keep output clean
- `cited_by_count` is the best single impact proxy
- Use `openalex_get_work` on any `openalex_id` to get the full record

---

## `openalex_get_work` Output

```json
{
  "openalex_id": "W2741809807",
  "doi": "10.1038/s41586-021-03819-2",
  "title": "Highly accurate protein structure prediction with AlphaFold",
  "abstract": "Full abstract text, often several paragraphs...",
  "publication_year": 2021,
  "publication_date": "2021-07-15",
  "type": "article",
  "cited_by_count": 12000,
  "open_access": true,
  "oa_url": "https://europepmc.org/articles/pmc8371605",
  "language": "en",
  "authors": [
    {
      "name": "Jumper, J.",
      "openalex_id": "A2208157607",
      "orcid": "0000-0001-6169-6580",
      "affiliation": "DeepMind"
    }
  ],
  "keywords": ["protein folding", "deep learning", "structural biology"],
  "topics": [
    {"name": "Structural Biology", "id": "T10234"},
    {"name": "Machine Learning", "id": "T12456"}
  ],
  "source_name": "Nature",
  "source_id": "S137773608",
  "volume": "596",
  "issue": "7873",
  "pages": "583-589",
  "referenced_works_count": 120
}
```

**Notes:**
- `abstract` is the complete text (no truncation)
- `oa_url` is the direct link to a free PDF/HTML (when available)
- `authors` is always a list (even single-author works)
- `pii` and `pubmed_id` appear when available
- `topics` limited to top 5 most relevant

---

## `openalex_search_authors` Output

```json
{
  "query": "Geoffrey Hinton",
  "total_results": 3,
  "showing": 3,
  "authors": [
    {
      "openalex_id": "A2208157607",
      "name": "Geoffrey Hinton",
      "orcid": "0000-0001-6169-6580",
      "works_count": 220,
      "cited_by_count": 350000,
      "h_index": 105,
      "affiliation": "Google DeepMind",
      "country": "US"
    }
  ]
}
```

**Notes:**
- Use `openalex_id` in `openalex_get_author` for full profile
- `h_index` comes from `summary_stats.h_index` in the raw API

---

## `openalex_get_author` Output

```json
{
  "openalex_id": "A2208157607",
  "name": "Geoffrey Hinton",
  "orcid": "0000-0001-6169-6580",
  "works_count": 220,
  "cited_by_count": 350000,
  "h_index": 105,
  "i10_index": 180,
  "affiliation": "Google DeepMind",
  "affiliation_id": "I1340965",
  "country": "US",
  "topics": [
    {"name": "Machine Learning", "id": "T10234"},
    {"name": "Neural Networks", "id": "T10235"}
  ],
  "citations_by_year": {
    "2024": 25000,
    "2023": 22000,
    "2022": 20000,
    "2021": 18000,
    "2020": 15000
  }
}
```

**Notes:**
- `cited_by_count` = unique works that cited any paper by this author
- `i10_index` = number of papers with at least 10 citations
- `citations_by_year` keys are string years

---

## `openalex_search_institutions` Output

```json
{
  "query": "MIT",
  "total_results": 5,
  "showing": 5,
  "institutions": [
    {
      "openalex_id": "I63966007",
      "name": "Massachusetts Institute of Technology",
      "ror": "https://ror.org/042nb2s44",
      "country_code": "US",
      "type": "education",
      "works_count": 285000,
      "cited_by_count": 8000000,
      "homepage": "https://mit.edu"
    }
  ]
}
```

**Notes:**
- Use `openalex_id` in work filters: `institutions.id:I63966007`
- `ror` is the ROR (Research Organization Registry) identifier

---

## `openalex_get_institution` Output

```json
{
  "openalex_id": "I97018004",
  "name": "Stanford University",
  "ror": "https://ror.org/00f54p054",
  "country_code": "US",
  "type": "education",
  "homepage": "https://stanford.edu",
  "works_count": 250000,
  "cited_by_count": 6000000,
  "h_index": 1200,
  "topics": [
    {"name": "Medicine", "id": "T50001"},
    {"name": "Computer Science", "id": "T50002"},
    {"name": "Biochemistry", "id": "T50003"}
  ],
  "image_url": "https://commons.wikimedia.org/..."
}
```

---

## `openalex_search_sources` Output

```json
{
  "query": "Nature",
  "total_results": 12,
  "showing": 10,
  "sources": [
    {
      "openalex_id": "S137773608",
      "name": "Nature",
      "issn_l": "0028-0836",
      "type": "journal",
      "is_oa": false,
      "works_count": 92000,
      "cited_by_count": 12000000,
      "h_index": 1400,
      "publisher": "Springer Nature",
      "homepage": "https://nature.com"
    }
  ]
}
```

---

## `openalex_get_source` Output

```json
{
  "openalex_id": "S137773608",
  "name": "Nature",
  "issn_l": "0028-0836",
  "issn": ["0028-0836", "1476-4687"],
  "type": "journal",
  "is_oa": false,
  "is_in_doaj": false,
  "works_count": 92000,
  "cited_by_count": 12000000,
  "h_index": 1400,
  "i10_index": 80000,
  "publisher": "Springer Nature",
  "homepage": "https://www.nature.com/nature",
  "topics": [
    {"name": "Molecular Biology", "id": "T60001"},
    {"name": "Medicine", "id": "T50001"}
  ]
}
```

---

## `openalex_aggregate_works` Output

```json
{
  "group_by": "publication_year",
  "total_groups": 8,
  "groups": [
    {"key": "2024", "label": "2024", "count": 5200},
    {"key": "2023", "label": "2023", "count": 4800},
    {"key": "2022", "label": "2022", "count": 3900},
    {"key": "2021", "label": "2021", "count": 3100}
  ]
}
```

**Notes:**
- Groups are returned sorted by count descending by default
- For `publication_year`, sort output by key (year) for chronological display
- `key` is the raw value (e.g. "US", "article", "W123...")
- `label` is the human-readable display name (same for year/type, institution name for institution IDs)

---

## Error Responses

When a tool fails, it raises `McpError` with a descriptive message:

| Scenario | Error message |
|----------|--------------|
| Missing API key or email | `Set OPENALEX_API_KEY (recommended) or OPENALEX_EMAIL in your environment` |
| Invalid API key | `OpenAlex authentication failed (401). Check your OPENALEX_API_KEY` |
| Entity not found | `Not found in OpenAlex: /works/W9999999999` |
| Rate limit exhausted | `OpenAlex rate limit exceeded after all retries` |
| Network timeout | `Request timed out after 30s` |
| Invalid group_by field | `Invalid group_by value 'xxx'. Valid options: ...` |

**Agent response strategy on errors:**
- 404 Not Found → suggest searching for the entity first, then use the returned ID
- Auth error → tell user to add `OPENALEX_API_KEY` to env config
- Rate limit → inform about quota; suggest spacing requests or using API key
