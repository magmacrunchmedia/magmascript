# Rights Domain

The Rights domain manages music rights metadata (ISRC, ISWC, ASCAP).

## Commands

```bash
magmascript rights search "Farewell"         # search by title, ISRC, ISWC, or ASCAP ID
magmascript rights isrc <code>               # lookup by ISRC
magmascript rights iswc <code>               # lookup by ISWC
magmascript rights ascap <id>                # lookup by ASCAP ID
magmascript rights catalog "C.P. Rutledge"   # full rights catalog for an artist
magmascript rights recording <id>            # rights for a specific recording
magmascript rights work <id>                 # rights for a specific work
magmascript rights export                    # TSV export for ASCAP forms
```

## Configuration

Uses the MCP domain for rights lookups. Requires `MAGMA_API_KEY`.

## Python API

```python
from magmascript import RightsClient

with RightsClient() as rights:
    catalog = rights.catalog("C.P. Rutledge")
```
