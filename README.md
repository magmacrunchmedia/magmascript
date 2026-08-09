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
```

## Usage

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
magmascript scores reset tetris              # reset one game (backup created)
magmascript scores reset-all                 # reset all games
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

## Python Library

```python
from magmascript import MCPClient, PIClient, GHClient, RightsClient

# MCP
with MCPClient() as mcp:
    boards = mcp.scoreboards()

# Pi (direct SSH)
with PIClient() as pi:
    status = pi.services()

# GitHub (direct API)
with GHClient() as gh:
    workflows = gh.workflows()

# Music rights metadata
with RightsClient() as rights:
    matches = rights.search("Farewell")
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
- [MCP Domain](https://github.com/magmacrunchmedia/magmascript/wiki/MCP-Domain)
- [Pi Domain](https://github.com/magmacrunchmedia/magmascript/wiki/Pi-Domain)
- [GitHub Domain](https://github.com/magmacrunchmedia/magmascript/wiki/GitHub-Domain)
- [Rights Domain](https://github.com/magmacrunchmedia/magmascript/wiki/Rights-Domain)
- [Architecture](https://github.com/magmacrunchmedia/magmascript/wiki/Architecture)
- [Shell Helpers](https://github.com/magmacrunchmedia/magmascript/wiki/Shell-Helpers)

## License

MIT
