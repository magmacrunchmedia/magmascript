# Search Domain

The Search domain provides a site search index builder for magmacrunch.com.

## Commands

### build-index

Builds the search index used by Fuse.js for client-side search.

```bash
magmascript search build-index               # build search-index.json
```

**What it does:**
1. Scans all site HTML files
2. Extracts title, category, URL, description, and body text
3. Enriches archive entries with MusicBrainz cache data
4. Deduplicates by URL
5. Writes to `search-index.json`

**Sections parsed:**
- Main/hub pages
- Distributed music releases
- Jukebox songs
- Physical media (floppy disk sub-pages)
- Archive sections (artists, places, labels, contributors)
- Arcade games
- Press articles
- Tools

### preview

Previews search index entries without writing to file.

```bash
magmascript search preview 10                # preview first 10 entries
magmascript search preview                   # preview first 10 (default)
```

## Configuration

Set `MAGMACRUNCH_ROOT` environment variable or `project.root` in config:

```bash
export MAGMACRUNCH_ROOT="/path/to/magmacrunch.com"
magmascript search build-index
```

## Python API

```python
from pathlib import Path
from magmascript.domains.search import SearchClient

client = SearchClient(project_root=Path("/path/to/magmacrunch.com"))

# Build index
result = client.build()
print(f"Built: {result.deduplicated} entries ({result.total_entries} total)")

# Preview entries
entries = client.preview(limit=10)
for e in entries:
    print(f"[{e.c}] {e.t} - {e.u}")
```

## Index Format

The search index is a JSON array of objects:

```json
[
  {
    "t": "Page Title",
    "c": "category",
    "u": "/path/to/page.html",
    "d": "Description text",
    "b": "Body text for full-text search"
  }
]
```

**Categories:**
- `page` — Main/hub pages
- `music` — Music releases and songs
- `song` — Jukebox songs
- `artist` — Artist archive pages
- `place` — Place archive pages
- `label` — Label archive pages
- `contributor` — Contributor archive pages
- `arcade` — Arcade games
- `press` — Press articles
- `tool` — Web tools

## MusicBrainz Enrichment

Archive entries are enriched with recording/release/work titles from the MusicBrainz cache, making them searchable by track name.
