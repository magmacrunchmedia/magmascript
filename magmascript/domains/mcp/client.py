"""MCP domain — typed client for all 23 MCP tools.

Wraps RPCClient with typed dataclasses. Raises MCPError on server failures.
"""

from __future__ import annotations

import json

import httpx

from magmascript.core.config import Config, get_config
from magmascript.core.exceptions import APIError, AuthError, MCPError
from magmascript.core.rpc import RPCClient, RPCError
from magmascript.domains.mcp.tools import (
    ArchivePage,
    ArcadeGame,
    BotStatus,
    DiscogsResult,
    Entity,
    PiServiceStatus,
    PiSystemInfo,
    PlayCount,
    RecordingDetail,
    ReleaseDetail,
    ReleaseSearchResult,
    ScoreEntry,
    Scoreboard,
    SearchResult,
    parse_archive_pages,
    parse_bot_list,
    parse_discogs_results,
    parse_arcade_games,
    parse_recording_detail,
    parse_release_detail,
    parse_release_search_results,
    parse_score_list,
    parse_scoreboard_list,
    parse_search_results,
    parse_pi_services,
    parse_pi_system_info,
    parse_play_counts,
)


def _wrap_mcp_error(e: Exception, context: str = "") -> Exception:
    """Wrap RPC and HTTP exceptions into typed magmascript errors."""
    if isinstance(e, RPCError):
        return MCPError(f"MCP error: {e.message}", code=e.code, data=e.data)
    if isinstance(e, RuntimeError):
        return MCPError(str(e))
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        msg = f"MCP server error {status}"
        if context:
            msg = f"{context}: {msg}"
        if status in (401, 403):
            return AuthError(msg, status_code=status)
        return APIError(msg, status_code=status)
    if isinstance(e, httpx.ConnectError):
        return APIError(f"MCP server unreachable" if not context else f"{context}: MCP server unreachable")
    if isinstance(e, httpx.TimeoutException):
        return APIError(f"MCP server timed out" if not context else f"{context}: timed out")
    return MCPError(str(e) if not context else f"{context}: {e}")


