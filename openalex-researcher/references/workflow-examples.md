# OpenAlex MCP Workflow Examples

## 1. Systematic Literature Review (SLR) Preparation

**Task:** Map all recent articles on a topic for a formal systematic review.

```python
# Step 1: Get the total pool size
overview = openalex_search_works(
    query='"digital health" AND "low-income countries"',
    filters="type:article,publication_year:>2018",
    sort="cited_by_count:desc",
    per_page=1
)
# → total_results: 847

# Step 2: Get annual trend to understand growth
trend = openalex_aggregate_works(
    group_by="publication_year",
    query='"digital health" AND "low-income countries"',
    filters="type:article,publication_year:2015-2024"
)

# Step 3: Retrieve pages
page1 = openalex_search_works(
    query='"digital health" AND "low-income countries"',
    filters="type:article,publication_year:>2018",
    sort="cited_by_count:desc",
    per_page=25, page=1
)
page2 = openalex_search_works(..., page=2)  # continue until total

# Step 4: Get full details for top papers
for work in page1["works"][:5]:
    detail = openalex_get_work(work["openalex_id"])
    # → abstract, all authors, keywords, open-access URL
```

---

## 2. Author Benchmarking

**Task:** Compare two economists by h-index, citation count, and recent output.

```python
# Find authors
results_a = openalex_search_authors(query="Daron Acemoglu", per_page=3)
author_id_a = results_a["authors"][0]["openalex_id"]  # A2021661963

results_b = openalex_search_authors(query="James Robinson economist", per_page=3)
author_id_b = results_b["authors"][0]["openalex_id"]

# Get full profiles
profile_a = openalex_get_author(author_id_a)
profile_b = openalex_get_author(author_id_b)

# Compare:
# profile_a["h_index"]          vs profile_b["h_index"]
# profile_a["cited_by_count"]   vs profile_b["cited_by_count"]
# profile_a["works_count"]      vs profile_b["works_count"]
# profile_a["citations_by_year"]["2023"] vs profile_b[...]
```

---

## 3. Institutional Research Landscape

**Task:** Understand a university's research strengths and recent output.

```python
# Step 1: Find the institution
inst_results = openalex_search_institutions(
    query="Pontificia Universidad Católica del Perú",
    country_code="PE"
)
inst_id = inst_results["institutions"][0]["openalex_id"]  # e.g. "I35455738"

# Step 2: Full institution profile (topics, h-index)
profile = openalex_get_institution(inst_id)
# → profile["topics"] = [{"name": "Social Sciences", ...}, ...]

# Step 3: Recent output count by year
trend = openalex_aggregate_works(
    group_by="publication_year",
    filters=f"institutions.id:{inst_id},publication_year:2015-2024"
)

# Step 4: Top research areas
topics_dist = openalex_aggregate_works(
    group_by="topics.id",
    filters=f"institutions.id:{inst_id},publication_year:>2019"
)

# Step 5: Most cited recent papers
top_papers = openalex_search_works(
    filters=f"institutions.id:{inst_id},publication_year:>2020",
    sort="cited_by_count:desc",
    per_page=10
)
```

---

## 4. Citation Impact Analysis

**Task:** Track how a landmark paper's influence grew over time.

```python
# Step 1: Find the work
result = openalex_search_works(
    query="Attention Is All You Need",
    filters="type:article",
    sort="cited_by_count:desc",
    per_page=1
)
work_id = result["works"][0]["openalex_id"]  # "W2741809807"
total_cites = result["works"][0]["cited_by_count"]

# Step 2: Get annual citation breakdown (via citing works aggregation)
yearly = openalex_aggregate_works(
    group_by="publication_year",
    filters=f"cites:{work_id}"
)
# → groups: [{"key": "2023", "count": 25000}, {"key": "2022", "count": 18000}, ...]

# Step 3: What fields are citing it?
by_topic = openalex_aggregate_works(
    group_by="topics.id",
    filters=f"cites:{work_id}"
)
```

---

## 5. Research Gap Discovery

**Task:** Find underexplored topic intersections.

```python
# Check size of niche intersection
niche = openalex_search_works(
    query='"circular economy" AND "construction industry" AND Peru',
    filters="publication_year:>2018",
    per_page=1
)
# → total_results: 12  → very small = research gap

# Compare to broader topic
broader = openalex_search_works(
    query='"circular economy" AND "construction industry"',
    filters="publication_year:>2018",
    per_page=1
)
# → total_results: 1840  → established field

# Country-level comparison (where most research comes from)
by_country = openalex_aggregate_works(
    group_by="institutions.country_code",
    query='"circular economy" AND "construction industry"',
    filters="publication_year:>2018"
)
# → {"groups": [{"key":"CN","count":450}, {"key":"US","count":320}, ...]}
# → PE is absent = clear contribution opportunity
```

---

## 6. Batch DOI Metadata Retrieval

**Task:** Get structured metadata for a list of DOIs from a reference list.

