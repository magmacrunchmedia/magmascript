# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.2.0] - 2026-08-24

Host objects handed to a script were half-usable: you could call their methods
and read their fields, but not read their properties or change anything. This
release closes that gap and lets packages outside this repo publish domains of
their own — the first is [texastoast](https://github.com/magmacrunchmedia/texastoast),
which exposes a game engine as the `toast` domain.

### Added
- **Domains can be published by other packages.** A package declares one in its
  own metadata and it appears in scripts and the REPL:

  ```toml
  [project.entry-points."magmascript.domains"]
  texastoast = "texastoast.mgs:TexastoastDomain"
  ```

  Built-in domains win a name clash, and an entry point that fails to import is
  skipped rather than taking the interpreter down with it. This is what lets a
  domain live in the project it belongs to instead of in this repo.
- `DomainProxy` accepts a `factory=` for lazy construction, and
  `discover_domains()` performs the entry-point scan.

### Fixed
- **Scripts can now set attributes on host objects.** `player.speed = 200` on
  an object from a domain raised `Cannot set property on Entity`, even though
  `player.speed` read back fine — a script could inspect an object and never
  change it. Attributes that exist and are not private are now settable, and
  a fixed-width value is unwrapped to a plain number on the way in so it does
  not poison the host's arithmetic. Writing an unknown or private attribute is
  still an error, and a read-only property reports the line that tried.
- **Properties on wrapped dataclasses are readable.** `DataclassWrapper` only
  walked `dataclasses.fields()`, so anything derived — `InputState.dx`,
  `ControllerState.up` — raised `AttributeError`. It was also inconsistent:
  plain classes pass through unwrapped, so *their* properties always worked.
  Methods on dataclasses are reachable for the same reason.

### Changed
- **Domain clients are built on first use, not at startup.** Every domain was
  constructed for every script and every REPL session, paying for domains
  nobody touched and ruling out any domain whose construction does something —
  opening a window, holding a socket. `DomainProxy.close()` no longer builds a
  client just to tear it down.

  One visible consequence: a domain whose constructor raises used to be dropped
  silently, so a script using it failed with `Undefined variable`. The real
  error now surfaces at the call that needed the domain.

## [3.1.1] - 2026-08-23

### Changed
- Neutralized the private infrastructure defaults that shipped in the public
  package. The SSH host/user defaults for the `pi`, `mc1`, and `mac` domains, and
  the `gh` owner/repo, are now empty rather than baking in magmacrunch's own
  hosts, Tailscale IPs, and usernames. A fresh `pip install` no longer probes a
  stranger's machines, and personal network topology is no longer published on
  PyPI. The magmacrunch.com values live on as examples in the README and wiki;
  set your own via `~/.config/magmascript/config.toml` or `MAGMA_*` env vars.
  The MCP server URL stays a default — it is a public endpoint.
- A domain call with no host configured now raises a clear "no SSH host
  configured" error pointing at the config, instead of a confusing SSH failure.
- `magmascript configure` requires an explicit `--host user@host` rather than
  defaulting to a personal machine.

## [3.1.0] - 2026-08-23

### Added
- **Mac domain** — manage a Mac over SSH, mirroring the pi and mc1 domains:
  `mac.info()`, `mac.processes()`, `mac.git_status()`, `mac.git_pull()`, and
  `mac.run()`, from `.mgs` scripts and the CLI (`magmascript mac ...`). Reuses
  `CommandRunner`; configured via `[mac]` / `MAGMA_MAC_HOST` / `MAGMA_MAC_USER`.
- **mc1 CLI** — the mc1 domain finally has a `cli.py` branch. `magmascript mc1
  status | info | processes | restart | power | set-power-mode | wake | reboot`
  all work; before this they exited 1 with "Unknown domain: 'mc1'".
- Tests for the mc1 domain (parsers, uptime formatting, registration) — it had
  none. 24 tests.

### Fixed
- `mc1 info` returned a blank `cpu_load` and `disk_free` on every call. The
  PowerShell emits `CPU:` and `DISK:` but the parser only accepted the field
  names `cpu_load` / `disk_free`, so both were silently dropped. The parser now
  maps the emitted keys to the fields.

## [3.0.1] - 2026-08-23

A documentation release. Nothing under `magmascript/` changed, so the wheel is
functionally identical to 3.0.0 — this exists to correct what the project page
and wiki tell people.

### Fixed
- The 3.0.0 project page on PyPI advertised four `magmascript mc1 ...` commands
  that exit 1 with `Unknown domain: 'mc1'`. `cli.py` has no `mc1` branch; the
  working interface is the `.mgs` script one (`mc1.info()`). The README was
  corrected after 3.0.0 was tagged, so only a new release could republish it.
- `info.cpu_usage` does not exist. The field is `cpu_load`, it is a `str` not an
  `int`, and it already carries the percent sign — the documented trailing `%`
  rendered `4%%`. Wrong in `README.md` and twice in `wiki/MC1-Domain.md`.
- MC1 environment variables are `MAGMA_MC1_HOST` / `MAGMA_MC1_USER`. The wiki
  said `MAGMASCRIPT_MC1_*`, which matches no prefix the code reads, so setting
  them failed silently.
- The config file is `~/.config/magmascript/config.toml`, not `.magmascript.toml`.
- `cpu_cores` is a `str`, not an `int`; `MC1ServiceStatus` was missing its
  `ok: bool` field.

### Added
- `scripts/embed-playground.py` generates the playground's embedded copy of
  `magmascript/lang/` instead of it being maintained by hand, where it had
  fallen a major version behind — `playground/app.js` shipped a pre-3.0 snapshot
  with no Asthenosphere, so the playground silently ran v2.x semantics. Sources
  are emitted as JSON strings rather than JS template literals, whose escaping
  had already needed one fix.
- `playground/examples/asthenosphere.mgs`.

## [3.0.0] - 2026-08-23

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
- Values now print with MagmaScript's spelling rather than Python's. `print(none)`
  said `None` while `str(none)` said `none`; booleans printed as `True`/`False`.
  All display — `print`, `echo`, f-strings, `str()`, `spooked` — goes through one
  function, and containers render recursively (`[1, none, true]`). Strings print
  bare at the top level and quoted inside a container.
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

- The test suite now passes on Windows. Nine import tests and four `quarry`/`litho`
  tests embedded a native path into `.mgs` source, where a backslash before `t` is
  a tab escape; they now embed POSIX-form paths, which every platform accepts.

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

[3.0.0]: https://github.com/magmacrunchmedia/magmascript/compare/v2.3.0...v3.0.0
[2.2.0]: https://github.com/magmacrunchmedia/magmascript/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/magmacrunchmedia/magmascript/compare/v2.0.1...v2.1.0
[2.0.1]: https://github.com/magmacrunchmedia/magmascript/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/magmacrunchmedia/magmascript/compare/v1.6.0...v2.0.0
[1.6.0]: https://github.com/magmacrunchmedia/magmascript/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/magmacrunchmedia/magmascript/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/magmacrunchmedia/magmascript/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/magmacrunchmedia/magmascript/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/magmacrunchmedia/magmascript/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/magmacrunchmedia/magmascript/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/magmacrunchmedia/magmascript/releases/tag/v1.0.0
