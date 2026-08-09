"""MCP domain — exposes MCPClient and registers with the domain registry."""

from magmascript.domains.mcp.client import MCPClient
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
)
from magmascript.core.registry import register_domain

# Register this domain
register_domain("mcp", MCPClient)

__all__ = [
    "MCPClient",
    "ArchivePage",
    "ArcadeGame",
    "BotStatus",
    "DiscogsResult",
    "Entity",
    "PiServiceStatus",
    "PiSystemInfo",
    "PlayCount",
    "ScoreEntry",
    "Scoreboard",
    "SearchResult",
]
