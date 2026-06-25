---
name: openalex-researcher
version: 1.0.0
description: >
  Use the OpenAlex MCP to search 250M+ scholarly works, retrieve author profiles,
  analyze institutional output, explore journal sources, and aggregate citation trends —
  all from the world's largest free and open scholarly database.
author: JOSETRA44
tags: [research, academic, scholarly, openalex, literature, citations, authors, institutions]
mcp:
  server: openalex
  tools:
    - openalex_search_works
    - openalex_get_work
    - openalex_search_authors
    - openalex_get_author
    - openalex_search_institutions
    - openalex_get_institution
    - openalex_search_sources
    - openalex_get_source
    - openalex_aggregate_works
  resources:
    - openalex://filter-reference
---

# OpenAlex Researcher Skill

Use this skill whenever the user needs to:
- Find scholarly papers, articles, preprints, or books
- Look up an author's publication record and impact metrics
- Analyze what a university or research institute publishes
- Explore journals, conferences, or open-access repositories
- Generate year-by-year citation or publication trend charts
- Understand the research landscape of a topic or field

OpenAlex covers 250M+ works, 300M+ authors, and 100K+ institutions. All data is free (CC0).

---

## When to Use Each Tool

| Situation | Tool(s) |
|-----------|---------|
| User asks to find papers on a topic | `openalex_search_works` |
| User has a DOI or paper ID | `openalex_get_work` |
| User asks about a researcher | `openalex_search_authors` → `openalex_get_author` |
| User wants institutional output | `openalex_search_institutions` → `openalex_search_works` |
| User asks about a journal | `openalex_search_sources` → `openalex_get_source` |
| User wants publication trends over time | `openalex_aggregate_works(group_by="publication_year")` |
| User wants topic/type/country breakdown | `openalex_aggregate_works(group_by=...)` |
| User needs filter syntax | Read `openalex://filter-reference` |

---

## MCP Setup

Add to your MCP client config:

```json
{
  "mcpServers": {
    "openalex": {
      "command": "uvx",
      "args": ["openalex-mcp"],
      "env": {
        "OPENALEX_API_KEY": "YOUR_KEY_HERE"
      }
    }
  }
}
```

Get a free API key at: https://openalex.org/settings/api

---

## Core Workflows

### 1. Literature Search (Topic Discovery)

**Goal:** Find the most impactful recent papers on a topic.

```
Step 1: openalex_search_works(
    query="federated learning privacy",
    filters="publication_year:>2020,type:article",
    sort="cited_by_count:desc",
    per_page=10
)
→ Returns: works[] with openalex_id, doi, title, cited_by_count, open_access

Step 2 (for important papers): openalex_get_work(identifier="10.1038/s41586-...")
→ Returns: full abstract, all authors with affiliations, topics, keywords
```

**Filter patterns to know:**
- `type:article` — journal articles only
- `type:preprint` — preprints (arXiv, bioRxiv, etc.)
- `open_access.is_oa:true` — freely readable
- `cited_by_count:>50` — filter out low-impact work
- `language:en` — English only

---

### 2. Author Profile & Benchmarking

**Goal:** Retrieve a researcher's metrics and compare with another.

```
Step 1: openalex_search_authors(query="Yoshua Bengio", per_page=3)
→ Pick the correct author from results, note openalex_id

Step 2: openalex_get_author(author_id="A2107864399")
→ Returns: name, orcid, h_index, i10_index, works_count, cited_by_count,
           affiliation, top topics, citations_by_year{}
```

**Benchmarking two researchers:**
```
profile_a = openalex_get_author("A2107864399")   # Bengio
profile_b = openalex_get_author("A2208157607")   # Hinton
Compare: h_index, cited_by_count, works_count
```

---

### 3. Institutional Research Audit

**Goal:** Analyze a university's scholarly output.

```
Step 1: openalex_search_institutions(query="PUCP", country_code="PE")
→ Returns: openalex_id (e.g. "I35455738"), works_count, cited_by_count

Step 2: openalex_aggregate_works(
    group_by="publication_year",
    filters="institutions.id:I35455738"
)
→ Returns: annual publication counts (trends over time)

Step 3: openalex_search_works(
    filters="institutions.id:I35455738,publication_year:>2020",
    sort="cited_by_count:desc",
    per_page=20
)
→ Returns: top recent papers from that institution
```

---

### 4. Publication Trend Analysis

**Goal:** See how a research area has grown or declined.

```
Step 1: openalex_aggregate_works(
    group_by="publication_year",
    query="large language models"
)
→ {"groups": [{"key":"2023","count":8500}, {"key":"2022","count":3200}, ...]}

Step 2: openalex_aggregate_works(
    group_by="type",
    query="large language models"
)
→ Breakdown: article / preprint / book-chapter / dataset

Step 3: openalex_aggregate_works(
    group_by="institutions.country_code",
    query="large language models",
    filters="publication_year:>2020"
)
→ Country-level production breakdown
```

---

### 5. Journal & Source Discovery

**Goal:** Find the best journals in a field.

```
Step 1: openalex_search_sources(
    query="machine learning",
    source_type="journal",
    is_oa=False,
    per_page=10
)
→ Returns: sources[] with name, issn_l, h_index, publisher, is_oa

Step 2: openalex_get_source(source_id="S2764455111")
→ Returns: full source profile including topics, i10_index, works_count
```

