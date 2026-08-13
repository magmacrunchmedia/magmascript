# Media Domain

The Media domain provides multi-provider media search across Openverse, Pexels, Pixabay, Met Museum, Smithsonian, and Archive.

## Commands

### search

Search for media across all providers.

```bash
magmascript media search "sunset"                      # search all providers
magmascript media search "sunset" --source openverse   # search specific provider
magmascript media search "sunset" --type image         # filter by type
magmascript media search "sunset" --orientation landscape  # filter by orientation
magmascript media search "sunset" --page 2 --per-page 12   # pagination
```

**Options:**
- `--source <provider>` — Filter to a specific provider (openverse, pexels, pixabay, met, smithsonian, archive)
- `--type <type>` — Filter by media type (image, video, audio)
- `--orientation <orientation>` — Filter by orientation (landscape, portrait, square)
- `--page <n>` — Page number (default: 1)
- `--per-page <n>` — Results per page (default: 24)

### providers

List available media providers and their capabilities.

```bash
magmascript media providers
```

### image

Get details for a specific media item.

```bash
magmascript media image <id> --source <provider>
```

## Python API

```python
from magmascript import MediaClient

with MediaClient() as media:
    # Search
    result = media.search("sunset", source="openverse", media_type="image")
    for item in result.results:
        print(item.title, item.url)

    # List providers
    providers = media.list_providers()
    for p in providers:
        print(f"{p.key}: {p.label} [{', '.join(p.types)}]")

    # Get specific item
    item = media.get("12345", "openverse")
```
