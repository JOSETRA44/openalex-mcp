# OpenAlex MCP Server

Connects any MCP-compatible AI agent to [OpenAlex](https://openalex.org) — the world's largest **free and open** scholarly database with 250+ million works, 300+ million authors, 100,000+ institutions, and billions of citation links.

**Works with:** Claude Desktop · Claude Code · Cursor · VS Code Copilot · Windsurf · Zed · any MCP client

**No paywall. No institutional access required. CC0 licensed data.**

---

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

### Option A — uvx (recommended)
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

### Option C — From source
```bash
git clone https://github.com/JOSETRA44/openalex-mcp.git
cd openalex-mcp
uv sync
cp .env.example .env   # edit .env with your key
uv run openalex-mcp    # run directly
```

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
```

The script backs up existing config files before modifying them.

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
# Expected: 28 passed
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
│   ├── server.py           # FastMCP entry point
│   ├── config.py           # Env var configuration (pydantic-settings)
│   ├── client.py           # Async HTTP client + TTL cache + rate limiting
│   ├── exceptions.py       # Error hierarchy
│   ├── formatters.py       # Raw OpenAlex JSON → clean AI-friendly dicts
│   ├── tools/              # 9 MCP tools (works, authors, institutions, sources, aggregate)
│   └── resources/          # openalex://filter-reference static resource
├── openalex-researcher/    # Agent skill
│   ├── SKILL.md
│   └── references/         # Filter syntax, workflows, output reference
├── tests/                  # Unit tests (28 cases, no network required)
├── setup_mcp.py            # Automated config installer
├── .env.example            # Environment variable template
└── pyproject.toml          # Package definition
```

---

## License

MIT — see [LICENSE](LICENSE)

Data from OpenAlex is [CC0](https://creativecommons.org/publicdomain/zero/1.0/) (public domain).
