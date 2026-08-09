# Last.fm Domain

The Last.fm domain provides a Python client for the Last.fm API with rate limiting, MBID resolution, and play count fetching.

## Commands

### fetch

Fetches play counts and top tracks for all artists in `scripts/play-counts.json`.

```bash
magmascript lastfm fetch                     # fetch play counts
magmascript lastfm fetch --dry-run           # preview without writing
magmascript lastfm fetch --skip-existing     # skip already-cached artists
```

**What it does:**
1. Reads artist list from `scripts/play-counts.json`
2. Resolves MusicBrainz IDs via Last.fm search (if not cached)
3. Fetches artist info (listeners, playcount)
4. Fetches top tracks
5. Saves to `arcade/admin/stats/lastfm/{slug}.json`
6. Saves history to `arcade/admin/stats/lastfm/history/{date}/{slug}.json`
7. Prunes old history (keeps last 12 snapshots)

**Options:**
- `--dry-run` — Show what would be done without writing files
- `--skip-existing` — Skip artists that already have cache files

**Rate limiting:**
- 250ms minimum between requests
- Retries up to 4 times on 429 errors
- Exponential backoff on failures

## Configuration

Requires `LASTFM_API_KEY` environment variable:

```bash
export LASTFM_API_KEY="your-lastfm-api-key"
export MAGMACRUNCH_ROOT="/path/to/magmacrunch.com"
magmascript lastfm fetch --skip-existing
```

## Python API

```python
from pathlib import Path
from magmascript.domains.lastfm import LastFmClient

client = LastFmClient(
    project_root=Path("/path/to/magmacrunch.com"),
    api_key="your-lastfm-api-key",
)

# Fetch play counts
result = client.fetch(skip_existing=True)
print(f"Completed: {result.completed}, Resolved: {result.resolved}")

# Close client
client.close()
```

## Cache Structure

```
arcade/admin/stats/lastfm/
├── {slug}.json           # Current play count data
└── history/
    └── {date}/
        └── {slug}.json   # Historical snapshots
```

## Artist Config

Artists are defined in `scripts/play-counts.json`:

```json
{
  "artists": [
    {"name": "C.P. Rutledge", "mbid": "44c1e0bd-...", "resolvedName": "C.P. Rutledge"},
    {"name": "Jon McCoy", "mbid": "33c830f0-...", "resolvedName": "Jon McCoy"}
  ]
}
```

The `mbid` and `resolvedName` fields are auto-populated on first fetch.
