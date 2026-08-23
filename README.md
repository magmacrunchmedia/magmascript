# magmascript

Scripting toolkit with domain-first subcommands for managing magmacrunch.com infrastructure.

## Install

```bash
git clone https://github.com/magmacrunchmedia/magmascript.git
cd magmascript
python3 -m venv .venv
.venv/bin/pip install -e ".[all]"
```

## Configure

```bash
# Auto-configure from MCP server
magmascript configure

# Or manually set environment variables
export MAGMA_API_KEY="your-mcp-key"
export GITHUB_TOKEN=$(gh auth token)
export MAGMACRUNCH_ROOT="/path/to/magmacrunch.com"
```

Or use `~/.config/magmascript/config.toml`:

```toml
[mcp]
url = "https://magmacrunch.duckdns.org/mcp"
api_key = "your-key"

[pi]
host = "your-pi-host"
user = "jake"

[gh]
token = "ghp_..."
owner = "magmacrunchmedia"
repo = "magmacrunch.com"

[project]
root = "/path/to/magmacrunch.com"
```

## MagmaScript Language

Write `.mgs` scripts using a Python-inspired mini language with direct access to all domains.

### Quick Start

```bash
# Run a script (shorthand)
magmascript scripts/examples/hello.mgs

# Run with arguments
magmascript scripts/examples/top-scores.mgs tetris

# Or use the explicit run subcommand
magmascript run scripts/examples/hello.mgs

# Start interactive REPL
magmascript repl
```

### Syntax Overview

```magmascript
// Variables
name = "MagmaCrunch"
version = 2

// String interpolation
print(f"Hello, {name} v{version}!")

// Functions
double = fn(x) { x * 2 }
result = double(21)

// Arrow functions
triple = x -> x * 3

// Script arguments
args_list = args()
if len(args_list) > 0 {
    print(f"First arg: {args_list[0]}")
}

// Control flow
if x > 10 {
    print("big")
} else {
    print("small")
}

// Loops
for i in range(5) {
    print(i)
}

while x > 0 {
    x = x - 1
}

// Dict literals
scores = {"Pong": 12, "Tetris": 45}
print(scores["Tetris"])

// List comprehensions
numbers = [1, 2, 3, 4, 5]
evens = [x for x in numbers if x % 2 == 0]
doubled = [x * 2 for x in numbers]

// String methods
csv = "apple,banana,cherry"
fruits = csv.split(",")
upper = [f.upper() for f in fruits]
print("-".join(upper))

// Domain calls work directly
boards = mcp.scoreboards()
for board in boards {
    print(f"{board.game}: {board.entries} entries")
}
```

### Language Features

#### Import System

```magmascript
// Import a module (access as namespace)
intent "utils.mgs"
result = utils.greet("World")

// Import with alias
intent "utils.mgs" as u
result = u.greet("World")

// Import specific names
intent { greet, farewell } from "utils.mgs"
result = greet("World")
```

#### Error Handling

```magmascript
try {
    result = risky_operation()
} haunter (e) {
    print(f"Error: {e.message}")
}

// Throw custom errors
throw fire toad("something went wrong")
```

MagmaCrunch error vocabulary:
- `haunter` — syntax/parse errors
- `fire toad` — runtime errors
- `devastate` — undefined variable errors
- `contemplate` — type errors
- `spooked` — warnings (non-fatal, prints to stderr)

```magmascript
spooked("this is a warning")
```

#### File I/O

```magmascript
content = quarry("data.txt")           // read file
litho("output.txt", "hello world")    // write file
```

#### HTTP Requests

```magmascript
response = http.get("https://api.example.com/data")
print(response.status)
print(response.json)

http.post("https://api.example.com/data", body={"key": "value"})
```

#### Shell Commands

```magmascript
result = exec("ls -la")
print(result.stdout)
print(result.exit_code)
```

#### Classes

```magmascript
class Dog {
    fn init(name) {
        self.name = name
    }

    fn bark(self) {
        return self.name + " says woof!"
    }
}

rex = Dog("Rex")
print(rex.bark())  // "Rex says woof!"
```

#### Default Parameters

```magmascript
fn greet(name, greeting="hello") {
    return greeting + ", " + name + "!"
}

greet("Jake")           // "hello, Jake!"
greet("Jake", "hey")    // "hey, Jake!"
```

#### Multi-Assignment

```magmascript
a, b = 1, 2
x, y, z = 10, 20, 30
a, b = [1, 2]  // list unpacking
```

