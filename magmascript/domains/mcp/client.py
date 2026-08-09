"""MCP domain — typed client for all 23 MCP tools."""

from __future__ import annotations

import json

from magmascript.core.config import Config, get_config
from magmascript.core.rpc import RPCClient
from magmascript.domains.mcp.tools import (
    ArchivePage,
    ArcadeGame,
    BotStatus,
    DiscogsResult,
    Entity,
    PiServiceStatus,
    PiSystemInfo,
    PlayCount,
    ScoreEntry,
    Scoreboard,
    SearchResult,
    parse_archive_pages,
    parse_bot_list,
    parse_discogs_results,
    parse_arcade_games,
    parse_score_list,
    parse_scoreboard_list,
    parse_search_results,
    parse_pi_services,
    parse_pi_system_info,
    parse_play_counts,
)


class MCPClient:
    """Typed client for the MagmaCrunch MCP server.

    Wraps RPCClient with domain-specific methods that return typed dataclasses.
    """

    def __init__(self, config: Config | None = None):
        cfg = config or get_config()
        self._rpc = RPCClient(url=cfg.mcp.url, api_key=cfg.mcp.api_key)

    # ------------------------------------------------------------------
    # MusicBrainz Cache
    # ------------------------------------------------------------------

    def search(self, query: str) -> list[SearchResult]:
        """Search cached MusicBrainz entity names by substring."""
        text = self._rpc.call_tool("search_cache", {"query": query})
        return parse_search_results(text)

    def list_entities(self, entity_type: str = "") -> list[SearchResult]:
        """List all cached MusicBrainz entities, optionally filtered by type."""
        args = {"entity_type": entity_type} if entity_type else {}
        text = self._rpc.call_tool("list_cached_entities", args)
        return parse_search_results(text)

    def get_entity(self, entity_type: str, key: str) -> Entity:
        """Get full cache data for a specific MusicBrainz entity."""
        text = self._rpc.call_tool("get_entity", {"entity_type": entity_type, "key": key})
        data = json.loads(text) if text.strip().startswith("{") else {}
        return Entity(
            name=data.get("name", key),
            uuid=data.get("uuid", key),
            type=entity_type,
            data=data,
        )

    # ------------------------------------------------------------------
    # High Scores
    # ------------------------------------------------------------------

    def scoreboards(self) -> list[Scoreboard]:
        """List all game leaderboards with entry counts and top scores."""
        text = self._rpc.call_tool("list_scoreboards")
        return parse_scoreboard_list(text)

    def scores(self, game: str, limit: int = 10) -> list[ScoreEntry]:
        """Get leaderboard for a specific game."""
        text = self._rpc.call_tool("get_scores", {"game": game, "limit": limit})
        return parse_score_list(text)

    # ------------------------------------------------------------------
    # Project Structure
    # ------------------------------------------------------------------

    def archive_pages(self) -> list[ArchivePage]:
        """List all archive pages (artists, places, contributors, labels)."""
        text = self._rpc.call_tool("list_archive_pages")
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

    def arcade_games(self) -> list[ArcadeGame]:
        """List all arcade games with their paths and server status."""
        text = self._rpc.call_tool("list_arcade_games")
        return parse_arcade_games(text)

    # ------------------------------------------------------------------
    # Pi Services (SSH)
    # ------------------------------------------------------------------

    def pi_status(self) -> list[PiServiceStatus]:
        """Check status of all arcade services on the Raspberry Pi."""
        text = self._rpc.call_tool("check_pi_services")
        return parse_pi_services(text)

    def pi_logs(self, service: str, lines: int = 30) -> str:
        """Get recent logs for a Pi service."""
        return self._rpc.call_tool("get_service_logs", {"service": service, "lines_count": lines})

    def pi_restart(self, service: str) -> str:
        """Restart a service on the Raspberry Pi."""
        return self._rpc.call_tool("restart_pi_service", {"service": service})

    def pi_info(self) -> PiSystemInfo:
        """Get Raspberry Pi system info (uptime, memory, CPU temp, load)."""
        text = self._rpc.call_tool("get_pi_system_info")
        return parse_pi_system_info(text)

    # ------------------------------------------------------------------
    # Deployment
    # ------------------------------------------------------------------

    def deploy(self, path: str, service: str = "") -> str:
        """Deploy files to the Raspberry Pi via rsync."""
        args = {"local_path": path}
        if service:
            args["service"] = service
        return self._rpc.call_tool("deploy_to_pi", args)

    # ------------------------------------------------------------------
    # GitHub Bots
    # ------------------------------------------------------------------

    def bots(self) -> list[BotStatus]:
        """List all GitHub Actions workflows with their last run status."""
        text = self._rpc.call_tool("list_bots")
        return parse_bot_list(text)

    def bot_status(self, name: str) -> str:
        """Get detailed status of a specific workflow."""
        return self._rpc.call_tool("get_bot_status", {"workflow_name": name})

    def trigger_bot(self, name: str) -> str:
        """Trigger a GitHub Actions workflow manually."""
        return self._rpc.call_tool("trigger_bot", {"workflow_name": name})

    def bot_runs(self, name: str, limit: int = 10) -> str:
        """Get recent run history for a workflow."""
        return self._rpc.call_tool("get_bot_runs", {"workflow_name": name, "limit": limit})

    # ------------------------------------------------------------------
    # Discogs
    # ------------------------------------------------------------------

    def discogs_search(self, query: str, search_type: str = "release") -> list[DiscogsResult]:
        """Search Discogs for releases, artists, or labels."""
        text = self._rpc.call_tool("search_discogs", {"query": query, "search_type": search_type})
        return parse_discogs_results(text)

    def discogs_release(self, release_id: str) -> str:
        """Get full details for a Discogs release."""
        return self._rpc.call_tool("get_discogs_release", {"release_id": release_id})

    def discogs_artist(self, artist_id: str) -> str:
        """Get artist profile, bio, and discography from Discogs."""
        return self._rpc.call_tool("get_discogs_artist", {"artist_id": artist_id})

    def discogs_label(self, label_id: str) -> str:
        """Get label info and catalog from Discogs."""
        return self._rpc.call_tool("get_discogs_label", {"label_id": label_id})

    # ------------------------------------------------------------------
    # Admin Data
    # ------------------------------------------------------------------

    def jukebox_songs(self) -> str:
        """Read the jukebox song list."""
        return self._rpc.call_tool("get_jukebox_songs")

    def tv_channels(self) -> str:
        """Read the TV channel list."""
        return self._rpc.call_tool("get_tv_channels")

    def themes(self) -> str:
        """Read the theme catalog."""
        return self._rpc.call_tool("get_themes")

    def play_counts(self) -> list[PlayCount]:
        """List all artists with their Last.fm play counts."""
        text = self._rpc.call_tool("get_play_counts")
        return parse_play_counts(text)

    def artist_play_counts(self, artist_name: str) -> str:
        """Get detailed Last.fm stats for a specific artist."""
        return self._rpc.call_tool("get_artist_play_counts", {"artist_name": artist_name})

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        """Close the underlying HTTP client."""
        self._rpc.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
