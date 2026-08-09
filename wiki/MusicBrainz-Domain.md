# MusicBrainz Domain

The MusicBrainz domain provides a Python client for the MusicBrainz API with rate limiting, caching, and entity-specific backup functionality.

## Commands

### backup

Runs full MusicBrainz backup for all entities (artists, places, contributors, labels, works, collectives).

```bash
magmascript mb backup                        # full backup
magmascript mb backup --dry-run              # preview without writing
magmascript mb backup --skip-existing        # skip already-cached entities
magmascript mb backup --stale-only           # only refresh stale caches
```

**What it does:**
1. Fetches data from MusicBrainz API for each entity
2. Saves to `archive/_cache/{type}/{uuid}.json`
3. Creates timestamped snapshots before overwriting
4. Cleans old snapshots (keeps last 4)

**Options:**
- `--dry-run` — Show what would be done without writing files
- `--skip-existing` — Skip entities that already have cache files
- `--stale-only` — Only refresh caches older than 30 days

**Rate limiting:**
- 1100ms minimum between requests
- Retries up to 4 times on 429/503 errors
- Exponential backoff on failures

## Configuration

Set `MAGMACRUNCH_ROOT` environment variable or `project.root` in config:

```bash
export MAGMACRUNCH_ROOT="/path/to/magmacrunch.com"
magmascript mb backup --skip-existing
```

## Python API

```python
from pathlib import Path
from magmascript.domains.mb import MusicBrainzClient

client = MusicBrainzClient(project_root=Path("/path/to/magmacrunch.com"))

# Full backup
result = client.backup()
print(f"Completed: {result.completed}, Skipped: {result.skipped}")

# Dry run
result = client.backup(dry_run=True, skip_existing=True)

# Close client
client.close()
```

## Entity Definitions

The client includes all magmacrunch archive entities:

| Type | Count | Description |
|------|-------|-------------|
| Artists | 11 | DDT LLC, woah, SVFP, Jon McCoy, etc. |
| Places | 8 | Green St. Apt, Irvin House, Frogwood Manor, etc. |
| Contributors | 13 | Jake McCoy, Judah Unmuth-Yockey, Ben Nikitas, etc. |
| Labels | 4 | magmacrunch music, The Slop Collective, etc. |
| Works | 8 | pay2play, try, starting again, etc. |
| Collectives | 4 | THLD, Audio Sound Paper, Vinny Bobarino, etc. |

## Cache Structure

```
archive/_cache/
├── artists/{uuid}.json
├── places/{uuid}.json
├── contributors/{uuid}.json
├── labels/{uuid}.json
├── works/{uuid}.json
├── collectives/{slug}.json
└── snapshots/{date}/{type}/{uuid}.json
```
