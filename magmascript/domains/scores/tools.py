"""Typed result dataclasses for the Scores domain."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScoreEntry:
    """A single high score entry."""

    rank: int
    initials: str
    score: int
    level: int | None = None
    difficulty: str | None = None
    time: str | None = None
    moves: int | None = None
    won: bool | None = None
    value_reached: int | None = None
    timestamp: int | None = None
    date: str | None = None
    total_score: int | None = None
    rounds: int | None = None
    escaped: bool | None = None


@dataclass
class Scoreboard:
    """Game leaderboard summary."""

    game: str
    game_id: str
    entries: int
    top: ScoreEntry | None = None


@dataclass
class PlayerStats:
    """Aggregate stats for a player across all games."""

    name: str
    total_entries: int
    games_played: int


@dataclass
class ScoresReport:
    """Full report across all games."""

    generated_at: str
    total_games: int
    total_scores: int
    scoreboards: list[Scoreboard]
    player_stats: list[PlayerStats] = field(default_factory=list)
