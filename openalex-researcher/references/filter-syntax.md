# OpenAlex Filter Syntax — Complete Reference

## Base URL pattern
```
https://api.openalex.org/{entity}?filter=field:value,field2:value2&search=...&sort=field:dir&per_page=N&page=N
```

---

## Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `:`       | equals | `type:article` |
| `!:`      | not equals | `!type:book` |
| `>`       | greater than | `cited_by_count:>100` |
| `<`       | less than | `cited_by_count:<10` |
| `>=`      | greater or equal | `publication_year:>=2020` |
| `<=`      | less or equal | `publication_year:<=2023` |
| `X-Y`     | range (inclusive) | `publication_year:2018-2023` |
| `.search:` | text search within field | `title.search:neural network` |
| `\|`       | OR between values | `institutions.country_code:US\|GB\|CA` |

---

## Works Filters (`/works`)

### Identifiers
```
doi:10.1038/s41586-021-03819-2
openalex:W2741809807
pmid:34512593
mag:2741809807
```

### Content
```
title.search:machine learning
abstract.search:carbon capture
fulltext.search:CRISPR gene editing
keyword.search:climate
```

### Classification
```
type:article
type:preprint
type:book
type:book-chapter
type:dataset
type:dissertation
type:review
type:paratext
type:other

language:en
language:es
language:zh
language:fr
language:de
language:pt
language:ar
language:ru
language:ja
language:ko

publication_year:2023
publication_year:2020-2024
publication_year:>2021
publication_year:>=2020
```

### Open Access
```
open_access.is_oa:true
open_access.status:gold
open_access.status:green
open_access.status:bronze
open_access.status:hybrid
open_access.status:closed

has_doi:true
has_abstract:true
has_fulltext:true
has_oa_accepted_or_published_version:true
```

### Authors & Affiliations
```
author.id:A2208157607
author.orcid:0000-0001-6169-6580
author.display_name.search:Hinton
institutions.id:I97018004
institutions.country_code:US
institutions.type:education
institutions.country_code:US|GB|CA
```

### Topics & Fields
```
topics.id:T10234
primary_topic.id:T10234
topics.domain.id:4
topics.field.id:22
```

### Publication Venue
```
primary_location.source.id:S137773608
primary_location.source.issn:0028-0836
primary_location.source.issn_l:0028-0836
primary_location.is_oa:true
```

### Impact
```
cited_by_count:>100
cited_by_count:50-500
cited_by_count:0
referenced_works_count:>20
```

### Citation relationships
```
cites:W2741809807       -- papers that cite this work
cited_by:W2741809807    -- papers cited by this work (references)
related_to:W2741809807  -- related works (similar topics)
```

---

## Author Filters (`/authors`)

```
display_name.search:Geoffrey Hinton
last_known_institutions.id:I97018004
last_known_institutions.country_code:US
last_known_institutions.type:education
orcid:0000-0002-1825-0097
has_orcid:true
works_count:>50
cited_by_count:>1000
h_index:>30
topics.id:T10234
```

---

## Institution Filters (`/institutions`)

```
display_name.search:Stanford
country_code:US
country_code:PE
country_code:MX
country_code:GB
type:education
type:healthcare
type:company
type:government
type:nonprofit
type:facility
ror:00f54p054
works_count:>5000
cited_by_count:>100000
```

---

## Source Filters (`/sources`)

```
display_name.search:Nature
issn:0028-0836
type:journal
type:repository
type:conference
type:book series
is_oa:true
is_in_doaj:true
host_organization.id:P4310320595
works_count:>1000
h_index:>50
```

---

## Sort Fields

### Works
```
sort=cited_by_count:desc       -- most cited first
sort=cited_by_count:asc        -- least cited first
sort=publication_date:desc     -- newest first
sort=publication_date:asc      -- oldest first
sort=relevance_score:desc      -- most relevant (requires search=)
```

### Authors
```
sort=cited_by_count:desc
sort=works_count:desc
sort=h_index:desc
```

### Institutions / Sources
```
sort=cited_by_count:desc
sort=works_count:desc
```

---

## Group By (Aggregation)

Add `group_by=field` to count entities by category:

```
/works?filter=...&group_by=publication_year
→ [{"key":"2023","key_display_name":"2023","count":1234}, ...]
```

### Works group_by fields
```
publication_year
type
open_access.status
language
institutions.id
institutions.country_code
topics.id
topics.domain.id
primary_location.source.id
is_oa
has_doi
has_abstract
```

### Authors group_by fields
```
last_known_institutions.country_code
last_known_institutions.type
topics.id
```