---

### 6. Citation Network (Papers Citing a Work)

**Goal:** Find who has cited a landmark paper.

```
Step 1: Get the OpenAlex ID for the work
openalex_get_work("10.1038/s41586-021-03819-2")
→ openalex_id = "W2741809807", cited_by_count = 12000

Step 2: Find citing papers
openalex_search_works(
    filters="cites:W2741809807",
    sort="cited_by_count:desc",
    per_page=10
)
→ Returns: most influential papers that cite AlphaFold
```

---

### 7. Open Access Discovery

**Goal:** Find freely readable papers for a user without journal access.

```
openalex_search_works(
    query="cancer immunotherapy checkpoint",
    filters="open_access.is_oa:true,publication_year:>2021,type:article",
    sort="cited_by_count:desc"
)
→ Each result includes oa_url (via openalex_get_work) for direct access
```

---

## Tool Reference

### openalex_search_works

```
query       : str  — keyword search (title + abstract)
filters     : str  — comma-separated filter expressions
sort        : str  — "cited_by_count:desc" | "publication_date:desc" | "relevance_score:desc"
per_page    : int  — 1–200 (default 10)
page        : int  — page number (default 1)
```

**Output shape:**
```json
{
  "query": "...",
  "total_results": 4821,
  "showing": 10,
  "page": 1,
  "per_page": 10,
  "works": [
    {
      "openalex_id": "W2741809807",
      "doi": "10.1038/s41586-021-03819-2",
      "title": "Highly accurate protein structure prediction with AlphaFold",
      "first_author": "Jumper, J.",
      "publication_year": 2021,
      "type": "article",
      "cited_by_count": 12000,
      "open_access": true,
      "source_name": "Nature",
      "language": "en"
    }
  ]
}
```

---

### openalex_get_work

```
identifier : str — OpenAlex ID ("W2741809807"), DOI ("10.1038/..."), or PubMed ID ("pmid:34512593")
```

**Output shape:**
```json
{
  "openalex_id": "W2741809807",
  "doi": "10.1038/s41586-021-03819-2",
  "title": "...",
  "abstract": "Full abstract text...",
  "publication_year": 2021,
  "type": "article",
  "cited_by_count": 12000,
  "open_access": true,
  "oa_url": "https://...",
  "language": "en",
  "authors": [
    {"name": "Jumper, J.", "openalex_id": "A2208157607", "orcid": "...", "affiliation": "DeepMind"}
  ],
  "keywords": ["protein folding", "deep learning"],
  "topics": [{"name": "Structural Biology", "id": "T10234"}],
  "source_name": "Nature",
  "volume": "596",
  "issue": "7873",
  "pages": "583-589",
  "referenced_works_count": 120
}
```

---

### openalex_get_author

```
author_id : str — OpenAlex ID ("A2208157607") or ORCID ("0000-0002-1825-0097")
```

**Output shape:**
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
  "topics": [{"name": "Machine Learning", "id": "T10234"}],
  "citations_by_year": {"2023": 20000, "2022": 18000}
}
```

---

### openalex_aggregate_works

```
group_by : str — field to group by (see valid values below)
filters  : str — scope the aggregation (same filter syntax as search_works)
query    : str — optional keyword scope
```

**Valid group_by values:**
- `publication_year` — annual output
- `type` — article/book/preprint/dataset
- `open_access.status` — gold/green/bronze/hybrid/closed
- `language` — en/es/zh/fr/de/pt/ar
- `institutions.id` — top institutions
- `institutions.country_code` — country breakdown
- `topics.id` — top research topics
- `primary_location.source.id` — top journals
- `is_oa` — open access yes/no
- `has_doi` — DOI coverage

**Output shape:**
```json
{
  "group_by": "publication_year",
  "total_groups": 8,
  "groups": [
    {"key": "2024", "label": "2024", "count": 5200},
    {"key": "2023", "label": "2023", "count": 4800}
  ]
}
```

---

## Formatting Results for Users

### Paper list
```
1. **{title}** ({publication_year})
   {first_author} | {source_name} | Cited {cited_by_count}×
   DOI: {doi} | {"Open Access" if open_access else ""}
```

### Author profile
```
**{name}** — {affiliation}, {country}
h-index: {h_index} | {works_count} papers | {cited_by_count:,} citations
ORCID: {orcid}
Top topics: {topics[0].name}, {topics[1].name}
```

### Trend chart (text)
```
Publication trend for "machine learning":
2020: ████████ 8,200
2021: ██████████ 10,400
2022: ████████████ 12,100
2023: ██████████████ 14,800
```

---

## Key Identifiers

| Entity | ID format | Example |
|--------|-----------|---------|
| Work | `W{number}` | `W2741809807` |
| Author | `A{number}` | `A2208157607` |
| Institution | `I{number}` | `I97018004` |
| Source | `S{number}` | `S137773608` |
| Topic | `T{number}` | `T10234` |

All IDs are also valid as full URLs: `https://openalex.org/W2741809807`

---

## Install This Skill

```bash
# Via npx skills (recommended)
npx skills add JOSETRA44/openalex-mcp@openalex-researcher

# Or clone the repo and copy manually
git clone https://github.com/JOSETRA44/openalex-mcp.git
cp -r openalex-mcp/openalex-researcher ~/.claude/skills/
```
