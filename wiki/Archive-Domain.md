# Archive Domain

The Archive domain provides tools for managing archive HTML pages.

## Commands

### check-format

Validates formatting consistency across archive HTML files.

```bash
magmascript archive check-format             # console output
magmascript archive check-format --json      # JSON output
```

**Checks:**
- Sub-nav CSS classes match link text
- No orphan closing `</div>` tags

**Exit code:** 1 if warnings found, 0 if clean.

### bake-cache

Inlines MusicBrainz cache JSON into archive stub pages as `window.__MB_CACHE`.

```bash
magmascript archive bake-cache               # bake cache into pages
magmascript archive bake-cache --dry-run     # preview changes
```

**What it does:**
1. Scans `archive/by-{artist,place,contributor,label}/` for HTML stubs
2. Extracts UUID/slug from config variables (`ARTIST_CONFIG`, `PLACE_CONFIG`, etc.)
3. Loads matching cache file from `archive/_cache/{type}/{uuid}.json`
4. Injects `<script>window.__MB_CACHE = {...}</script>` before template script tags

**Options:**
- `--dry-run` — Show what would be written without modifying files

## Configuration

Set `MAGMACRUNCH_ROOT` environment variable or `project.root` in config:

```bash
export MAGMACRUNCH_ROOT="/path/to/magmacrunch.com"
magmascript archive check-format
```

## Python API

```python
from pathlib import Path
from magmascript.domains.archive import ArchiveClient

client = ArchiveClient(project_root=Path("/path/to/magmacrunch.com"))

# Check format
warnings = client.check_format()
for w in warnings:
    print(f"{w.file}:{w.line} - {w.msg}")

# Bake cache
result = client.bake_cache(dry_run=True)
print(f"Baked: {result.baked}, Skipped: {result.skipped}")
```
