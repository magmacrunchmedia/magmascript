# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - Unreleased

The Asthenosphere — an explicit-memory tier beneath the dynamic language.

### Added

**The Asthenosphere** — an explicit-memory tier beneath the dynamic language.
Not faster (an `i32` add still costs a Python dispatch); the point is that the
interpreter sees every memory operation and reports what C does silently.

- Fixed-width numbers `i8 i16 i32 i64 u8 u16 u32 u64 f32 f64`. Arithmetic wraps
  like C and announces each wrap. No integer promotion: `i32 + u8` is an error
  pointing at `osmosis()`. `/` truncates toward zero on integer widths rather
  than flooring.
- A real byte arena: `garrison(n)` claims ground, `scorch(p)` releases it,
  pines carry their block's bounds through pointer arithmetic, and `p[i]` /
  `p.peek(w)` / `p.poke(w, v)` read and write it.
- `floorplan Name { field: type }` — structs with C layout rules. Fields may be
  widths, arrays (`u8[16]`), nested floorplans, or `pine[Other]` pointers,
  including self-reference for linked lists. `layout()` prints the padding rows,
  `sizeof()` and `alignof()` report the numbers.
- `bathysphere(p)` — annotated hex dump showing which bytes belong to which
  field and what they decode to. `.arena` does the same for the whole arena in
  the REPL.
- Memory faults, all with the usual caret diagram and all catchable by
  `try`/`haunter`: `quicksand` (use-after-scorch and double-scorch, naming the
  line that scorched), `area does not exist` (out of bounds, with the block's
  extent), and `spooked: ancient weeds` at exit for anything never scorched.
- `hypnagogia` — a single pass before execution reporting names that are bound
  nowhere and statements that can never run. Advisory only, and deliberately
  timid so dynamic code is not flagged.
- Examples: `astheno-list.mgs`, `astheno-packing.mgs`, `astheno-faults.mgs`.
- `wiki/Asthenosphere.md`.

Other additions:
- Index assignment: `a[0] = x`, `d["k"] = v`, and the `+=` / `-=` forms. Previously
  a parse error; lists and dicts were read-only through the index operator.
- Recursion depth guard. Exceeding `MAX_CALL_DEPTH` (500) now raises
  `exploding brain syndrome` with an elided stack trace instead of leaking a raw
  Python `RecursionError`.

### Changed — BREAKING
- Empty dicts are now falsy, matching empty lists and strings. `if {}` previously
  took the true branch.
- The `f` string prefix is now meaningful. Only `f"..."` interpolates; in a plain
  string `{` is an ordinary character. Previously *any* string containing `{` was
  interpolated, so `print("use {braces}")` misbehaved. This also fixes plain
  strings containing an unmatched `{`, which previously raised
  "Unterminated string".

### Fixed
- Errors raised inside a function body now carry the filename and caret diagram.
  The CLI constructs its own `Interpreter`, but only the module-level `run()`
  helper registered it globally, so function bodies executed against a blank
  interpreter with no source text.
- Version skew: `__init__.py` reported 2.2.0 while `pyproject.toml` reported 2.3.0.
- The REPL crashed on Windows. `_repl_basic()` imported `readline` unguarded, so
  the fallback path — the one taken when `prompt_toolkit` is absent — could not
  start at all.
- The enhanced REPL crashed on every platform with a current `prompt_toolkit`.
  `PromptSession` was constructed with `prompt=` and `continuation=`, which are
  not constructor arguments; they are `message=` and `prompt_continuation=`.

### Removed
- `scripts/examples/top-scores.ms`, a pre-1.2.0 sketch whose header still said
  the interpreter was unimplemented.

## [2.2.0] - 2026-08-14

### Added
- MC1 Windows PC domain: `MC1Client` for remote management via SSH/PowerShell
- MC1 service management: list, restart, system info, processes, reboot

### Fixed
- Release workflow race condition: increased PyPI retry window and added wait step

## [2.1.0] - 2026-08-12

### Added
- `.mgs` file shorthand: `magmascript hello.mgs` now works without the `run` subcommand
- Release workflow now triggers on tag push and auto-creates GitHub Releases

## [2.0.1] - 2026-08-12

### Fixed
- Bug fixes and improvements

## [2.0.0] - 2026-08-12

### Added
- Domain bridge with 10 domain clients (mcp, pi, gh, media, scores, rights, archive, mb, lastfm, search)
- `echo()` builtin (alias for print)
- Regex support: `.match()` and `.findall()` on strings
- `in` / `not in` operators for lists, strings, and dicts
- List/string slicing with step support
- Default function parameters
- Multi-assignment with list unpacking
- Classes with `self`, `init`, and methods
- Import system: `intent`, `intent as`, `intent { ... } from`
- `try`/`haunter`/`throw` error handling with MagmaCrunch vocabulary
- 392 tests

