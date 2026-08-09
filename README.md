# magmascript

Scripting toolkit with domain-first subcommands. Starts with MCP as the first domain, built to grow into a mini-language (`.ms` scripts).

## Install

```bash
pip install -e ".[all]"
```

Or just use from source:

```bash
python -m magmascript.cli mcp search "aphex twin"
```

## Config

Set your API key via environment variable or config file:

```bash
# Environment
export MAGMA_API_KEY="your-key-here"

# Or config file: ~/.config/magmascript/config.toml
[mcp]
url = "https://magmacrunch.duckdns.org/mcp"
api_key = "your-key-here"
```

## CLI Usage

```bash
# MusicBrainz search
magmascript mcp search "aphex twin"
magmascript mcp entities artists

# High scores
magmascript mcp scoreboards
magmascript mcp scores tetris

# Pi services
magmascript mcp pi-status
magmascript mcp pi-logs arcade-chat
magmascript mcp pi-info

# GitHub bots
magmascript mcp bots
magmascript mcp trigger "Deploy to Pi"

# Quick shell wrapper
mcp search "radiohead"
mcp scores solitaire
```

## Python Library

```python
from magmascript import MCPClient

client = MCPClient()
results = client.search("aphex twin")
boards = client.scoreboards()
client.close()

# Or as context manager
with MCPClient() as mcp:
    results = mcp.search("radiohead")
    for r in results:
        print(f"{r.name} ({r.type})")
```

## Shell Helpers

```bash
source lib/magmascript.sh

mcp_search "boards of canada"
mcp_scoreboards
mcp_pi_status
```

## JavaScript (Web/Node)

```javascript
import { MCPClient } from './lib/magmascript.js'

const client = new MCPClient(url, apiKey)
const results = await client.search('aphex twin')
const boards = await client.scoreboards()
```

## Architecture

```
magmascript/
├── core/           # Framework: registry, config, rpc, output
├── domains/        # One module per domain (mcp/, future: pi/, gh/)
├── cli/            # Shell entry points
├── lib/            # Multi-language wrappers
└── tests/
```

### Module Registry

New domains register themselves the same way. The CLI and future DSL discover them through the registry:

```python
from magmascript.core.registry import register_domain

class PiClient:
    def status(self): ...
    def logs(self, service): ...

register_domain("pi", PiClient)
```

## Available MCP Tools

| Tool | Client Method | Description |
|---|---|---|
| `search_cache` | `search(query)` | Search cached MusicBrainz entities |
| `get_entity` | `get_entity(type, key)` | Get full entity data |
| `list_cached_entities` | `list_entities(type)` | List all cached entities |
| `list_scoreboards` | `scoreboards()` | List all leaderboards |
| `get_scores` | `scores(game, limit)` | Get game leaderboard |
| `list_archive_pages` | `archive_pages()` | List archive pages |
| `list_arcade_games` | `arcade_games()` | List arcade games |
| `check_pi_services` | `pi_status()` | Check Pi services |
| `get_service_logs` | `pi_logs(service, lines)` | Get service logs |
| `restart_pi_service` | `pi_restart(service)` | Restart service |
| `get_pi_system_info` | `pi_info()` | Get Pi system info |
| `deploy_to_pi` | `deploy(path, service)` | Deploy to Pi |
| `list_bots` | `bots()` | List GitHub workflows |
| `get_bot_status` | `bot_status(name)` | Get workflow details |
| `trigger_bot` | `trigger_bot(name)` | Trigger workflow |
| `get_bot_runs` | `bot_runs(name, limit)` | Get workflow runs |
| `search_discogs` | `discogs_search(query, type)` | Search Discogs |
| `get_discogs_release` | `discogs_release(id)` | Get Discogs release |
| `get_discogs_artist` | `discogs_artist(id)` | Get Discogs artist |
| `get_discogs_label` | `discogs_label(id)` | Get Discogs label |
| `get_jukebox_songs` | `jukebox_songs()` | List jukebox songs |
| `get_tv_channels` | `tv_channels()` | List TV channels |
| `get_themes` | `themes()` | List themes |
| `get_play_counts` | `play_counts()` | List Last.fm play counts |

## License

MIT
