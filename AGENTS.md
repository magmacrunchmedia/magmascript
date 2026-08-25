# AGENTS.md — magmascript

Scripting toolkit with domain-first subcommands for managing magmacrunch.com
infrastructure, plus **MagmaScript**: a Python-inspired mini language (`.mgs`
file extension) with a tree-walk interpreter and a domain bridge that exposes
the same domains (mcp, pi, gh, scores, …) inside scripts and the REPL.

## AI Attribution

**No AI attribution.** Do not append `Co-Authored-By: Claude …`, "Generated with
…", or any similar trailer to commit messages, PR bodies, or release notes. If
your tooling adds such a line by default, remove it before committing.

## Layout

```
magmascript/
├── pyproject.toml            # setuptools; entry point: magmascript = magmascript.cli:main
├── magmascript/
│   ├── cli.py                # subcommand dispatch
│   ├── repl.py               # interactive REPL (prompt_toolkit + pygments)
│   ├── core/                 # config, cache, commands, github, registry, rpc, runner
│   ├── domains/              # one package per domain: mcp, pi, mc1, mac, gh,
│   │                         #   scores, archive, mb, lastfm, search, rights, media
│   └── lang/                 # the language: lexer, parser, ast_nodes, interpreter,
│       │                     #   builtins, environment, domain_bridge, tokens
│       └── astheno/          # Asthenosphere: explicit-memory tier (arena, structs)
├── tests/                    # pytest suite (test_lang, test_astheno, test_cli, …)
├── scripts/examples/         # working .mgs example scripts
├── cli/                      # thin shell wrappers (gh, mcp, media, pi)
├── lib/                      # magmascript.sh / .py / .js shell helpers
└── wiki/                     # source for the GitHub wiki pages
```

## Commands

```bash
# Install (editable, with cli + dev extras)
python3 -m venv .venv
.venv/bin/pip install -e ".[all]"        # Windows: .venv\Scripts\pip install -e ".[all]"

# Tests (pytest configured in pyproject: testpaths=tests, addopts="-v --tb=short")
.venv/bin/pytest
.venv/bin/pytest tests/test_lang.py      # single file

# Run a script / the REPL
magmascript scripts/examples/hello.mgs   # shorthand for `magmascript run <file>`
magmascript run scripts/examples/hello.mgs
magmascript repl

# Config check / dashboard
magmascript configure
magmascript magma
```

Config comes from env vars (`MAGMA_API_KEY`, `GITHUB_TOKEN`,
`MAGMACRUNCH_ROOT`) or `~/.config/magmascript/config.toml`.

## Conventions

- **Language identity (do not drift):** MagmaScript is a Python-inspired mini
  language with the `.mgs` extension; a tree-walk interpreter with a domain
  bridge to magmascript modules. Python-like semantics, brace-delimited blocks.
- Nonstandard keywords are deliberate vocabulary, not typos: `intent` = import,
  `haunter` = catch (also names parse errors), `throw fire toad(...)` = raise
  runtime error, `devastate` = undefined-variable error, `contemplate` = type
  error, `spooked(...)` = warning to stderr, `quarry`/`litho` = file read/write.
- The Asthenosphere (`magmascript/lang/astheno/`) is the explicit-memory tier:
  `floorplan` (struct), `garrison`/`scorch` (alloc/free), `bathysphere` (hex
  dump), widths `i8..f64`, no integer promotion. `floorplan` is the **only**
  reserved word it adds; everything else is a shadowable builtin — keep it that
  way so existing scripts never break.
- Third-party packages register domains via the
  `[project.entry-points."magmascript.domains"]` entry point (class taking one
  `config` arg, constructed lazily). Built-in domains win name clashes; a
  failing entry-point import is skipped, never fatal.
- Requires Python >=3.11. Only hard runtime dependency is `httpx`; rich /
  prompt_toolkit / pygments live behind the `cli` extra, so core code must not
  import them unconditionally.
- Update the matching page under `wiki/` when language or domain behavior
  changes; the README and wiki are the reference docs.

## Git

Commit and push as `magmacrunchmedia` — always use the `magmacrunchmedia`
GitHub account for any git/gh operations. **NEVER** use the work account for
anything. No AI attribution trailers, ever.

<!-- Update this file in the same commit as any change to build, test, deploy, or layout. -->
