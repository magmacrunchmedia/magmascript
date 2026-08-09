# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-08-09

### Added
- Dict literals: `{"name": "Jake", "age": 30}`
- List comprehensions: `[x * 2 for x in items]` with optional filter `[x for x in items if x > 5]`
- String methods: `.split()`, `.join()`, `.upper()`, `.lower()`, `.contains()`, `.replace()`, `.length()`, `.startswith()`, `.endswith()`, `.strip()`
- Method chaining on strings: `"  Hello World  ".strip().lower()`
- `keys()` and `values()` now work on dict literals
- 37 new tests for dict literals, list comprehensions, and string methods (258 total)

## [1.2.0] - 2026-08-09

### Added
- MagmaScript language interpreter for `.mgs` files
- Tree-walk interpreter with lexer, parser, and AST
- Python-inspired syntax with brace and indent blocks
- F-string interpolation: `f"hello {name}!"`
- Arrow functions: `x -> x * 2`
- Function definitions: `fn add(a, b) { a + b }`
- Control flow: `if`/`else`, `for`/`in`, `while`
- Domain bridge: `mcp`, `pi`, `gh`, `media`, `scores`, `rights` available in .mgs scripts
- Built-in functions: `print`, `len`, `type`, `range`, `str`, `int`, `float`, `abs`, `min`, `max`, `sum`, `keys`, `values`
- Interactive REPL (`magmascript repl`)
- CLI command to run scripts (`magmascript run script.mgs`)
- 163 tests covering lexer, parser, interpreter, environment, and integration
- Example scripts: `hello.mgs`, `fibonacci.mgs`, `domain-example.mgs`, `top-scores.mgs`

### Fixed
- Function scope isolation: variables defined inside functions no longer leak to global scope
- Indent-based blocks now work correctly with the lexer
- Domain bridge no longer wraps callable objects in DataclassWrapper

## [1.1.0]

### Added
- Multi-provider media search (Openverse, Pexels, Pixabay, Met Museum, Smithsonian, Archive)
- GitHub discussions support via GraphQL
- Rights domain for ISRC/ISWC/ASCAP lookups
- Archive page validation and cache baking
- Site search index builder
- Shell helpers library (`lib/magmascript.sh`)
- JavaScript MCP client (`lib/magmascript.js`)
- Python convenience wrapper (`lib/magmascript.py`)
- Homebrew formula auto-update on release

### Changed
- Improved error messages across all domains
- Better caching with atomic writes and per-domain TTLs

## [1.0.0]

### Added
- Initial release
- MCP server tools (search, entities, scoreboards, scores, games, archive, bots, discogs, jukebox, TV, themes)
- Raspberry Pi management via SSH
- GitHub operations (workflows, issues, file CRUD, atomic commits)
- MusicBrainz backup client
- Last.fm play count tracking
- Cache management with TTL support
- Domain-first CLI architecture
