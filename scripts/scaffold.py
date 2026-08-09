#!/usr/bin/env python3
"""Domain scaffolder for magmascript.

Generates boilerplate for new domains.

Usage:
    python scripts/scaffold.py <name> --description "..." --transport <ssh|rpc|http>
    python scripts/scaffold.py <name> --description "..." --transport ssh --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOMAINS_DIR = PROJECT_ROOT / "magmascript" / "domains"
CLI_DIR = PROJECT_ROOT / "cli"
LIB_FILE = PROJECT_ROOT / "lib" / "magmascript.sh"
CLI_FILE = PROJECT_ROOT / "magmascript" / "cli.py"
DOMAINS_INIT = DOMAINS_DIR / "__init__.py"


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

def _init_py(name: str, description: str, client_class: str, tool_names: list[str]) -> str:
    imports = "\n".join(f"from magmascript.domains.{name}.tools import {t}" for t in tool_names)
    all_items = ",\n".join(f'    "{t}",' for t in [client_class] + tool_names)
    return f'''"""{description}."""

{imports}
from magmascript.domains.{name}.client import {client_class}
from magmascript.core.registry import register_domain

# Register this domain
register_domain("{name}", {client_class})

__all__ = [
{all_items}
]
'''


def _tools_py(name: str, description: str, tool_names: list[str]) -> str:
    classes = []
    for t in tool_names:
        classes.append(f'''@dataclass
class {t}:
    """TODO: Add fields for {t}."""
    id: str
    name: str
''')
    return f'''"""Typed result dataclasses for the {description}."""

from __future__ import annotations

from dataclasses import dataclass, field


{"".join(classes)}
# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def parse_results(text: str) -> list[dict]:
    """TODO: Parse text output into structured data."""
    results = []
    for line in text.splitlines():
        # TODO: implement parsing
        pass
    return results
'''


def _client_py_ssh(name: str, description: str, client_class: str) -> str:
    return f'''"""{description}.

Uses SSH for remote command execution.
"""

from __future__ import annotations

import subprocess

from magmascript.core.config import Config, get_config
from magmascript.core.exceptions import SSHError
from magmascript.domains.{name}.tools import parse_results


class {client_class}:
    """{description}."""

    def __init__(self, config: Config | None = None):
        cfg = config or get_config()
        self._host = cfg.pi.host
        self._user = cfg.pi.user

    def _ssh(self, cmd: str, *, timeout: int = 15) -> str:
        """Run a command on the Pi via SSH. Returns stdout."""
        try:
            user_host = f"{{self._user}}@{{self._host}}"
            result = subprocess.run(
                [
                    "ssh",
                    "-o", "ConnectTimeout=5",
                    "-o", "StrictHostKeyChecking=no",
                    user_host,
                    cmd,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0:
                raise SSHError(
                    f"SSH failed (exit {{result.returncode}}): {{result.stderr.strip()}}",
                    host=self._host,
                    code=result.returncode,
                )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise SSHError(f"SSH to {{self._host}} timed out", host=self._host)
        except SSHError:
            raise
        except Exception as e:
            raise SSHError(f"SSH to {{self._host}} failed: {{e}}", host=self._host)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def search(self, query: str) -> str:
        """TODO: Implement search."""
        return self._ssh(f"echo 'TODO: search for {{query}}'")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
'''


def _client_py_rpc(name: str, description: str, client_class: str) -> str:
    return f'''"""{description}.

Uses RPC client for JSON-RPC communication.
"""

from __future__ import annotations

from magmascript.core.config import Config, get_config
from magmascript.core.rpc import RPCClient
from magmascript.domains.{name}.tools import parse_results


class {client_class}:
    """{description}."""

    def __init__(self, config: Config | None = None):
        cfg = config or get_config()
        self._rpc = RPCClient(url="", api_key="")  # TODO: configure

    def _call(self, method: str, params: dict | None = None) -> str:
        """Call an RPC method and return the result."""
        return self._rpc.call_tool(method, params or {{}})

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def search(self, query: str) -> str:
        """TODO: Implement search."""
        return self._call("search", {{"query": query}})

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        self._rpc.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
'''


def _client_py_http(name: str, description: str, client_class: str) -> str:
    return f'''"""{description}.

