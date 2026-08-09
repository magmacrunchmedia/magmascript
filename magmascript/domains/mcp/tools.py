"""Typed result dataclasses for all 23 MCP tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# MusicBrainz Cache
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    """A cached MusicBrainz entity (from search_cache or list_cached_entities)."""

    name: str
    uuid: str
    type: str  # artists, places, contributors, labels, works, collectives
    file: str
    size_kb: float | None = None


@dataclass
class Entity:
    """Full MusicBrainz entity data (from get_entity)."""

    name: str
    uuid: str
    type: str
    data: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# High Scores
# ---------------------------------------------------------------------------


@dataclass
class ScoreEntry:
    """A single high score entry."""

    initials: str
    score: int
    level: int | None = None
    difficulty: int | None = None
    time: str | None = None


@dataclass
class Scoreboard:
    """Game leaderboard summary (from list_scoreboards)."""

    game: str
    game_id: str
    entries: int
    top: ScoreEntry | None = None


# ---------------------------------------------------------------------------
# Project Structure
# ---------------------------------------------------------------------------


@dataclass
class ArcadeGame:
    """An arcade game entry (from list_arcade_games)."""

    name: str
    path: str
    has_server: bool
    port: int | None = None


@dataclass
class ArchivePage:
    """An archive page (from list_archive_pages)."""

    name: str
    path: str
    category: str  # artists, places, contributors, labels


# ---------------------------------------------------------------------------
# Pi Services (SSH)
# ---------------------------------------------------------------------------


@dataclass
class PiServiceStatus:
    """Status of a Pi service (from check_pi_services)."""

    name: str
    status: str  # active, inactive, etc.
    ok: bool


@dataclass
class PiSystemInfo:
    """Raspberry Pi system info (from get_pi_system_info)."""

    uptime: str
    memory: str
    cpu_temp: str
    load: str
    disk: str


# ---------------------------------------------------------------------------
# GitHub Bots
# ---------------------------------------------------------------------------


@dataclass
class BotStatus:
    """GitHub Actions workflow status (from list_bots)."""

    name: str
    file: str
    status: str
    last_run: str
    event: str


# ---------------------------------------------------------------------------
# Discogs
# ---------------------------------------------------------------------------


@dataclass
class DiscogsResult:
    """A Discogs search result (from search_discogs)."""

    title: str
    type: str  # release, master, artist, label
    id: str
    year: str | None = None


# ---------------------------------------------------------------------------
# Last.fm Play Counts
# ---------------------------------------------------------------------------


@dataclass
class PlayCount:
    """Artist play count data (from get_play_counts)."""

    name: str
    listeners: int
    playcount: int
    top_track: str | None = None


# ---------------------------------------------------------------------------
# Parsers — convert raw JSON/text into typed objects
# ---------------------------------------------------------------------------


def parse_search_results(text: str) -> list[SearchResult]:
    """Parse the text output of search_cache or list_cached_entities into SearchResults."""
    results = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("- ["):
            continue
        # Format: - [type] name (uuid) (N KB)
        try:
            bracket_end = line.index("]")
            entity_type = line[3:bracket_end]
            rest = line[bracket_end + 2 :]

            # Extract UUID (first paren group) and optional size (second paren group)
            uuid = ""
            name = rest
            size_kb = None
            if "(" in rest:
                uuid_start = rest.index("(")
                uuid_end = rest.index(")")
                uuid = rest[uuid_start + 1 : uuid_end]
                name = rest[:uuid_start].strip()
                # Check for size in remaining text
                remaining = rest[uuid_end + 1 :]
                if "KB" in remaining and "(" in remaining:
                    size_part = remaining.split("(")[1].replace(")", "").replace("KB", "").strip()
                    try:
                        size_kb = float(size_part)
                    except ValueError:
                        pass

            results.append(SearchResult(name=name, uuid=uuid, type=entity_type, file="", size_kb=size_kb))
        except (ValueError, IndexError):
            continue
    return results


def parse_scoreboard_list(text: str) -> list[Scoreboard]:
    """Parse the text output of list_scoreboards into Scoreboards."""
    results = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        # Format: - Game (N entries) — Top: XXX with 12345
        try:
            # Find " (" separator between game name and entry count
            paren_start = line.index(" (")
            game = line[2:paren_start]
            # Extract number from "N entries)"
            after_paren = line[paren_start + 2:]
            close_paren = after_paren.index(")")
            entries_text = after_paren[:close_paren]
            # Extract just the number (before "entries")
            entries = int(entries_text.split()[0])
            game_id = game.lower().replace(" ", "-")

            top = None
            remainder = after_paren[close_paren + 1:]
            if "Top:" in remainder:
                top_part = remainder.split("Top:")[1].strip()
                if " with " in top_part:
                    initials, score_str = top_part.split(" with ", 1)
                    try:
                        top = ScoreEntry(initials=initials.strip(), score=int(score_str.strip()))
                    except ValueError:
                        pass

            results.append(Scoreboard(game=game, game_id=game_id, entries=entries, top=top))
        except (ValueError, IndexError):
            continue
    return results


def parse_score_list(text: str) -> list[ScoreEntry]:
    """Parse the text output of get_scores into ScoreEntries."""
    results = []
    for line in text.splitlines():
        line = line.strip()
        if not line[0:1].isdigit() or ". " not in line:
            continue
        # Format: 1. ABC — 12345 (level 5)
        try:
            num_end = line.index(". ")
            rest = line[num_end + 2 :]
            initials, score_part = rest.split(" — ", 1)
            score_str = score_part.split("(")[0].strip()
            score = int(score_str)

            level = None
            if "level " in score_part:
                level_str = score_part.split("level ")[1].split(")")[0].split(",")[0]
                try:
                    level = int(level_str)
                except ValueError:
                    pass

            results.append(ScoreEntry(initials=initials.strip(), score=score, level=level))
        except (ValueError, IndexError):
            continue
    return results


def parse_pi_services(text: str) -> list[PiServiceStatus]:
    """Parse the text output of check_pi_services into PiServiceStatus."""
    results = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("✓") and not line.startswith("✗"):
            continue
        icon = line[0]
        rest = line[2:].strip()
        if ": " in rest:
            name, status = rest.split(": ", 1)
            results.append(PiServiceStatus(name=name.strip(), status=status.strip(), ok=icon == "✓"))
    return results


def parse_pi_system_info(text: str) -> PiSystemInfo:
    """Parse the text output of get_pi_system_info into PiSystemInfo."""
    info = {"uptime": "", "memory": "", "cpu_temp": "", "load": "", "disk": ""}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Uptime:"):
            info["uptime"] = line.split(":", 1)[1].strip()
        elif line.startswith("Memory:"):
            info["memory"] = line.split(":", 1)[1].strip()
        elif line.startswith("CPU Temp:"):
            info["cpu_temp"] = line.split(":", 1)[1].strip()
        elif line.startswith("Load:"):
            info["load"] = line.split(":", 1)[1].strip()
        elif line.startswith("Disk:"):
            info["disk"] = line.split(":", 1)[1].strip()
    return PiSystemInfo(**info)


def parse_bot_list(text: str) -> list[BotStatus]:
    """Parse the markdown table output of list_bots into BotStatus."""
    results = []
    for line in text.splitlines():
        if not line.startswith("|") or "---" in line or "Workflow" in line:
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) < 4:
            continue
        name = parts[0]
        status_raw = parts[1].lstrip("✓✗— ").strip()
        last_run = parts[2]
        event = parts[3]
        file = name.lower().replace(" ", "-") + ".yml"
        results.append(BotStatus(name=name, file=file, status=status_raw, last_run=last_run, event=event))
    return results


def parse_discogs_results(text: str) -> list[DiscogsResult]:
    """Parse the text output of search_discogs into DiscogsResults."""
    results = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("- ["):
            continue
        # Format: - [release] Artist - Title (2023) [ID: 12345]
        try:
            bracket_end = line.index("]")
            discogs_type = line[3:bracket_end]
            rest = line[bracket_end + 2 :]
            title = rest
            year = None
            discogs_id = ""
            if "(" in rest:
                parts = rest.split("(")
                title = parts[0].strip()
                year = parts[1].split(")")[0].strip()
            if "[ID:" in rest:
                id_part = rest.split("[ID:")[1].split("]")[0].strip()
                discogs_id = id_part
            results.append(DiscogsResult(title=title, type=discogs_type, id=discogs_id, year=year))
        except (ValueError, IndexError):
            continue
    return results


def parse_archive_pages(text: str) -> list[ArchivePage]:
    """Parse the text output of list_archive_pages into ArchivePages."""
    results = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("- ["):
            continue
        try:
            bracket_end = line.index("]")
            category = line[3:bracket_end]
            rest = line[bracket_end + 2 :]
            if " (" in rest:
                name, path = rest.rsplit(" (", 1)
                path = path.rstrip(")")
            else:
                name, path = rest, ""
            results.append(ArchivePage(name=name.strip(), path=path.strip(), category=category))
        except (ValueError, IndexError):
            continue
    return results


def parse_arcade_games(text: str) -> list[ArcadeGame]:
    """Parse the text output of list_arcade_games into ArcadeGames."""
    results = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        # Format: - name (path) [server port NNNN]
        try:
            rest = line[2:]
            has_server = "[server port" in rest
            port = None
            if has_server:
                port_str = rest.split("[server port")[1].split("]")[0].strip()
                port = int(port_str)
                rest = rest.split("[server port")[0].strip()

            if " (" in rest:
                name, path = rest.rsplit(" (", 1)
                path = path.rstrip(")")
            else:
                name, path = rest, ""

            results.append(ArcadeGame(name=name.strip(), path=path.strip(), has_server=has_server, port=port))
        except (ValueError, IndexError):
            continue
    return results


def parse_play_counts(text: str) -> list[PlayCount]:
    """Parse the markdown table output of get_play_counts into PlayCounts."""
    results = []
    for line in text.splitlines():
        if not line.startswith("|") or "---" in line or "Artist" in line:
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) < 4:
            continue
        name = parts[0]
        try:
            playcount = int(parts[1].replace(",", ""))
            listeners = int(parts[2].replace(",", ""))
        except ValueError:
            continue
        top_track = parts[3] if parts[3] else None
        results.append(PlayCount(name=name, listeners=listeners, playcount=playcount, top_track=top_track))
    return results
