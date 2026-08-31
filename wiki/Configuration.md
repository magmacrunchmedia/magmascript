# Configuration

magmascript loads configuration from environment variables and a config file.

## Quick Setup

```bash
# Auto-configure from MCP server (recommended)
magmascript configure

# Or manually
export MAGMA_API_KEY="your-mcp-key"
export GITHUB_TOKEN=$(gh auth token)
```

## Priority

1. Environment variables (highest)
2. Config file (`~/.config/magmascript/config.toml`)
3. Defaults (lowest)

## Configure Command

The `configure` command fetches the API key from the MCP server and writes it to your config file:

```bash
# Fetch from Pi (default)
magmascript configure

# Fetch from custom host
magmascript configure --host user@server

# Fetch from localhost (for Pi)
magmascript configure --host jake@localhost
```

This is the recommended way to set up magmascript on a new machine.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MAGMA_URL` | MCP server URL | `https://magmacrunch.duckdns.org/mcp` |
| `MAGMA_API_KEY` | MCP API key | — |
| `MAGMA_PI_HOST` | Pi hostname | `your-pi-host` |
| `MAGMA_PI_USER` | Pi SSH user | `jake` |
| `MAGMA_GITHUB_TOKEN` | GitHub token | — |
| `MAGMA_GITHUB_OWNER` | GitHub owner | `magmacrunch-media` |
| `MAGMA_GITHUB_REPO` | GitHub repo | `magmacrunch.com` |
| `MAGMA_PROJECT_ROOT` | Project root path | — |
| `DISCORD_WEBHOOK_URL` | Discord webhook | — |
| `LASTFM_API_KEY` | Last.fm API key | — |

## Config File

Location: `~/.config/magmascript/config.toml`

```toml
[mcp]
url = "https://magmacrunch.duckdns.org/mcp"
api_key = "your-key"

[pi]
host = "your-pi-host"
user = "jake"

[gh]
token = "ghp_..."
owner = "magmacrunch-media"
repo = "magmacrunch.com"

[project]
root = "/path/to/magmacrunch.com"

[discord]
webhook_url = "https://discord.com/api/webhooks/..."
```

## Project Root

Some commands need to access local filesystem files. Set the project root:

```bash
export MAGMACRUNCH_ROOT="/path/to/magmacrunch.com"
```

Or in config file:

```toml
[project]
root = "/path/to/magmacrunch.com"
```

**Commands that require project root:**
- `archive check-format`
- `archive bake-cache`
- `mb backup`
- `lastfm fetch`
- `search build-index`
- `search preview`

## Domain-Specific Config

### Last.fm

Requires `LASTFM_API_KEY`:

```bash
export LASTFM_API_KEY="your-key"
```

### Discord

For posting to Discord webhooks:

```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

## Examples

### Minimal config (Pi SSH only)

```bash
# No config needed - uses SSH key auth
magmascript pi status
```

### Full config

```toml
[mcp]
url = "https://magmacrunch.duckdns.org/mcp"
api_key = "abc123"

[gh]
token = "ghp_..."
owner = "magmacrunch-media"
repo = "magmacrunch.com"

[project]
root = "/Users/jake/Documents/website"

[discord]
webhook_url = "https://discord.com/api/webhooks/..."
```

```bash
export LASTFM_API_KEY="your-key"
magmascript scores report --post-discussion --post-discord
```