```python
dois = [
    "10.1016/j.worlddev.2023.106285",
    "10.1093/qje/qjac034",
    "10.1257/aer.20201879",
    "10.1016/j.labeco.2023.102400",
]

papers = []
for doi in dois:
    try:
        work = openalex_get_work(doi)
        papers.append({
            "doi": doi,
            "title": work["title"],
            "year": work.get("publication_year"),
            "cited_by": work.get("cited_by_count", 0),
            "authors": [a["name"] for a in work.get("authors", [])],
            "abstract": work.get("abstract", "")[:300],
            "oa_url": work.get("oa_url"),
            "journal": work.get("source_name"),
        })
    except Exception as e:
        papers.append({"doi": doi, "error": str(e)})
```

---

## 7. Open Access Discovery for a User

**Task:** A user has no institutional access — find freely readable papers.

```python
# Search with OA filter
oa_results = openalex_search_works(
    query="mRNA vaccine mechanism immune response",
    filters="open_access.is_oa:true,type:article,publication_year:>2020",
    sort="cited_by_count:desc",
    per_page=10
)

# For each result, get the direct PDF link
for work in oa_results["works"]:
    detail = openalex_get_work(work["openalex_id"])
    if detail.get("oa_url"):
        print(f"{detail['title']}\n  → {detail['oa_url']}\n")

# Check open access status breakdown for a topic
oa_breakdown = openalex_aggregate_works(
    group_by="open_access.status",
    query="mRNA vaccine",
    filters="type:article"
)
# → {"groups": [{"key":"gold","count":1200}, {"key":"closed","count":3400}, ...]}
```

---

## 8. Journal Selection for Manuscript Submission

**Task:** Help a researcher identify suitable journals for their paper.

```python
# Step 1: Find journals in the field
journals = openalex_search_sources(
    query="environmental economics sustainability",
    source_type="journal",
    per_page=15
)
# Sort by h_index internally or by cited_by_count

# Step 2: Filter for OA if needed
oa_journals = openalex_search_sources(
    query="environmental economics",
    source_type="journal",
    is_oa=True,
    per_page=10
)

# Step 3: Get full details for top candidates
top_journal = openalex_get_source(journals["sources"][0]["openalex_id"])
# → h_index, i10_index, is_in_doaj, topics, works_count

# Step 4: Check recent output from target journal
journal_papers = openalex_search_works(
    filters=f"primary_location.source.id:{top_journal['openalex_id']},publication_year:2023",
    sort="cited_by_count:desc",
    per_page=5
)
# → See what's being published in that journal this year
```

---

## 9. Researcher Network Mapping

**Task:** Find who co-authors most with a target researcher.

```python
# Step 1: Get author's works
author_id = "A2208157607"  # Geoffrey Hinton
works = openalex_search_works(
    filters=f"author.id:{author_id}",
    sort="cited_by_count:desc",
    per_page=25
)

# Step 2: Get full details to see all authors
coauthors: dict = {}
for w in works["works"][:10]:
    detail = openalex_get_work(w["openalex_id"])
    for author in detail.get("authors", []):
        if author["openalex_id"] != author_id:
            aid = author["openalex_id"]
            coauthors[aid] = coauthors.get(aid, {"name": author["name"], "count": 0})
            coauthors[aid]["count"] += 1

# Sort by collaboration frequency
top_coauthors = sorted(coauthors.values(), key=lambda x: x["count"], reverse=True)
```

---

## 10. Latin American Economics Research Audit

**Task:** Map the state of economics research in Peru for a policy report.

```python
# Step 1: Get top Peruvian economics papers
pe_econ = openalex_search_works(
    query="economics employment labor",
    filters="institutions.country_code:PE,publication_year:>2018,type:article",
    sort="cited_by_count:desc",
    per_page=20
)

# Step 2: Annual growth of Peruvian research output
pe_trend = openalex_aggregate_works(
    group_by="publication_year",
    filters="institutions.country_code:PE,type:article,publication_year:2010-2024"
)

# Step 3: Which universities produce the most
pe_inst_breakdown = openalex_aggregate_works(
    group_by="institutions.id",
    filters="institutions.country_code:PE,publication_year:>2018"
)

# Step 4: Compare Peru vs regional peers
latam_comparison = openalex_aggregate_works(
    group_by="institutions.country_code",
    filters="institutions.country_code:PE|CL|CO|MX|AR|BR,publication_year:2020-2024,type:article"
)
```

---

## Output Formatting Templates

### Paper list (Markdown)
```
{index}. **{title}** ({publication_year})
   {first_author} | {source_name} | {cited_by_count:,} citations
   DOI: `{doi}` | {"Open Access" if open_access else ""}
```

### Author comparison table
```
| Metric | {name_a} | {name_b} |
|--------|---------|---------|
| h-index | {h_index} | {h_index} |
| Total citations | {cited_by_count:,} | {cited_by_count:,} |
| Works | {works_count} | {works_count} |
| Affiliation | {affiliation} | {affiliation} |
```

### Annual trend bar chart (text)
```python
max_count = max(g["count"] for g in groups)
for g in sorted(groups, key=lambda x: x["key"]):
    bar_len = int(g["count"] / max_count * 20)
    print(f'{g["key"]}: {"█" * bar_len} {g["count"]:,}')
```
