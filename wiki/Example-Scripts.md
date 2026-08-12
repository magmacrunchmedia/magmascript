# Example Scripts

Working example scripts in `scripts/examples/`:

| Script | Description |
|--------|-------------|
| `hello.mgs` | Hello World and basic features |
| `fibonacci.mgs` | Recursive functions and loops |
| `top-scores.mgs` | Arcade leaderboards (all games or single game) |
| `album-isrcs.mgs` | Get ISRCs/ISWCs for every song on an album |
| `album-lookup.mgs` | Album research: MusicBrainz + ISRC/ISWC + rights |
| `artist-rights.mgs` | Full artist rights catalog |
| `pi-health.mgs` | Pi system health check |
| `pi-traffic-report.mgs` | Nginx traffic analysis |
| `deploy-and-verify.mgs` | Deploy to Pi with service verification |
| `full-backup.mgs` | MusicBrainz backup pipeline |
| `weekly-scores.mgs` | Weekly scores report in markdown |
| `maintenance.mgs` | Weekly maintenance pipeline |
| `real-domains.mgs` | Test real domain connections (MCP search, scoreboards, games) |
| `domain-example.mgs` | Domain object overview and usage patterns |

## Running Examples

```bash
# Basic usage
magmascript run scripts/examples/hello.mgs

# With arguments
magmascript run scripts/examples/top-scores.mgs tetris

# From the project root
magmascript run scripts/examples/fibonacci.mgs
```

## Writing Your Own

See [MagmaScript Language](MagmaScript-Language) for the full language reference.