#### `in` / `not in` Operators

```magmascript
if "key" in {"name": "Jake"} { ... }
if 5 not in [1, 2, 3] { ... }
if "xyz" not in "hello" { ... }
```

#### List/String Slicing

```magmascript
[1, 2, 3, 4, 5][0:3]     // [1, 2, 3]
[1, 2, 3][::-1]           // [3, 2, 1]
[0, 1, 2, 3, 4][::2]     // [0, 2, 4]
"hello world"[0:5]        // "hello"
"abcdef"[::-1]            // "fedcba"
```

#### Regex

```magmascript
"123abc".match("\\d+")            // ["123"] (match at start)
"abc123def456".findall("\\d+")    // ["123", "456"]
```

### Built-in Functions

| Function | Description |
|----------|-------------|
| `print(...)` | Print to stdout |
| `echo(...)` | Print to stdout (alias for print) |
| `len(x)` | Length of string, list, or dict |
| `type(x)` | Type name as string |
| `range(n)`, `range(start, stop)`, `range(start, stop, step)` | Generate integer ranges |
| `str(x)`, `int(x)`, `float(x)` | Type conversions |
| `abs(x)`, `min(...)`, `max(...)`, `sum(...)` | Math utilities |
| `keys(d)`, `values(d)` | Dict operations |
| `args()` | Get script arguments from CLI |
| `quarry(path)` | Read file contents |
| `litho(path, content)` | Write content to file |
| `exec(command)` | Execute shell command, returns `{stdout, stderr, exit_code}` |

### String Methods

| Method | Description |
|--------|-------------|
| `s.split(sep)` | Split string by separator |
| `s.join(list)` | Join list with string separator |
| `s.upper()` | Convert to uppercase |
| `s.lower()` | Convert to lowercase |
| `s.contains(sub)` | Check if substring exists |
| `s.replace(old, new)` | Replace substring |
| `s.length()` | Get string length |
| `s.startswith(prefix)` | Check if starts with prefix |
| `s.endswith(suffix)` | Check if ends with suffix |
| `s.strip()` | Remove leading/trailing whitespace |
| `s.match(pattern)` | Match regex at start, return groups or none |
| `s.findall(pattern)` | Find all non-overlapping regex matches |

### Example Scripts

See `scripts/examples/` for working examples:

| Script | Description |
|--------|-------------|
| `hello.mgs` | Hello World and basic features |
| `fibonacci.mgs` | Recursive functions and loops |
| `top-scores.mgs` | Arcade leaderboards (all games or single game) |
| `album-isrcs.mgs` | Get ISRCs/ISWCs for every song on an album |
| `album-lookup.mgs` | Album research: MusicBrainz + ISRC/ISWC + rights |
| `artist-rights.mgs` | Full artist rights catalog |
| `pi-health.mgs` | Pi system health check |
| `pi-traffic-report.mgs` | Nginx traffic analysis |
| `deploy-and-verify.mgs` | Deploy to Pi with service verification |
| `full-backup.mgs` | MusicBrainz backup pipeline |
| `weekly-scores.mgs` | Weekly scores report in markdown |
| `maintenance.mgs` | Weekly maintenance pipeline |
| `real-domains.mgs` | Test real domain connections (MCP search, scoreboards, games) |
| `domain-example.mgs` | Domain object overview and usage patterns |
| `astheno-list.mgs` | A linked list built by hand in the arena |
| `astheno-packing.mgs` | The same struct fields, two orderings, two sizes |
| `astheno-faults.mgs` | Every memory fault, caught and named |

### The Asthenosphere — explicit memory

The layer beneath the lithosphere. A second tier where you manage memory
yourself: a real byte arena, pointers, structs with visible padding, and
integers that wrap like C's.

It is not faster than the dynamic tier — an `i32` add still costs a Python
dispatch. What it gives you instead is the thing C cannot: the interpreter sees
every memory operation, so it catches the use-after-free, names the line that
leaked, and hex-dumps a struct with its fields labelled. **C's behavior, but
narrated.**

```magmascript
floorplan Point {
    tag: u8
    x: i32
    y: i32
}

layout(Point)              // prints the field table, padding rows included

p = garrison(Point)        // claim ground
p.x = i32(10)
p.y = i32(-20)
bathysphere(p)             // annotated hex dump
scorch(p)                  // release it
```

Widths are `i8 i16 i32 i64  u8 u16 u32 u64  f32 f64`. There is no integer
promotion — `i32 + u8` is an error pointing you at `osmosis()` — and `/`
truncates toward zero on integer widths, as C does.