class MCPClient:
    """Typed client for the MagmaCrunch MCP server.

    Wraps RPCClient with domain-specific methods that return typed dataclasses.
    Raises MCPError on server failures, APIError on connection issues.
    """

    def __init__(self, config: Config | None = None):
        cfg = config or get_config()
        self._rpc = RPCClient(url=cfg.mcp.url, api_key=cfg.mcp.api_key)

    def _call(self, tool: str, args: dict | None = None) -> str:
        """Call an MCP tool and return the text result.

        Wraps exceptions into MCPError/APIError.
        """
        try:
            return self._rpc.call_tool(tool, args or {})
        except Exception as e:
            raise _wrap_mcp_error(e, tool)

    # ------------------------------------------------------------------
    # MusicBrainz Cache
    # ------------------------------------------------------------------

    def search(self, query: str) -> list[SearchResult]:
        """Search cached MusicBrainz entity names by substring."""
        text = self._call("search_cache", {"query": query})
        return parse_search_results(text)

    def list_entities(self, entity_type: str = "") -> list[SearchResult]:
        """List all cached MusicBrainz entities, optionally filtered by type."""
        args = {"entity_type": entity_type} if entity_type else {}
        text = self._call("list_cached_entities", args)
        return parse_search_results(text)

    def get_entity(self, entity_type: str, key: str) -> Entity:
        """Get full cache data for a specific MusicBrainz entity."""
        text = self._call("get_entity", {"entity_type": entity_type, "key": key})
        try:
            data = json.loads(text) if text.strip().startswith("{") else {}
        except json.JSONDecodeError:
            data = {}
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
        text = self._call("list_scoreboards")
        return parse_scoreboard_list(text)

    def scores(self, game: str, limit: int = 10) -> list[ScoreEntry]:
        """Get leaderboard for a specific game."""
        text = self._call("get_scores", {"game": game, "limit": limit})
        return parse_score_list(text)

    # ------------------------------------------------------------------
    # Project Structure
    # ------------------------------------------------------------------

    def archive_pages(self) -> list[ArchivePage]:
        """List all archive pages (artists, places, contributors, labels)."""
        text = self._call("list_archive_pages")
        return parse_archive_pages(text)

    def arcade_games(self) -> list[ArcadeGame]:
        """List all arcade games with their paths and server status."""
        text = self._call("list_arcade_games")
        return parse_arcade_games(text)

    # ------------------------------------------------------------------
    # Pi Services (via MCP — slower, prefer magmascript pi domain)
    # ------------------------------------------------------------------

    def pi_status(self) -> list[PiServiceStatus]:
        """Check status of all arcade services on the Raspberry Pi."""
        text = self._call("check_pi_services")
        return parse_pi_services(text)

    def pi_logs(self, service: str, lines: int = 30) -> str:
        """Get recent logs for a Pi service."""
        return self._call("get_service_logs", {"service": service, "lines_count": lines})

    def pi_restart(self, service: str) -> str:
        """Restart a service on the Raspberry Pi."""
        return self._call("restart_pi_service", {"service": service})

    def pi_info(self) -> PiSystemInfo:
        """Get Raspberry Pi system info (uptime, memory, CPU temp, load)."""
        text = self._call("get_pi_system_info")
        return parse_pi_system_info(text)

    # ------------------------------------------------------------------
    # Deployment
    # ------------------------------------------------------------------

    def deploy(self, path: str, service: str = "") -> str:
        """Deploy files to the Raspberry Pi via rsync."""
        args = {"local_path": path}
        if service:
            args["service"] = service
        return self._call("deploy_to_pi", args)

    # ------------------------------------------------------------------
    # GitHub Bots (via MCP — prefer magmascript gh domain)
    # ------------------------------------------------------------------

    def bots(self) -> list[BotStatus]:
        """List all GitHub Actions workflows with their last run status."""
        text = self._call("list_bots")
        return parse_bot_list(text)

    def bot_status(self, name: str) -> str:
        """Get detailed status of a specific workflow."""
        return self._call("get_bot_status", {"workflow_name": name})

    def trigger_bot(self, name: str) -> str:
        """Trigger a GitHub Actions workflow manually."""
        return self._call("trigger_bot", {"workflow_name": name})

    def bot_runs(self, name: str, limit: int = 10) -> str:
        """Get recent run history for a workflow."""
        return self._call("get_bot_runs", {"workflow_name": name, "limit": limit})

    # ------------------------------------------------------------------
    # Discogs
    # ------------------------------------------------------------------

    def discogs_search(self, query: str, search_type: str = "release") -> list[DiscogsResult]:
        """Search Discogs for releases, artists, or labels."""
        text = self._call("search_discogs", {"query": query, "search_type": search_type})
        return parse_discogs_results(text)

    def discogs_release(self, release_id: str) -> str:
        """Get full details for a Discogs release."""
        return self._call("get_discogs_release", {"release_id": release_id})

    def discogs_artist(self, artist_id: str) -> str:
        """Get artist profile, bio, and discography from Discogs."""
        return self._call("get_discogs_artist", {"artist_id": artist_id})

    def discogs_label(self, label_id: str) -> str:
        """Get label info and catalog from Discogs."""
        return self._call("get_discogs_label", {"label_id": label_id})

    # ------------------------------------------------------------------
    # Admin Data
    # ------------------------------------------------------------------

    def jukebox_songs(self) -> str:
        """Read the jukebox song list."""
        return self._call("get_jukebox_songs")

    def update_jukebox_songs(self, songs_json: str) -> str:
        """Write jukebox songs (JSON string)."""
        return self._call("update_jukebox_songs", {"songs_json": songs_json})

    def tv_channels(self) -> str:
        """Read the TV channel list."""
        return self._call("get_tv_channels")

    def update_tv_channels(self, channels_json: str) -> str:
        """Write TV channels (JSON string)."""
        return self._call("update_tv_channels", {"channels_json": channels_json})

    def themes(self) -> str:
        """Read the theme catalog."""
        return self._call("get_themes")

    def update_themes(self, themes_json: str) -> str:
        """Write themes (JSON string)."""
        return self._call("update_themes", {"themes_json": themes_json})

    def play_counts(self) -> list[PlayCount]:
        """List all artists with their Last.fm play counts."""
        text = self._call("get_play_counts")
        return parse_play_counts(text)

    def artist_play_counts(self, artist_name: str) -> str:
        """Get detailed Last.fm stats for a specific artist."""
        return self._call("get_artist_play_counts", {"artist_name": artist_name})

    # ------------------------------------------------------------------
    # MusicBrainz API (direct calls, not via MCP tools)
    # ------------------------------------------------------------------

    def mb_search_releases(self, query: str, limit: int = 5) -> list[ReleaseSearchResult]:
        """Search MusicBrainz for releases by query string."""
        url = "https://musicbrainz.org/ws/2/release/"
        params = {"query": query, "fmt": "json", "limit": limit}
        headers = {"User-Agent": "magmascript/1.3.0 (https://github.com/magmacrunchmedia/magmascript)"}
        try:
            resp = httpx.get(url, params=params, headers=headers, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            return parse_release_search_results(data)
        except Exception as e:
            raise _wrap_mcp_error(e, "mb_search_releases")

    def mb_get_release(self, mbid: str) -> ReleaseDetail:
        """Get full release details including track list with recordings."""
        url = f"https://musicbrainz.org/ws/2/release/{mbid}"
        params = {"fmt": "json", "inc": "artist-credits+recordings"}
        headers = {"User-Agent": "magmascript/1.3.0 (https://github.com/magmacrunchmedia/magmascript)"}
        try:
            resp = httpx.get(url, params=params, headers=headers, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            return parse_release_detail(data)
        except Exception as e:
            raise _wrap_mcp_error(e, "mb_get_release")

    def mb_get_recording(self, mbid: str) -> RecordingDetail:
        """Get recording details including ISRCs and work relationships."""
        url = f"https://musicbrainz.org/ws/2/recording/{mbid}"
        params = {"fmt": "json", "inc": "artist-credits+isrcs+work-rels"}
        headers = {"User-Agent": "magmascript/1.3.0 (https://github.com/magmacrunchmedia/magmascript)"}
        try:
            resp = httpx.get(url, params=params, headers=headers, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            return parse_recording_detail(data)
        except Exception as e:
            raise _wrap_mcp_error(e, "mb_get_recording")

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
