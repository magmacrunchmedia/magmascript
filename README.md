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
export MAGMA_API_KEY="your-mcp-key"
export GITHUB_TOKEN=$(gh auth token)
export MAGMACRUNCH_ROOT="/path/to/magmacrunch.com"
# pi domain works with no config (SSH key auth)
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
- `hello.mgs` — Hello World and basic features
- `fibonacci.mgs` — Recursive functions and loops
- `domain-example.mgs` — Using domain objects
- `top-scores.mgs` — Working with scoreboards

## Domains

### MCP Domain — MusicBrainz, scores, Discogs, write operations
```bash
magmascript mcp scoreboards                  # game leaderboards
magmascript mcp scores tetris                # tetris scores
magmascript mcp search "radiohead"           # search MusicBrainz
magmascript mcp entities                     # all cached entities
magmascript mcp games                        # arcade games
magmascript mcp jukebox save songs.json --deploy  # save jukebox + commit
magmascript mcp tv save channels.json --deploy    # save TV + commit
magmascript mcp themes save themes.json --deploy  # save themes + commit
```

### Pi Domain — Direct SSH to Raspberry Pi
```bash
magmascript pi status                        # all service statuses
magmascript pi logs arcade-chat              # service logs
magmascript pi restart arcade-chat           # restart service
magmascript pi info                          # uptime, memory, temp
magmascript pi deploy arcade/chat-server.py  # deploy files
magmascript pi backup musicbrainz            # backup + commit to GitHub
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
magmascript scores report --post-discussion  # post to GitHub Discussion
magmascript scores report --post-discord     # post to Discord
magmascript scores reset tetris              # reset one game (backup created)
magmascript scores reset-all                 # reset all games
```

### Archive Domain — Archive page operations
```bash
magmascript archive check-format             # validate HTML formatting
magmascript archive bake-cache               # inline MusicBrainz cache into pages
magmascript archive bake-cache --dry-run     # preview changes
```

### MusicBrainz Domain — MusicBrainz API client
```bash
magmascript mb backup                        # full MusicBrainz backup
magmascript mb backup --dry-run              # preview backup
magmascript mb backup --skip-existing        # skip cached entities
magmascript mb backup --stale-only           # only refresh stale caches
```

### Last.fm Domain — Last.fm API client
```bash
magmascript lastfm fetch                     # fetch play counts
magmascript lastfm fetch --dry-run           # preview fetch
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
magmascript rights isrc US-S1Z-24-00012      # look up recording by ISRC
magmascript rights iswc T-337.058.315-2      # look up work by ISWC
magmascript rights ascap 933623780           # look up work by ASCAP ID
magmascript rights catalog "C.P. Rutledge"   # full rights catalog for an artist
magmascript rights export                    # TSV export for ASCAP forms
```

### Media Domain — Multi-provider media search
```bash
magmascript media search "sunset"            # search all providers
magmascript media search "sunset" --source openverse  # search specific provider
magmascript media providers                  # list available providers
```

### Cache Domain — Cache management
```bash
magmascript cache stats                      # show cache statistics
magmascript cache clear                      # clear all cache
magmascript cache clear --domain scores      # clear specific domain
```

## Python Library

```python
from magmascript import MCPClient, PIClient, GHClient, ScoresClient, RightsClient
from magmascript.domains.archive import ArchiveClient
from magmascript.domains.mb import MusicBrainzClient
from magmascript.domains.lastfm import LastFmClient
from magmascript.domains.search import SearchClient

# MCP
with MCPClient() as mcp:
    boards = mcp.scoreboards()

# Pi (direct SSH)
with PIClient() as pi:
    status = pi.services()

# GitHub (direct API)
with GHClient() as gh:
    workflows = gh.workflows()

# Scores (direct SSH)
with ScoresClient() as scores:
    report = scores.report()
    discord_payload = scores.report_discord()

# Music rights metadata
with RightsClient() as rights:
    matches = rights.search("Farewell")
    catalog = rights.catalog("C.P. Rutledge")

# Archive (requires project root)
with ArchiveClient(project_root="/path/to/magmacrunch.com") as archive:
    warnings = archive.check_format()
    result = archive.bake_cache(dry_run=True)

# MusicBrainz (requires project root)
with MusicBrainzClient(project_root="/path/to/magmacrunch.com") as mb:
    result = mb.backup(skip_existing=True)

# Last.fm (requires API key and project root)
with LastFmClient(project_root="/path/to/magmacrunch.com") as lastfm:
    result = lastfm.fetch(skip_existing=True)

# Search (requires project root)
with SearchClient(project_root="/path/to/magmacrunch.com") as search:
    result = search.build()
    entries = search.preview(limit=10)
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
- [MCP Domain](https://github.com/magmacrunchmedia/magmascript/wiki/MCP-Domain)
- [Pi Domain](https://github.com/magmacrunchmedia/magmascript/wiki/Pi-Domain)
- [GitHub Domain](https://github.com/magmacrunchmedia/magmascript/wiki/GitHub-Domain)
- [Scores Domain](https://github.com/magmacrunchmedia/magmascript/wiki/Scores-Domain)
- [Archive Domain](https://github.com/magmacrunchmedia/magmascript/wiki/Archive-Domain)
- [MusicBrainz Domain](https://github.com/magmacrunchmedia/magmascript/wiki/MusicBrainz-Domain)
- [Last.fm Domain](https://github.com/magmacrunchmedia/magmascript/wiki/Last.fm-Domain)
- [Search Domain](https://github.com/magmacrunchmedia/magmascript/wiki/Search-Domain)
- [Rights Domain](https://github.com/magmacrunchmedia/magmascript/wiki/Rights-Domain)
- [Architecture](https://github.com/magmacrunchmedia/magmascript/wiki/Architecture)
- [Shell Helpers](https://github.com/magmacrunchmedia/magmascript/wiki/Shell-Helpers)

## License

MIT
