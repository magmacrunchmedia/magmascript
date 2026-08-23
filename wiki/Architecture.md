# Architecture

## Overview

MagmaScript is a two-tier tree-walk interpreter with a domain bridge to external systems. The **dynamic tier** handles Python-like scripting (variables, functions, classes). The **Asthenosphere** is an explicit-memory tier beneath it — fixed-width integers, a real byte arena, and C-layout structs — where the interpreter catches memory faults that C silently ignores.

## Components

```
magmascript/
├── lang/           # Language core
│   ├── lexer.py    # Tokenizer
│   ├── parser.py   # AST generator
│   ├── interpreter.py  # Tree-walk interpreter
│   ├── ast_nodes.py    # AST node definitions
│   ├── environment.py  # Variable scoping
│   ├── builtins.py     # Built-in functions
│   ├── tokens.py       # Token definitions
│   ├── hypnagogia.py   # Pre-execution analysis (unused names, dead code)
│   ├── domain_bridge.py  # Domain proxy system
│   └── astheno/      # Asthenosphere (explicit-memory tier)
│       ├── __init__.py  # Arena, pine, floorplan builtins
│       ├── arena.py     # garrison/scorch/peek/poke
│       ├── floorplan.py # floorplan compiler and layout()
│       ├── numeric.py   # Fixed-width integers (i8..u64, f32, f64)
│       └── dump.py      # bathysphere hex dump
├── domains/        # Domain clients
│   ├── mcp/        # MCP server client
│   ├── pi/         # Raspberry Pi SSH
│   ├── mc1/        # Windows PC SSH/PowerShell
│   ├── gh/         # GitHub API
│   ├── scores/     # Game scores
│   ├── rights/     # Music rights
│   ├── media/      # Media search
│   ├── archive/    # Archive pages
│   ├── mb/         # MusicBrainz
│   ├── lastfm/     # Last.fm
│   └── search/     # Search index
├── core/           # Core infrastructure
│   ├── config.py   # Configuration
│   ├── commands.py # Brand commands (magma, crunch, texas, toast)
│   └── rpc.py      # MCP RPC client
├── cli.py          # CLI entry point
└── repl.py         # Interactive REPL
```

## Language Pipeline

```
Dynamic tier:
  Source code → Lexer → Tokens → Parser → AST → Interpreter → Result

Asthenosphere (runs before execution):
  AST → hypnagogia (unused names, dead code warnings)
```

## Domain Bridge

Domains are Python classes that get wrapped as `DomainProxy` objects and injected into the interpreter's global environment. This allows `.mgs` scripts to call Python functions naturally:

```magmascript
boards = mcp.scoreboards()  // calls Python MCPClient.scoreboards()
```

## Error System

MagmaCrunch-themed error vocabulary:
- `haunter` — syntax/parse errors (caught before execution)
- `fire toad` — runtime errors (caught during execution)
- `devastate` — undefined variable errors
- `contemplate` — type errors
- `spooked` — warnings (non-fatal)