Uses HTTP API for remote calls.
"""

from __future__ import annotations

import httpx

from magmascript.core.config import Config, get_config
from magmascript.core.exceptions import APIError
from magmascript.domains.{name}.tools import parse_results


class {client_class}:
    """{description}."""

    def __init__(self, config: Config | None = None):
        cfg = config or get_config()
        self._http = httpx.Client(timeout=30.0)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def search(self, query: str) -> str:
        """TODO: Implement search."""
        resp = self._http.get(f"https://api.example.com/search?q={{query}}")
        resp.raise_for_status()
        return resp.text

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
'''


def _cli_wrapper(name: str, description: str) -> str:
    return f'''#!/usr/bin/env bash
# magmascript {description} wrapper
#
# Usage:
#   {name} search "query"
#
# Install:
#   chmod +x cli/{name}
#   ln -s $(pwd)/cli/{name} ~/bin/{name}

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if command -v magmascript &>/dev/null; then
    exec magmascript {name} "$@"
fi

exec python3 -m magmascript.cli {name} "$@"
'''


# ---------------------------------------------------------------------------
# File edits
# ---------------------------------------------------------------------------

def _edit_domains_init(name: str) -> None:
    """Add import and __all__ entry to domains/__init__.py."""
    content = DOMAINS_INIT.read_text()

    # For Python imports, replace hyphens with underscores
    import_name = name.replace("-", "_")

    # Add import before the __all__ line
    import_line = f"from magmascript.domains import {import_name}  # noqa: F401\n"
    if import_line not in content:
        # Find the last import line and add after it
        lines = content.split("\n")
        last_import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("from magmascript.domains import"):
                last_import_idx = i
        lines.insert(last_import_idx + 1, import_line.rstrip())
        content = "\n".join(lines)

    # Update __all__
    if f'"{name}"' not in content:
        import re
        content = re.sub(
            r'__all__ = \[(.*?)\]',
            lambda m: m.group(0).replace("]", f', "{name}"]'),
            content,
        )

    DOMAINS_INIT.write_text(content)


def _edit_cli_py(name: str, client_class: str, description: str) -> None:
    """Add dispatch block, usage, and dispatch function to cli.py."""
    content = CLI_FILE.read_text()

    # 1. Add to usage() Domains section
    domain_line = f"    {name:<12}{description}"
    if domain_line not in content:
        content = content.replace(
            "    cache       Cache management (stats, clear)",
            f"    cache       Cache management (stats, clear)\n{domain_line}",
        )

    # 2. Add dispatch block in main() before the "else" clause
    dispatch_block = f'''
        elif domain == "{name}":
            from magmascript.domains.{name} import {client_class}
            client = {client_class}(config)
            try:
                _dispatch_{name}(action, rest, client, fmt)
            finally:
                client.close()
'''
    if f'domain == "{name}"' not in content:
        content = content.replace(
            '        else:\n            print(f"Unknown domain:',
            f"{dispatch_block}        else:\n            print(f\"Unknown domain:",
        )

    # 3. Add dispatch function before if __name__
    dispatch_func = f'''

def _dispatch_{name}(action: str, args: list[str], client, fmt: str):
    """Dispatch {description} subcommands."""
    if not action or action == "--help":
        usage()

    if action == "search":
        if not args:
            print("Usage: {name} search <query>", file=sys.stderr)
            sys.exit(1)
        result = client.search(args[0])
        print(result)

    else:
        print(f"Unknown {name} action: {{action!r}}", file=sys.stderr)
        print("Run 'magmascript {name} --help' for available actions.", file=sys.stderr)
        sys.exit(1)


'''
    if f"_dispatch_{name}" not in content:
        content = content.replace(
            "\nif __name__",
            f"{dispatch_func}if __name__",
        )

    # 4. Update error message
    old_error = 'Available: mcp, pi, gh, media, scores, cache'
    new_error = f'Available: mcp, pi, gh, media, scores, cache, {name}'
    if new_error not in content:
        content = content.replace(old_error, new_error)

    CLI_FILE.write_text(content)


def _edit_magmascript_sh(name: str, description: str) -> None:
    """Add shell helpers to lib/magmascript.sh."""
    content = LIB_FILE.read_text()

    helpers = f'''
# ── {description} helpers ────────────────────────────────────────────────────

{name}_search() {{
    $_MAGMASCRIPT {name} search "$@"
}}

'''

    # Insert before the final echo
    echo_line = 'echo "Scores: scores_list, scores_get, scores_report"'
    if f"{name}_search" not in content:
        content = content.replace(
            echo_line,
            f"{echo_line}\n{helpers.rstrip()}",
        )

    LIB_FILE.write_text(content)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Scaffold a new magmascript domain")
    parser.add_argument("name", help="Domain name (lowercase, e.g. 'isrc')")
    parser.add_argument("--description", "-d", required=True, help="One-line description")
    parser.add_argument("--transport", "-t", choices=["ssh", "rpc", "http"], default="ssh",
                        help="Transport type (default: ssh)")
    parser.add_argument("--tools", nargs="*", default=["Result"],
                        help="Dataclass names for tools.py (default: ['Result'])")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be created without writing files")
    args = parser.parse_args()

    name = args.name.lower().replace(" ", "-")
    description = args.description
    transport = args.transport
    tool_names = args.tools

    # Derive client class name: "isrc" -> "ISRCClient", "discord" -> "DiscordClient"
    client_class = name.replace("-", " ").title().replace(" ", "") + "Client"

    print(f"Scaffolding domain: {name}")
    print(f"  Description: {description}")
    print(f"  Transport: {transport}")
    print(f"  Client class: {client_class}")
    print(f"  Tools: {tool_names}")
    print()

    # Files to create
    domain_dir = DOMAINS_DIR / name
    files_to_create = [
        (domain_dir / "__init__.py", _init_py(name, description, client_class, tool_names)),
        (domain_dir / "tools.py", _tools_py(name, description, tool_names)),
        (domain_dir / "client.py", {
            "ssh": _client_py_ssh,
            "rpc": _client_py_rpc,
            "http": _client_py_http,
        }[transport](name, description, client_class)),
        (CLI_DIR / name, _cli_wrapper(name, description)),
    ]

    for path, content in files_to_create:
        if args.dry_run:
            print(f"  CREATE {path.relative_to(PROJECT_ROOT)}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            print(f"  ✓ Created {path.relative_to(PROJECT_ROOT)}")

    # Files to edit
    edits = [
        ("domains/__init__.py", lambda: _edit_domains_init(name)),
        ("cli.py", lambda: _edit_cli_py(name, client_class, description)),
        ("lib/magmascript.sh", lambda: _edit_magmascript_sh(name, description)),
    ]

    for desc, edit_fn in edits:
        if args.dry_run:
            print(f"  EDIT   {desc}")
        else:
            edit_fn()
            print(f"  ✓ Updated {desc}")

    print()
    if args.dry_run:
        print("Dry run complete. No files were modified.")
    else:
        print(f"Domain '{name}' scaffolded successfully!")
        print()
        print("Next steps:")
        print(f"  1. Edit magmascript/domains/{name}/client.py — implement your methods")
        print(f"  2. Edit magmascript/domains/{name}/tools.py — add dataclasses and parsers")
        print(f"  3. Run tests: pytest")
        print(f"  4. Test: magmascript {name} --help")


if __name__ == "__main__":
    main()
