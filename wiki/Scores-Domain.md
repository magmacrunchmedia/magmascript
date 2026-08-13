# Scores Domain

The Scores domain manages arcade game high scores.

## Commands

```bash
magmascript scores list                      # all game leaderboards
magmascript scores get <game>                # scores for a specific game
magmascript scores report                    # markdown report
magmascript scores report --discord          # Discord JSON payload
magmascript scores reset <game>              # reset one game (backup created)
magmascript scores reset-all                 # reset all games (backup created)
```

## Configuration

Requires SSH access to the Pi (uses Pi domain internally).

## Python API

```python
from magmascript import ScoresClient

with ScoresClient() as scores:
    boards = scores.list()
    report = scores.report()
```
