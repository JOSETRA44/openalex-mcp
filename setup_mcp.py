#!/usr/bin/env python3
"""
Automated OpenAlex MCP setup script.

Detects installed MCP clients and adds the openalex server configuration.
Backs up existing config files before modifying.

Usage:
    python setup_mcp.py               # interactive
    python setup_mcp.py --key KEY     # non-interactive
    python setup_mcp.py --list        # show detected clients only
    python setup_mcp.py --dry-run --key KEY --yes
"""

import argparse
import json
import os
import platform
import shutil
import sys
from datetime import datetime
from pathlib import Path


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _home() -> Path:
    return Path.home()


def _appdata() -> Path:
    return Path(os.environ.get("APPDATA", _home() / "AppData" / "Roaming"))


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _uvx_command() -> list[str]:
    if _is_windows():
        uvx = shutil.which("uvx") or shutil.which("uvx.exe")
    else:
        uvx = shutil.which("uvx")
    if uvx:
        return [uvx, "openalex-mcp"]
    scopus = shutil.which("openalex-mcp") or shutil.which("openalex-mcp.exe")
    if scopus:
        return [scopus]
    return ["uvx", "openalex-mcp"]


def _server_block(api_key: str) -> dict:
    cmd = _uvx_command()
    return {
        "command": cmd[0],
        "args": cmd[1:],
        "env": {"OPENALEX_API_KEY": api_key},
    }


def _backup(path: Path) -> None:
    if path.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = path.with_suffix(f".backup_{ts}{path.suffix}")
        shutil.copy2(path, backup)
        print(f"  Backed up existing config to {backup.name}")


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8").strip()
        return json.loads(text) if text else {}
    except json.JSONDecodeError:
        print(f"  WARNING: Could not parse {path} as JSON -- skipping.")
        return None


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ─── Client Definitions ───────────────────────────────────────────────────────

def _claude_desktop_path() -> Path | None:
    if _is_windows():
        return _appdata() / "Claude" / "claude_desktop_config.json"
    elif platform.system() == "Darwin":
        return _home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    return None


def _cursor_path() -> Path | None:
    if _is_windows():
        base = _appdata() / "Cursor" / "User" / "globalStorage" / "cursor.mcp"
    elif platform.system() == "Darwin":
        base = _home() / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "cursor.mcp"
    else:
        base = _home() / ".config" / "Cursor" / "User" / "globalStorage" / "cursor.mcp"
    return base / "mcp.json"


def _windsurf_path() -> Path | None:
    if _is_windows():
        return _appdata() / "Codeium" / "windsurf" / "mcp_config.json"
    return _home() / ".codeium" / "windsurf" / "mcp_config.json"


def _vscode_workspace_path() -> Path | None:
    return Path(".vscode") / "mcp.json"


CLIENTS = [
    {
        "name": "Claude Desktop",
        "path_fn": _claude_desktop_path,
        "key": "mcpServers",
        "format": "standard",
        "note": "Restart Claude Desktop to apply.",
    },
    {
        "name": "Cursor (global)",
        "path_fn": _cursor_path,
        "key": "mcpServers",
        "format": "standard",
        "note": "Reload Cursor window (Ctrl+Shift+P -> Reload Window).",
    },
    {
        "name": "Windsurf",
        "path_fn": _windsurf_path,
        "key": "mcpServers",
        "format": "standard",
        "note": "Restart Windsurf to apply.",
    },
    {
        "name": "VS Code (workspace)",
        "path_fn": _vscode_workspace_path,
        "key": "servers",
        "format": "vscode",
        "note": "VS Code: Ctrl+Shift+P -> GitHub Copilot: Configure MCP.",
    },
]


# ─── Installers ───────────────────────────────────────────────────────────────

def _install_standard(path: Path, top_key: str, api_key: str, dry_run: bool) -> bool:
    data = _read_json(path)
    if data is None:
        return False
    servers = data.setdefault(top_key, {})
    if "openalex" in servers:
        print("  'openalex' entry already exists -- updating.")
    servers["openalex"] = _server_block(api_key)
    if not dry_run:
        _backup(path)
        _write_json(path, data)
    return True