Mistakes are reported, not swallowed:

```
quicksand at demo.mgs:line 4, column 7
    |
  4 | x = p.peek(i32)
    |       ^
this ground was scorched at line 3 (garrisoned at line 1)
```

| Fault | Reported as |
|--------|-------------|
| touching scorched ground | `quicksand`, naming the line that scorched it |
| reading outside a block | `area does not exist`, with the block's extent |
| never scorching | `spooked: ancient weeds` at exit, naming each garrison line |
| arithmetic that does not fit | `spooked`, with the exact value and the wrap |

`floorplan` is the only new reserved word; everything else is a shadowable
builtin, so existing scripts are unaffected. Full reference on the
[Asthenosphere wiki page](https://github.com/magmacrunchmedia/magmascript/wiki/Asthenosphere).

### REPL

Start an interactive MagmaScript session:

```bash
magmascript repl
```

**Features:**
- Syntax highlighting via Pygments
- Tab completion for keywords, builtins, domain methods, and user-defined variables
- Persistent history across sessions (`~/.magmascript_history`)
- Multiline editing with proper continuation prompts
- Dot-commands:

| Command | Description |
|---------|-------------|
| `.help` | Show available commands |
| `.exit` | Exit the REPL |
| `.clear` | Clear the screen |
| `.ast` | Show AST for last expression |
| `.magma` | System status dashboard |
| `.crunch <target>` | Run batch pipeline |
| `.texas <target>` | Full/heavy operation |
| `.toast <target>` | Burn/clear caches |

## Domains

### MCP Domain — MusicBrainz, scores, Discogs, write operations
```bash
magmascript mcp scoreboards                  # game leaderboards
magmascript mcp scores tetris                # tetris scores
magmascript mcp search "radiohead"           # search MusicBrainz
magmascript mcp entities                     # all cached entities
magmascript mcp games                        # arcade games
magmascript mcp mb-search "album name"       # search MusicBrainz releases
magmascript mcp mb-release <mbid>            # get release details
magmascript mcp mb-recording <mbid>          # get recording details
```

### Pi Domain — Direct SSH to Raspberry Pi
```bash
magmascript pi status                        # all service statuses
magmascript pi logs arcade-chat              # service logs
magmascript pi restart arcade-chat           # restart service
magmascript pi info                          # uptime, memory, temp
magmascript pi deploy arcade/chat-server.py  # deploy files
magmascript pi backup musicbrainz            # backup + commit to GitHub
magmascript pi traffic                       # nginx traffic analysis
```

### MC1 Domain — Windows PC management (via SSH)
```magmascript
// In a .mgs script
info = mc1.info()
print(f"CPU: {info.cpu_usage}%, Memory: {info.memory}")

services = mc1.services()
for svc in services {
    print(f"{svc.name}: {svc.status}")
}

mc1.restart("OllamaSvc")
mc1.set_power_mode("always-on")
```

### GitHub Domain — Direct API access
```bash
magmascript gh workflows                     # all workflow statuses
magmascript gh trigger "Deploy to Pi"        # trigger workflow
magmascript gh issues                        # list issues
magmascript gh file path/to/file.txt         # read file
magmascript gh sync                          # diff + commit all data files
```

### Scores Domain — Game high scores
```bash
magmascript scores list                      # all game leaderboards
magmascript scores get tetris                # tetris scores
magmascript scores report                    # markdown report
magmascript scores report --discord          # Discord JSON payload
magmascript scores reset tetris              # reset one game (backup created)
```

### Archive Domain — Archive page operations
```bash
magmascript archive check-format             # validate HTML formatting
magmascript archive bake-cache               # inline MusicBrainz cache into pages
magmascript archive generate-stubs           # generate stub HTML for new entities
```

### MusicBrainz Domain — MusicBrainz API client
```bash
magmascript mb backup                        # full MusicBrainz backup
magmascript mb backup --dry-run              # preview backup
magmascript mb backup --stale-only           # only refresh stale caches
```

### Last.fm Domain — Last.fm API client
```bash
magmascript lastfm fetch                     # fetch play counts
magmascript lastfm fetch --skip-existing     # skip cached artists
```

### Search Domain — Site search index builder
```bash
magmascript search build-index               # build search-index.json
magmascript search preview 10                # preview first 10 entries
```

### Rights Domain — Music rights metadata (ISRC, ISWC, ASCAP)
```bash
magmascript rights search "Farewell"         # search by title, ISRC, ISWC, or ASCAP ID
magmascript rights catalog "C.P. Rutledge"   # full rights catalog for an artist
magmascript rights export                    # TSV export for ASCAP forms
```

### Media Domain — Multi-provider media search
```bash
magmascript media search "sunset"            # search all providers
magmascript media providers                  # list available providers
```

### Cache Domain — Cache management
```bash
magmascript cache stats                      # show cache statistics
magmascript cache clear                      # clear all cache
```

### Magma — System status dashboard
```bash
magmascript magma                            # version, domains, cache stats
```

### Crunch — Batch pipeline
```bash
magmascript crunch mb                        # MusicBrainz backup
magmascript crunch lastfm                    # Last.fm fetch
magmascript crunch search                    # Build search index
magmascript crunch archive                   # Archive pages
magmascript crunch scores                    # Scores update
magmascript crunch gh                        # GitHub sync
magmascript crunch all                       # Run all targets
```

### Texas — Full/heavy operation (same targets, no shortcuts)
```bash
magmascript texas mb                         # Full MusicBrainz backup
magmascript texas lastfm                     # Full Last.fm fetch
magmascript texas search                     # Full search index rebuild
magmascript texas archive                    # Full archive processing
magmascript texas scores                     # Full scores update
magmascript texas gh                         # Full GitHub sync
magmascript texas all                        # Full heavy run
```

### Toast — Burn/clear caches
```bash
magmascript toast cache                      # Clear general cache
magmascript toast mb-cache                   # Clear MusicBrainz cache
magmascript toast lastfm-cache               # Clear Last.fm cache
magmascript toast scores-cache               # Clear scores cache
magmascript toast gh-cache                   # Clear GitHub cache
magmascript toast search-index               # Remove search index
magmascript toast all                        # Clear everything
```

## Python Library

```python
from magmascript import MCPClient, PIClient, GHClient, RightsClient

# MCP
with MCPClient() as mcp:
    boards = mcp.scoreboards()
    releases = mcp.mb_search_releases("album name")

# Pi (direct SSH)
with PIClient() as pi:
    status = pi.services()
    info = pi.info()

# GitHub (direct API)
with GHClient() as gh:
    workflows = gh.workflows()

# Music rights metadata
with RightsClient() as rights:
    catalog = rights.catalog("C.P. Rutledge")
```

## Shell Helpers

```bash
source lib/magmascript.sh

mcp_scoreboards          # MCP commands
pi_status                # Pi commands
gh_workflows             # GitHub commands
```

## Documentation

Full documentation on the [Wiki](https://github.com/magmacrunchmedia/magmascript/wiki):
- [MagmaScript Language](https://github.com/magmacrunchmedia/magmascript/wiki/MagmaScript-Language)
- [Configuration](https://github.com/magmacrunchmedia/magmascript/wiki/Configuration)
- [MCP Domain](https://github.com/magmacrunchmedia/magmascript/wiki/MCP-Domain)
- [Pi Domain](https://github.com/magmacrunchmedia/magmascript/wiki/Pi-Domain)
- [MC1 Domain](https://github.com/magmacrunchmedia/magmascript/wiki/MC1-Domain)
- [GitHub Domain](https://github.com/magmacrunchmedia/magmascript/wiki/GitHub-Domain)
- [Scores Domain](https://github.com/magmacrunchmedia/magmascript/wiki/Scores-Domain)
- [Rights Domain](https://github.com/magmacrunchmedia/magmascript/wiki/Rights-Domain)
- [Archive Domain](https://github.com/magmacrunchmedia/magmascript/wiki/Archive-Domain)
- [Last.fm Domain](https://github.com/magmacrunchmedia/magmascript/wiki/Last.fm-Domain)
- [MusicBrainz Domain](https://github.com/magmacrunchmedia/magmascript/wiki/MusicBrainz-Domain)
- [Search Domain](https://github.com/magmacrunchmedia/magmascript/wiki/Search-Domain)
- [Media Domain](https://github.com/magmacrunchmedia/magmascript/wiki/Media-Domain)
- [Example Scripts](https://github.com/magmacrunchmedia/magmascript/wiki/Example-Scripts)
- [Asthenosphere](https://github.com/magmacrunchmedia/magmascript/wiki/Asthenosphere)
- [Architecture](https://github.com/magmacrunchmedia/magmascript/wiki/Architecture)

## License

MIT
