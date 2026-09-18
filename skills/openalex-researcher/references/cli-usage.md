# OpenAlex CLI Reference (No MCP Connection)

Read this file when the `openalex_*` MCP tools are **not** in your available tools list —
for example, a shell-only coding agent, a CI job, or a session where the OpenAlex MCP
server isn't registered. The `openalex` CLI calls the exact same underlying functions as
the MCP tools, so results are identical — only the calling convention changes (shell
command instead of a tool call).

Before relying on it, confirm it's installed:
```bash
openalex --version || pip install openalex-mcp    # or: uv tool install openalex-mcp
```

Auth works the same way as the MCP server — set `OPENALEX_API_KEY` (or `OPENALEX_EMAIL`)
in the environment or a `.env` file. No key set → the CLI exits with a config error
telling you to set one; get a free key at https://openalex.org/settings/api.

---

## MCP tool → CLI command

| MCP tool | CLI command |
|----------|-------------|
| `openalex_search_works` | `openalex search-works` |
| `openalex_get_work` | `openalex get-work` |
| `openalex_search_authors` | `openalex search-authors` |
| `openalex_get_author` | `openalex get-author` |
| `openalex_search_institutions` | `openalex search-institutions` |
| `openalex_get_institution` | `openalex get-institution` |
| `openalex_search_sources` | `openalex search-sources` |
| `openalex_get_source` | `openalex get-source` |
| `openalex_aggregate_works` | `openalex aggregate-works` |
| Read `openalex://filter-reference` | `openalex filter-guide` |

Run `openalex <command> --help` for the full flag list of any command.

---

## Always pass `--json` when parsing programmatically

Without `--json`, the CLI prints a human-readable table meant for a terminal, not for
parsing. With `--json`, it prints the same structured dict the MCP tool would return to
an LLM — pipe it into `jq`, `python -c`, or read it back with a script.

```bash
openalex --json search-works "federated learning" -f "publication_year:>2021,type:article" -s "cited_by_count:desc" \
  | jq '.works[] | {title, cited_by_count, doi}'
```

---

## Command reference

### search-works
```bash
openalex search-works "<query>" -f "<filters>" -s "<sort>" -n <per_page> -p <page>
```
```bash
openalex search-works "CRISPR gene editing" -f "publication_year:>2022,open_access.is_oa:true" -s "cited_by_count:desc" -n 10
```

### get-work
```bash
openalex get-work "<identifier>"     # OpenAlex ID, DOI, or pmid:12345678
```
```bash
openalex get-work 10.1038/s41586-021-03819-2
openalex --json get-work W2741809807 | jq '.authors, .oa_url'
```

### search-authors
```bash
openalex search-authors "<query>" -f "<filters>" -s "<sort>" -n <per_page>
```
```bash
openalex search-authors "Geoffrey Hinton" -n 3
```

### get-author
```bash
openalex get-author "<author_id>"    # A-number or ORCID
```
```bash
openalex get-author A2208157607
```

### search-institutions
```bash
openalex search-institutions "<query>" -c <country_code> -t <type> -n <per_page>
```
```bash
openalex search-institutions "PUCP" -c PE
```

### get-institution
```bash
openalex get-institution "<institution_id>"   # I-number or ROR ID
```

### search-sources
```bash
openalex search-sources "<query>" -f "<filters>" -t <source_type> [--oa | --no-oa] -n <per_page>
```
```bash
openalex search-sources "bioinformatics" -t journal --oa
```

### get-source
```bash
openalex get-source "<source_id>"    # S-number or ISSN
```

### aggregate-works
```bash
openalex aggregate-works <group_by> -f "<filters>" -q "<query>"
```
```bash
openalex aggregate-works publication_year -f "institutions.id:I35455738"
openalex aggregate-works institutions.country_code -q "large language models" -f "publication_year:>2020"
```
Valid `group_by` values: `publication_year`, `type`, `open_access.status`, `language`,
`institutions.id`, `institutions.country_code`, `topics.id`, `primary_location.source.id`,
`authorships.author.id`, `is_oa`, `has_doi`, `has_abstract`.

### filter-guide
```bash
openalex filter-guide     # prints the full filter syntax reference (same as the MCP resource)
```

---

## Workflow translations (mirrors `workflow-examples.md`)

### Literature search → citation-network follow-up
```bash
# 1. Find the landmark paper's OpenAlex ID
openalex --json get-work 10.1038/s41586-021-03819-2 | jq -r '.openalex_id'
# → W2741809807

# 2. Find who cites it, most-cited first
openalex search-works -f "cites:W2741809807" -s "cited_by_count:desc" -n 10
```

### Institutional research audit
```bash
openalex search-institutions "PUCP" -c PE                                   # get I-id
openalex aggregate-works publication_year -f "institutions.id:I35455738"    # trend
openalex search-works -f "institutions.id:I35455738,publication_year:>2020" -s "cited_by_count:desc" -n 20
```

### Author benchmarking
```bash
openalex --json search-authors "Yoshua Bengio" -n 1 | jq -r '.authors[0].openalex_id'
openalex get-author A2107864399
```