def _install_vscode(path: Path, api_key: str, dry_run: bool) -> bool:
    data = _read_json(path)
    if data is None:
        return False
    block = _server_block(api_key)
    vscode_block = {
        "type": "stdio",
        "command": block["command"],
        "args": block["args"],
        "env": block["env"],
    }
    servers = data.setdefault("servers", {})
    if "openalex" in servers:
        print("  'openalex' entry already exists -- updating.")
    servers["openalex"] = vscode_block
    if not dry_run:
        _backup(path)
        _write_json(path, data)
    return True


def detect_clients() -> list[dict]:
    found = []
    for client in CLIENTS:
        path = client["path_fn"]()
        if path is None:
            continue
        parent_exists = path.parent.exists() or client["name"].startswith("VS Code")
        if parent_exists:
            found.append({**client, "path": path})
    return found


def install(api_key: str, selected: list[dict], dry_run: bool = False) -> None:
    ok, skip = [], []
    for client in selected:
        path: Path = client["path"]
        prefix = "[DRY RUN] " if dry_run else ""
        print(f"\n{prefix}Configuring {client['name']}...")
        print(f"  Config: {path}")
        if client["format"] == "vscode":
            success = _install_vscode(path, api_key, dry_run)
        else:
            success = _install_standard(path, client["key"], api_key, dry_run)
        if success:
            print(f"  Done. {client['note']}")
            ok.append(client["name"])
        else:
            skip.append(client["name"])

    print("\n" + "-" * 50)
    if ok:
        print(f"[OK] Configured: {', '.join(ok)}")
    if skip:
        print(f"[SKIP] Skipped (parse error): {', '.join(skip)}")
    if not dry_run and ok:
        print("\nNext steps:")
        print("  1. Restart the AI clients listed above.")
        print("  2. Ask: 'Search OpenAlex for recent papers on climate change and agriculture'")
        print("  3. The agent will use openalex_search_works automatically.")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Automated OpenAlex MCP configuration installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--key", metavar="API_KEY", help="OpenAlex API key (skips interactive prompt)")
    parser.add_argument("--list", action="store_true", help="List detected clients and exit")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing")
    parser.add_argument("--yes", "-y", action="store_true", help="Configure all clients without prompting")
    args = parser.parse_args()

    print("=" * 42)
    print("   OpenAlex MCP -- Setup Assistant")
    print("=" * 42)
    print()

    detected = detect_clients()

    if not detected:
        print("No supported MCP clients detected on this machine.")
        print("Supported: Claude Desktop, Cursor, Windsurf, VS Code")
        print("\nFor manual setup, see: https://github.com/JOSETRA44/openalex-mcp")
        sys.exit(0)

    print(f"Detected {len(detected)} client(s):")
    for c in detected:
        exists = "exists" if c["path"].exists() else "will create"
        print(f"  - {c['name']:25s} {c['path']}  [{exists}]")

    if args.list:
        sys.exit(0)

    print()

    if args.yes:
        selected = detected
    else:
        print("Configure all detected clients? [Y/n] ", end="", flush=True)
        answer = input().strip().lower()
        if answer in ("n", "no"):
            print("Select clients to configure (comma-separated numbers, e.g. 1,3):")
            for i, c in enumerate(detected, 1):
                print(f"  {i}. {c['name']}")
            raw = input("Your selection: ").strip()
            try:
                indices = [int(x.strip()) - 1 for x in raw.split(",")]
                selected = [detected[i] for i in indices if 0 <= i < len(detected)]
            except (ValueError, IndexError):
                print("Invalid selection. Exiting.")
                sys.exit(1)
        else:
            selected = detected

    if not selected:
        print("Nothing to do.")
        sys.exit(0)

    api_key = args.key
    if not api_key:
        print("\nEnter your OpenAlex API key (from https://openalex.org/settings/api):")
        print("  > Free key — takes 30 seconds to get")
        print("  > Will be stored in MCP config files only, not in this script")
        api_key = input("API key: ").strip()
        if not api_key:
            print("No API key provided. Exiting.")
            sys.exit(1)

    install(api_key, selected, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