### Changed
- Major language expansion from CLI-only to full scripting language
- Domain bridge wraps Python clients as MagmaScript-native objects

## [1.6.0] - 2026-08-09

### Added
- Brand commands: `magma`, `crunch`, `texas`, `toast` — available as both CLI subcommands and REPL dot-commands
- `magma` — system status dashboard (domains, cache stats, version)
- `crunch <target>` — batch pipeline runner (mb, lastfm, search, archive, scores, gh, all)
- `texas <target>` — full/heavy operation (same targets, no shortcuts, force refresh)
- `toast <target>` — burn/clear caches (cache, mb-cache, lastfm-cache, scores-cache, gh-cache, search-index, all)
- `--dry-run` flag support for crunch and texas commands
- 28 new tests for commands and CLI dispatch (306 total)

### Changed
- REPL now includes `.magma`, `.crunch`, `.texas`, `.toast` dot-commands with tab completion
- CLI usage updated with new brand commands

## [1.5.0] - 2026-08-09

### Added
- Enhanced REPL with syntax highlighting and tab completion (via prompt_toolkit + Pygments)
- Pygments lexer for MagmaScript (`*.mgs` files)
- Tab completion for keywords, builtins, domain names, user-defined variables, domain methods, and string methods
- Persistent REPL history across sessions (`~/.magmascript_history`)
- Multiline editing with proper continuation prompts
- Graceful fallback to readline-based REPL when prompt_toolkit is not installed

### Changed
- REPL now uses prompt_toolkit for interactive input when available
- Added `prompt_toolkit>=3.0` and `pygments>=2.0` to `[cli]` optional dependencies

## [1.4.0] - 2026-08-09

### Added
- Album ISRC/ISWC lookup via MusicBrainz API (`mb_search_releases`, `mb_get_release`, `mb_get_recording`)
- `args()` builtin for accessing script arguments from CLI
- `magmascript configure` subcommand — fetches API key from MCP server and writes to config
- `top-scores.mgs` — Arcade leaderboards (all games or single game mode)
- `album-isrcs.mgs` — Album ISRC/ISWC lookup example script
- `pi-health.mgs` — Pi system health check
- `pi-traffic-report.mgs` — Nginx traffic analysis
- `deploy-and-verify.mgs` — Deploy to Pi with service verification
- `artist-rights.mgs` — Artist rights catalog lookup
- `album-lookup.mgs` — Album research: MusicBrainz + ISRC/ISWC + rights
- `weekly-scores.mgs` — Weekly scores report in markdown
- `full-backup.mgs` — MusicBrainz backup pipeline
- `maintenance.mgs` — Weekly maintenance pipeline
- Domain bridge now registers archive, mb, lastfm, search domains
- 278 tests passing

### Fixed
- Domain bridge now instantiates client classes with config instead of storing classes
- `len()` now works with `ListWrapper` from domain calls
- ISRC parser handles both string and dict formats from MusicBrainz API
- `parse_return()` handles `return` inside blocks without a value

## [1.3.0] - 2026-08-09

### Added
- Dict literals: `{"name": "Jake", "age": 30}`
- List comprehensions: `[x * 2 for x in items]` with optional filter `[expr for x in list if cond]`
- String methods: `.split()`, `.join()`, `.upper()`, `.lower()`, `.contains()`, `.replace()`, `.length()`, `.startswith()`, `.endswith()`, `.strip()`
- Method chaining on strings: `"  Hello World  ".strip().lower()`
- `keys()` and `values()` now work on dict literals
- Domain bridge now properly instantiates client classes with config
- Registered missing domains: archive, mb, lastfm, search
- 20 new tests for domain bridge (278 total)

### Fixed
- Domain bridge now creates client instances instead of storing classes
- Domains that fail to initialize are gracefully skipped
- DomainProxy now has `close()` method for cleanup

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

## [1.1.0] - 2026-08-08

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

## [1.0.0] - 2026-08-08

### Added
- Initial release
- MCP server tools (search, entities, scoreboards, scores, games, archive, bots, discogs, jukebox, TV, themes)
- Raspberry Pi management via SSH
- GitHub operations (workflows, issues, file CRUD, atomic commits)
- MusicBrainz backup client
- Last.fm play count tracking
- Cache management with TTL support
- Domain-first CLI architecture
