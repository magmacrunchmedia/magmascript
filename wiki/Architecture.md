# Architecture

## Overview

MagmaScript is a tree-walk interpreter with a domain bridge to external systems.

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
│   └── domain_bridge.py  # Domain proxy system
├── domains/        # Domain clients
│   ├── mcp/        # MCP server client
│   ├── pi/         # Raspberry Pi SSH
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
Source code → Lexer → Tokens → Parser → AST → Interpreter → Result
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