---

## Pagination

```
per_page=25              -- results per page (1–200)
page=2                   -- page number (1-indexed)
```

For deep pagination (>10,000 results):
```
cursor=*                 -- first request returns meta.next_cursor
cursor={next_cursor}     -- subsequent pages
```

---

## Logical Combinations

### AND (multiple filters on different fields)
```
filter=type:article,language:en,open_access.is_oa:true,publication_year:>2020
```

### OR (multiple values for the same field — pipe-separated)
```
filter=institutions.country_code:US|GB|CA|AU
filter=type:article|review|book-chapter
```

### NOT
```
filter=!type:paratext
filter=!language:zh
```

---

## 50 Ready-to-Use Filter Examples

```bash
# 1. ML articles from last 3 years
type:article,publication_year:>2022
search: machine learning

# 2. Open-access cancer papers
open_access.is_oa:true,type:article
search: cancer treatment

# 3. Papers from MIT
institutions.id:I63966007

# 4. Papers from MIT published 2020-2024
institutions.id:I63966007,publication_year:2020-2024

# 5. English-language articles with abstracts
language:en,has_abstract:true,type:article

# 6. Preprints about COVID
type:preprint
search: COVID-19 pandemic

# 7. Highly-cited AI papers
cited_by_count:>500,type:article
search: artificial intelligence

# 8. Gold open access papers
open_access.status:gold,type:article

# 9. Papers from US institutions in 2023
institutions.country_code:US,publication_year:2023

# 10. Papers from multiple countries
institutions.country_code:PE|MX|CO|CL|AR

# 11. Dataset-type works
type:dataset

# 12. Dissertations from last 5 years
type:dissertation,publication_year:>2019

# 13. Papers citing AlphaFold
cites:W2741809807

# 14. Papers referenced by a specific work
cited_by:W2741809807

# 15. Works with DOI
has_doi:true

# 16. Works by a specific author
author.id:A2208157607

# 17. Works by ORCID
author.orcid:0000-0001-6169-6580

# 18. Works by author name
author.display_name.search:LeCun Yann

# 19. Works in Nature journal
primary_location.source.id:S137773608

# 20. Works with fulltext available
has_fulltext:true

# 21. Spanish-language papers
language:es

# 22. Works from healthcare institutions
institutions.type:healthcare

# 23. Book chapters
type:book-chapter,publication_year:>2018

# 24. Works in top ML journal
primary_location.source.issn:2041-1723

# 25. Works with more than 50 references
referenced_works_count:>50

# 26. Annual trend for a topic (use group_by)
group_by=publication_year
search: quantum computing

# 27. Open-access journals only
is_oa:true  [on /sources]

# 28. Brazilian institutions
country_code:BR  [on /institutions]

# 29. European institutions in education
country_code:DE|FR|GB|IT|ES&type:education  [on /institutions]

# 30. Authors with ORCID at top universities
has_orcid:true,last_known_institutions.type:education

# 31. Works on a specific topic
topics.id:T10234

# 32. Works in top 10 journals (chain: get source IDs first)
primary_location.source.id:S137773608|S2764455111|S49688027

# 33. Recently published with many citations
publication_year:>2020,cited_by_count:>200

# 34. Interdisciplinary works (multiple topics)
topics.id:T10234  -- then inspect other topics in results

# 35. Works with open-access full text
open_access.is_oa:true,has_fulltext:true

# 36. Conference papers
type:proceedings-article

# 37. Non-English papers (exclude English)
!language:en

# 38. Works not yet cited
cited_by_count:0

# 39. Works from a specific publisher's journals
host_organization.id:P4310320595  [on /sources]

# 40. Author h-index > 50
h_index:>50  [on /authors]

# 41. Latin American papers 2020-2024
institutions.country_code:PE|MX|CO|CL|AR|BR,publication_year:2020-2024

# 42. Papers on climate from government institutions
institutions.type:government
search: climate change adaptation

# 43. Technology transfer / patents-related
search: patent technology transfer commercialization

# 44. Systematic reviews
type:review,title.search:systematic review

# 45. Meta-analyses
title.search:meta-analysis

# 46. Works with no abstract (for data quality checks)
has_abstract:false,type:article

# 47. Works from a hospital network
institutions.type:healthcare,institutions.country_code:US

# 48. AI/ML papers that are open access gold
topics.id:T10234,open_access.status:gold

# 49. Preprints that became articles (find by DOI then check versions)
type:preprint,has_doi:true

# 50. High-impact works from small countries
institutions.country_code:PE,cited_by_count:>50
```
