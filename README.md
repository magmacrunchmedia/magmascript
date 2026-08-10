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
host = "192.168.1.16"
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
# Run a script
magmascript run scripts/examples/hello.mgs

# Run with arguments
magmascript run scripts/examples/top-scores.mgs tetris

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

### Built-in Functions

| Function | Description |
|----------|-------------|
| `print(...)` | Print to stdout |
| `len(x)` | Length of string, list, or dict |
| `type(x)` | Type name as string |
| `range(n)` | List of integers 0..n-1 |
| `str(x)`, `int(x)`, `float(x)` | Type conversions |
| `abs(x)`, `min(...)`, `max(...)`, `sum(...)` | Math utilities |
| `keys(d)`, `values(d)` | Dict operations |
| `args()` | Get script arguments from CLI |

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
- [Configuration](https://github.com/magmacrunchmedia/magmascript/wiki/Configuration)
- [MagmaScript Language](https://github.com/magmacrunchmedia/magmascript/wiki/MagmaScript-Language)
- [MCP Domain](https://github.com/magmacrunchmedia/magmascript/wiki/MCP-Domain)
- [Pi Domain](https://github.com/magmacrunchmedia/magmascript/wiki/Pi-Domain)
- [GitHub Domain](https://github.com/magmacrunchmedia/magmascript/wiki/GitHub-Domain)
- [Scores Domain](https://github.com/magmacrunchmedia/magmascript/wiki/Scores-Domain)
- [Rights Domain](https://github.com/magmacrunchmedia/magmascript/wiki/Rights-Domain)
- [Example Scripts](https://github.com/magmacrunchmedia/magmascript/wiki/Example-Scripts)
- [Architecture](https://github.com/magmacrunchmedia/magmascript/wiki/Architecture)

## License

MIT
