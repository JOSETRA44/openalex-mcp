# OpenAlex MCP Server & CLI

<!-- mcp-name: io.github.JOSETRA44/openalex-mcp -->

Connects any MCP-compatible AI agent — or your terminal — to [OpenAlex](https://openalex.org): the world's largest **free and open** scholarly database with 250+ million works, 300+ million authors, 100,000+ institutions, and billions of citation links.

**Works with:** Claude Desktop · Claude Code · Cursor · VS Code Copilot · Windsurf · Zed · any MCP client — or standalone via the [`openalex` CLI](#cli-command-line)

**No paywall. No institutional access required. CC0 licensed data.**

---


[![PyPI](https://img.shields.io/pypi/v/openalex-mcp.svg)](https://pypi.org/project/openalex-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/JOSETRA44/openalex-mcp/blob/main/LICENSE)
[![MCP](https://img.shields.io/badge/MCP-server-blue.svg)](https://modelcontextprotocol.io)

## What you can ask it

| Ask | Tool that answers it |
|---|---|
| "Find recent papers on graph neural networks, most cited first" | `openalex_search_works` |
| "What's Geoffrey Hinton's h-index and how many papers has he published?" | `openalex_search_authors` → `openalex_get_author` |
| "Which institutions publish the most on CRISPR?" | `openalex_aggregate_works` |
| "Give me everything about this DOI" | `openalex_get_work` |
| "Is this journal open access, and how big is it?" | `openalex_search_sources` |
| "How has output on transformers grown per year since 2017?" | `openalex_aggregate_works` |

No API key needed. Setting `OPENALEX_EMAIL` puts you in OpenAlex's *polite pool*,
which raises your rate limit — worth doing, takes ten seconds.

## Quickstart (2 minutes)

**1. Get your free API key** at [openalex.org/settings/api](https://openalex.org/settings/api) — takes 30 seconds

**2. Install the server**
```bash
pip install openalex-mcp
```

**3. Add to your AI agent** — copy your client's config from [Configuration](#configuration-by-client) below.

---

## Prerequisites

### Python 3.11+
```bash
python --version   # needs 3.11 or higher
# Install if missing: https://python.org/downloads
```

### uv (recommended)
```bash
# Windows
winget install astral-sh.uv

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

> **No uv?** Use `pip install openalex-mcp` instead, then replace `uvx openalex-mcp` in configs with the path from `where openalex-mcp` (Windows) or `which openalex-mcp` (macOS/Linux).

---

## Installation Options

One package, two executables: `openalex-mcp` (the MCP server, for AI agents) and
`openalex` (the [CLI](#cli-command-line), for your terminal). Every option below
installs both.

### Option A — uvx (recommended for MCP clients)
```bash
uvx openalex-mcp          # install and run — uv handles everything
uv tool upgrade openalex-mcp  # upgrade later
```

### Option B — pip
```bash
pip install openalex-mcp
which openalex-mcp    # macOS/Linux → /usr/local/bin/openalex-mcp
where openalex-mcp    # Windows    → C:\Users\YOU\AppData\...
```

### Option C — One command, straight from GitHub (no PyPI release needed)
Puts both `openalex` and `openalex-mcp` permanently on your `PATH` — nothing to `cd`
into, nothing to activate:
```bash
uv tool install git+https://github.com/JOSETRA44/openalex-mcp
# or, if you use pipx instead of uv:
pipx install git+https://github.com/JOSETRA44/openalex-mcp
```
Then verify: `openalex --version`. Upgrade later with `uv tool upgrade openalex-mcp` /
`pipx upgrade openalex-mcp`, or re-run the install command to pick up the latest commit.

### Option D — From source (for contributing)
```bash
git clone https://github.com/JOSETRA44/openalex-mcp.git
cd openalex-mcp
uv sync                # installs openalex + openalex-mcp into .venv/
cp .env.example .env   # edit .env with your key
uv run openalex-mcp    # run the MCP server directly
.venv/bin/openalex --help   # or .venv\Scripts\openalex.exe --help on Windows
```
Prefer the CLI on your global `PATH` while developing? `uv tool install --editable .`
installs it globally and keeps tracking your source edits live — no reinstall needed
after each change.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `OPENALEX_API_KEY` | Recommended | — | Free API key from [openalex.org/settings/api](https://openalex.org/settings/api) |
| `OPENALEX_EMAIL` | Alt to key | — | Your email — uses the "polite pool" (slower but free, no key) |
| `OPENALEX_CACHE_TTL` | No | `300` | Response cache duration in seconds (0 = disabled) |
| `OPENALEX_MAX_RETRIES` | No | `3` | Retries on rate-limit errors |
| `LOG_LEVEL` | No | `INFO` | `DEBUG` · `INFO` · `WARNING` · `ERROR` |

> Either `OPENALEX_API_KEY` or `OPENALEX_EMAIL` is required. The API key gives 10× more daily quota ($1/day free).

---

## Configuration by Client

Replace `YOUR_API_KEY_HERE` with your actual key in all configs below.

---

### Claude Desktop

**Config file:**
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "openalex": {
      "command": "uvx",
      "args": ["openalex-mcp"],
      "env": {
        "OPENALEX_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

Restart Claude Desktop after saving. You'll see a hammer icon (🔨) confirming tools are loaded.

---

### Claude Code (CLI)

Add to your project's `.mcp.json` in the repo root:

```json
{
  "mcpServers": {
    "openalex": {
      "command": "uvx",
      "args": ["openalex-mcp"],
      "env": {
        "OPENALEX_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

Or from source (local development):

```json
{
  "mcpServers": {
    "openalex": {
      "command": "uv",
      "args": [
        "--directory", "/absolute/path/to/openalex-mcp",
        "run", "openalex-mcp"
      ],
      "env": {
        "OPENALEX_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

Verify with `/mcp` in the Claude Code prompt — you should see `openalex` with 9 tools.

---

### Cursor

**Config file:** `.cursor/mcp.json` in project root, or globally:
- Windows: `%APPDATA%\Cursor\User\globalStorage\cursor.mcp\mcp.json`
- macOS: `~/Library/Application Support/Cursor/User/globalStorage/cursor.mcp/mcp.json`

```json
{
  "mcpServers": {
    "openalex": {
      "command": "uvx",
      "args": ["openalex-mcp"],
      "env": {
        "OPENALEX_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

**Settings → Features → MCP** → toggle on → reload window.

---

### VS Code + GitHub Copilot

Create `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "openalex": {
      "type": "stdio",
      "command": "uvx",
      "args": ["openalex-mcp"],
      "env": {
        "OPENALEX_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

**Ctrl+Shift+P** → `GitHub Copilot: Configure MCP`

---

### Windsurf

**Config file:**
- Windows: `%APPDATA%\Codeium\windsurf\mcp_config.json`
- macOS: `~/.codeium/windsurf/mcp_config.json`

```json
{
  "mcpServers": {
    "openalex": {
      "command": "uvx",
      "args": ["openalex-mcp"],
      "env": {
        "OPENALEX_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

---

### Zed

Edit `~/.config/zed/settings.json`:

```json
{
  "context_servers": {
    "openalex": {
      "command": {
        "path": "uvx",
        "args": ["openalex-mcp"],
        "env": {
          "OPENALEX_API_KEY": "YOUR_API_KEY_HERE"
        }
      }
    }
  }
}
```

---

### Continue.dev

Edit `.continue/config.yaml`:

```yaml
mcpServers:
  - name: openalex
    command: uvx
    args:
      - openalex-mcp
    env:
      OPENALEX_API_KEY: "YOUR_API_KEY_HERE"
```

---

### Any other MCP client (generic stdio)

```
command: uvx
args:    ["openalex-mcp"]
env:     OPENALEX_API_KEY=YOUR_API_KEY_HERE
```

---

## Automated Setup Script

Auto-detect your installed clients and configure them:

```bash
# Interactive
python setup_mcp.py

# Non-interactive — configure all detected clients
python setup_mcp.py --key YOUR_API_KEY_HERE --yes

# Preview without writing files
python setup_mcp.py --key YOUR_API_KEY_HERE --dry-run --yes

# Show detected clients only
python setup_mcp.py --list

# Also install the openalex-researcher agent skill (needs Node.js/npm)
python setup_mcp.py --key YOUR_API_KEY_HERE --yes --with-skill
```

The script backs up existing config files before modifying them. It also offers
(interactively, or via `--with-skill`/`--no-skill`) to install the
[`openalex-researcher` agent skill](#agent-skill) via `npx skills` — a separate,
explicit step since it touches the network and your agent's skills directory.

---

## Available Tools (9 total)

| Tool | What it does |
|------|-------------|
| `openalex_search_works` | Keyword + filter search over 250M+ scholarly works |
| `openalex_get_work` | Full metadata for one work (by OpenAlex ID, DOI, or PubMed ID) |
| `openalex_search_authors` | Find researchers by name, institution, ORCID, or metrics |
| `openalex_get_author` | Author profile: h-index, i10-index, citations by year, topics |
| `openalex_search_institutions` | Search universities and research organizations by name/country |
| `openalex_get_institution` | Institution details: country, type, h-index, top topics |
| `openalex_search_sources` | Search journals, conferences, and repositories |
| `openalex_get_source` | Source details: ISSN, publisher, OA status, h-index |
| `openalex_aggregate_works` | Group/count works by year, type, country, topic, etc. |

### MCP Resource

| Resource | Contents |
|----------|----------|
| `openalex://filter-reference` | Complete filter syntax: 100+ field codes, operators, and examples |

---

## CLI (Command Line)

This package also installs an `openalex` command — a standalone terminal client for OpenAlex, no MCP client required. Every subcommand calls the exact same tool functions the MCP server uses (`src/openalex_mcp/tools/*.py`), so results match 1:1.

### Install
```bash
uv tool install git+https://github.com/JOSETRA44/openalex-mcp   # one command, global PATH — see Installation Options
openalex --help                 # confirm it's on your PATH
```
`pip install openalex-mcp` and `uv sync` (from a source checkout) also install it — see [Installation Options](#installation-options) for every method.

### Commands

| Command | Mirrors | What it does |
|---------|---------|---------------|
| `openalex search-works <query>` | `openalex_search_works` | Search works |
| `openalex get-work <id>` | `openalex_get_work` | Full work metadata |
| `openalex search-authors <query>` | `openalex_search_authors` | Search researchers |
| `openalex get-author <id>` | `openalex_get_author` | Full author profile |
| `openalex search-institutions <query>` | `openalex_search_institutions` | Search institutions |
| `openalex get-institution <id>` | `openalex_get_institution` | Full institution details |
| `openalex search-sources <query>` | `openalex_search_sources` | Search journals/venues |
| `openalex get-source <id>` | `openalex_get_source` | Full source details |
| `openalex aggregate-works <group_by>` | `openalex_aggregate_works` | Group/count works |
| `openalex filter-guide` | `openalex://filter-reference` | Print the filter syntax reference |
| `openalex config` | — | Show resolved settings; `--test` makes a live request to confirm your key/email works |
| `openalex completion {bash,zsh,powershell}` | — | Print a shell tab-completion script |

Run `openalex <command> --help` for that command's flags. Global flags on every command:
- `--json` — raw machine-readable output instead of a table (pipe into `jq`, script it)
- `-o, --output FILE` — write output to a file instead of stdout
- `--api-key` / `--email` — override `.env` for a single call

```bash
openalex search-works "federated learning privacy" -f "publication_year:>2021,type:article" -s "cited_by_count:desc"
openalex get-work 10.1038/s41586-021-03819-2
openalex search-authors "Geoffrey Hinton"
openalex aggregate-works publication_year -f "institutions.id:I865918315" --json | jq '.groups[0]'
openalex config --test                       # confirm your API key actually works
eval "$(openalex completion bash)"           # tab-completion in your current shell
```

Auth and settings come from the same environment variables as the MCP server — see [Environment Variables](#environment-variables).

---

## Agent Skill

A ready-made [Agent Skill](https://www.anthropic.com/news/skills) lives at
[`skills/openalex-researcher/`](skills/openalex-researcher/SKILL.md) — it teaches any
skill-aware agent (Claude Code, Claude.ai, etc.) the tool-selection logic, filter
patterns, and output shapes for OpenAlex, and works whether the agent has the MCP
server connected (uses the `openalex_*` tools) or not (falls back to the `openalex` CLI
via Bash — see `skills/openalex-researcher/references/cli-usage.md`).

```bash
# Install with the skills CLI (https://github.com/vercel-labs/skills)
npx skills add JOSETRA44/openalex-mcp --skill openalex-researcher

# Or let setup_mcp.py offer it alongside MCP client configuration
python setup_mcp.py --key YOUR_API_KEY_HERE --yes --with-skill
```

---

## Example Queries

```python
# Find recent papers on a topic
openalex_search_works(
    query="federated learning privacy",
    filters="publication_year:>2021,type:article",
    sort="cited_by_count:desc"
)

# Get full paper details by DOI
openalex_get_work("10.1038/s41586-021-03819-2")

# Find an author and get their profile
openalex_search_authors(query="Geoffrey Hinton")
openalex_get_author("A2208157607")

# Find an institution, then see its recent output
openalex_search_institutions(query="UNAM", country_code="MX")
openalex_search_works(
    filters="institutions.id:I865918315,publication_year:>2020",
    sort="cited_by_count:desc"
)

# Annual publication trend for a topic
openalex_aggregate_works(
    group_by="publication_year",
    filters="type:article",
    query="machine learning"
)

# Find open-access journals in a field
openalex_search_sources(
    query="bioinformatics",
    is_oa=True,
    source_type="journal"
)
```

---

## Filter Quick Reference

| Pattern | Example |
|---------|---------|
| Year range | `publication_year:2020-2024` |
| Newer than | `publication_year:>2021` |
| Work type | `type:article` · `type:preprint` · `type:book` |
| Open access only | `open_access.is_oa:true` |
| Highly cited | `cited_by_count:>100` |
| By institution | `institutions.id:I97018004` |
| By country | `institutions.country_code:US` |
| In a journal | `primary_location.source.id:S137773608` |
| By language | `language:en` · `language:es` · `language:zh` |
| Papers citing a work | `cites:W2741809807` |
| Has DOI | `has_doi:true` |
| Has abstract | `has_abstract:true` |

For the full filter reference, read the `openalex://filter-reference` resource or see [developers.openalex.org](https://developers.openalex.org).

---

## Rate Limits & Quotas

| Auth method | Daily budget | Calls/second |
|-------------|:-----------:|:------------:|
| API key (free) | $1.00/day | ~10 |
| Email (polite pool) | $0.10/day | ~3 |
| No auth | $0.10/day | ~1 |

The server tracks rate-limit headers and automatically sleeps when the quota is low.

**Action costs (free tier):**
| Action | Daily allowance |
|--------|:--------------:|
| Get single entity (by ID/DOI) | Unlimited |
| List + filter | 10,000 calls / 1M results |
| Full-text search | 1,000 calls / 100K results |

> **Tip:** Use `openalex_get_work` (unlimited) for single-record lookups rather than search.

---

## Verify It's Working

### MCP Inspector (interactive UI)
```bash
npx @modelcontextprotocol/inspector uvx openalex-mcp
```
Open the URL, click **Connect**, **List Tools** — you should see all 9 tools.

### Quick smoke test
```bash
echo "" | OPENALEX_API_KEY=your_key uvx openalex-mcp
# Should start without errors, then exit when stdin closes
```

### Run unit tests (source install)
```bash
uv sync --group dev
uv run pytest tests/ -v
# Expected: all passed (no network required)
```

---

## Troubleshooting

### "Configuration error: Set OPENALEX_API_KEY..."
Add `OPENALEX_API_KEY` to your MCP client's `env` block. Get a free key at [openalex.org/settings/api](https://openalex.org/settings/api).

### "command not found: uvx"
Install uv: [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/)

### 401 error
API key is invalid. Regenerate at [openalex.org/settings/api](https://openalex.org/settings/api).

### 404 error on a work/author/institution
The identifier may be wrong. Try looking up the entity with a search tool first, then use the returned `openalex_id`.

### "uvx openalex-mcp" slow on first run
uv is downloading and caching the package — subsequent starts are instant (~0.2s).

### Tools appear but return empty results
Broaden your query: remove `publication_year` filters, or try `query=` instead of `filters=`.

---

## vs. Scopus / Web of Science

| | OpenAlex | Scopus | Web of Science |
|--|:-------:|:------:|:--------------:|
| Cost | **Free** | Subscription | Subscription |
| Coverage | 250M+ works | 90M works | 170M works |
| Open data | **CC0** | Proprietary | Proprietary |
| API quota | 10K calls/day | 20K/week | Limited |
| Non-English | **Excellent** | Good | Fair |
| Full-text links | Yes | Partial | Partial |

---

## Project Structure

```
openalex-mcp/
├── src/openalex_mcp/
│   ├── server.py           # FastMCP entry point (registers tools as MCP tools)
│   ├── cli.py              # `openalex` CLI entry point (calls the same tool functions)
│   ├── cli_output.py       # Human-readable table/detail rendering for the CLI
│   ├── completion.py       # Shell completion script generators (bash/zsh/powershell)
│   ├── config.py           # Env var configuration (pydantic-settings)
│   ├── client.py           # Async HTTP client + TTL cache + rate limiting
│   ├── exceptions.py       # Error hierarchy
│   ├── formatters.py       # Raw OpenAlex JSON → clean AI-friendly dicts
│   ├── tools/              # Core tool functions, shared by server.py and cli.py
│   └── resources/          # openalex://filter-reference static resource
├── skills/openalex-researcher/   # Agent skill (npx skills add JOSETRA44/openalex-mcp --skill openalex-researcher)
│   ├── SKILL.md
│   └── references/         # Filter syntax, workflows, output reference, CLI usage
├── tests/                  # Unit tests (no network required)
├── setup_mcp.py            # Automated config installer (MCP clients + optional agent skill)
├── .env.example            # Environment variable template
└── pyproject.toml          # Package definition (openalex-mcp + openalex entry points)
```

---

## CLI for agents

250M+ scholarly works with no API key required — the widest free net to cast first.

This CLI follows [`ARSENAL-SPEC.md`](../ARSENAL-SPEC.md), the contract every research
tool in this workspace shares: an agent that can drive one can drive all of them.

### Discover it without reading this file

```bash
openalex describe --json          # every command, argument, row field and example
openalex describe <command> --json
```

The manifest is derived from the parser itself, so it cannot drift out of date.

### Output

`-f, --format` accepts `table`, `json`, `jsonl`, `csv`, `md`; `-o FILE` writes to a file; `-q` silences notes.
**Data goes to stdout, notes and progress to stderr** — piping to `jq` always yields
parseable JSON.

`--format json` returns the standard envelope:

```json
{
  "ok": true,
  "command": "search-works",
  "source": "openalex",
  "fetched_at": "2026-08-21T14:03:11Z",
  "cached": false,
  "count": 10,
  "meta": {},
  "data": {},
  "rows": []
}
```

`count` always equals `len(rows)`. An empty result is exit 0, not an error. Failures
return an error envelope carrying `error.code`, `error.message` and an actionable
`error.hint`, printed to stdout in machine formats so a pipeline can inspect it.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | ok |
| 1 | api |
| 2 | usage |
| 3 | not_found |
| 4 | auth |
| 5 | rate_limit |
| 6 | network |

### Cache

Results are cached on disk and survive between invocations, so a repeated query is
instant. `--refresh` refetches and rewrites; `--no-cache` skips it entirely; the
envelope reports `cached`.

```bash
openalex cache stats -f json
openalex cache clear
```

### Recipes

```bash
openalex search-works 'graph neural networks' -f jsonl --all --max 500
openalex search-works --filters 'publication_year:2024,type:article' -n 200 -f csv -o works.csv
openalex get-work 10.1038/s41586-021-03819-2 -f json
openalex get-work W2741809807 -f md
openalex search-authors 'Geoffrey Hinton' -n 5 -f json
```

Or through the workspace-wide entry point: `arsenal run openalex <command> ...`,
and `arsenal doctor openalex --live` to check this CLI still honours the contract.

## Troubleshooting

**`openalex: command not found` after installing**
`uv tool install` puts binaries in `~/.local/bin`. Add it to your `PATH`, or use
`uvx openalex-mcp` which needs no install at all.

**The MCP server starts and then just sits there**
That is correct. An stdio MCP server waits on stdin for its client; it is not
hung. Run it through your MCP client, not directly in a terminal.

**`429 Too Many Requests`**
You are in the anonymous pool. Set `OPENALEX_EMAIL` to your real address to join
the polite pool. The CLI reports this as exit code 5.

**Results seem stale**
Responses are cached on disk between runs. Use `--refresh` to refetch, or
`openalex cache clear` to wipe it.

## Documentation

| Document | What's in it |
|---|---|
| [`CHANGELOG.md`](CHANGELOG.md) | What changed in each release |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Dev setup, the CLI contract, how to run the tests |
| [`SECURITY.md`](SECURITY.md) | What this server sends and where; how to report a vulnerability |
| [`server.json`](server.json) | Registry metadata for the official MCP registry |
| [`../ARSENAL-SPEC.md`](../ARSENAL-SPEC.md) | The CLI contract shared by every research server here |

## Licence

MIT — see [`LICENSE`](LICENSE).
