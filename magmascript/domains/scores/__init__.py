"""Scores domain — exposes ScoresClient and registers with the domain registry."""

from magmascript.domains.scores.client import ScoresClient
from magmascript.domains.scores.tools import (
    PlayerStats,
    ScoreEntry,
    Scoreboard,
    ScoresReport,
)
from magmascript.core.registry import register_domain

# Register this domain
register_domain("scores", ScoresClient)

__all__ = [
    "ScoresClient",
    "PlayerStats",
    "ScoreEntry",
    "Scoreboard",
    "ScoresReport",
]
