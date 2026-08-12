# MCP Domain

The MCP domain provides access to the MagmaCrunch MCP server for MusicBrainz, scores, Discogs, and write operations.

## Commands

```bash
# Search and entities
magmascript mcp search "radiohead"           # search cached MusicBrainz entities
magmascript mcp entities                     # all cached entities
magmascript mcp entity <type> <key>          # get full entity data

# Scores
magmascript mcp scoreboards                  # game leaderboards
magmascript mcp scores <game> [limit]        # get leaderboard for a game
magmascript mcp games                        # all arcade games

# Archive
magmascript mcp archive                      # all archive pages

# MusicBrainz
magmascript mcp mb-search "album name"       # search MusicBrainz releases
magmascript mcp mb-release <mbid>            # get release details
magmascript mcp mb-recording <mbid>          # get recording details

# GitHub Actions
magmascript mcp bots                         # list workflows
magmascript mcp bot-status <name>            # workflow details
magmascript mcp trigger <name>               # trigger a workflow
magmascript mcp bot-runs <name> [limit]      # workflow run history

# Discogs
magmascript mcp discogs <query> [type]       # search Discogs

# Jukebox
magmascript mcp jukebox                      # list jukebox songs
magmascript mcp jukebox save <file>          # save songs from JSON
magmascript mcp jukebox save <file> --deploy # save + commit to GitHub

# TV
magmascript mcp tv                           # list TV channels
magmascript mcp tv save <file>               # save channels from JSON
magmascript mcp tv save <file> --deploy      # save + commit to GitHub

# Themes
magmascript mcp themes                       # list theme catalog
magmascript mcp themes save <file>           # save themes from JSON
magmascript mcp themes save <file> --deploy  # save + commit to GitHub

# Play counts
magmascript mcp plays                        # list Last.fm play counts
magmascript mcp artist-plays                 # play counts by artist
```

## Configuration

Requires `MAGMA_API_KEY` environment variable or `[mcp]` section in config.toml:

```toml
[mcp]
url = "https://magmacrunch.duckdns.org/mcp"
api_key = "your-key"
```

## Python API

```python
from magmascript import MCPClient

with MCPClient() as mcp:
    boards = mcp.scoreboards()
    releases = mcp.mb_search_releases("album name")
```
