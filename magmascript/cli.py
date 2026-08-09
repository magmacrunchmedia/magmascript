"""CLI entry point for magmascript.

Usage:
    magmascript mcp search "aphex twin"
    magmascript mcp scores tetris
    magmascript pi status
    magmascript pi logs arcade-chat
"""

from __future__ import annotations

import sys

from magmascript.core.config import get_config
from magmascript.core.output import format_output


def usage():
    print("""magmascript — scripting toolkit with domain-first subcommands

Usage:
    magmascript <domain> <action> [args...]

Domains:
    mcp         MagmaCrunch MCP server tools
    pi          Raspberry Pi management (direct SSH)

MCP Actions:
    search <query>              Search cached MusicBrainz entities
    entities [type]             List cached entities (artists, places, etc.)
    entity <type> <key>         Get full entity data
    scoreboards                 List all game leaderboards
    scores <game> [limit]       Get leaderboard for a game
    games                       List all arcade games
    archive                     List all archive pages
    bots                        List GitHub Actions workflows
    bot-status <name>           Get workflow details
    trigger <name>              Trigger a workflow
    bot-runs <name> [limit]     Get workflow run history
    discogs <query> [type]      Search Discogs
    jukebox                     List jukebox songs
    tv                          List TV channels
    themes                      List theme catalog
    plays                       List Last.fm play counts
    artist-plays <name>         Get artist play counts

Pi Actions:
    status                      Check all arcade service statuses
    logs <service> [lines]      Get service logs
    logs-errors [lines]         Get error logs from all services
    logs-today                  Get today's logs
    restart <service>           Restart a service
    restart-all                 Restart all arcade services
    info                        System info (uptime, memory, temp)
    traffic [lines]             Nginx access log analysis
    deploy <path> [service]     Deploy to Pi via rsync
    reboot                      Reboot the Pi
    shutdown                    Power off the Pi

Options:
    --json                      Output as JSON
    --table                     Output as table (default)
    --help                      Show this help
""")
    sys.exit(0)


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("--help", "-h", "help"):
        usage()

    domain = args[0]
    action = args[1] if len(args) > 1 else ""
    rest = args[2:]

    # Parse output format
    fmt = "table"
    if "--json" in rest:
        fmt = "json"
        rest.remove("--json")
    elif "--table" in rest:
        rest.remove("--table")

    config = get_config()

    if domain == "mcp":
        from magmascript.domains.mcp import MCPClient
        client = MCPClient(config)
        try:
            _dispatch_mcp(action, rest, client, fmt)
        finally:
            client.close()

    elif domain == "pi":
        from magmascript.domains.pi import PIClient
        client = PIClient(config)
        try:
            _dispatch_pi(action, rest, client, fmt)
        finally:
            client.close()

    else:
        print(f"Unknown domain: {domain!r}. Available: mcp, pi", file=sys.stderr)
        sys.exit(1)


def _dispatch_mcp(action: str, args: list[str], client, fmt: str):
    """Dispatch MCP subcommands."""
    if not action or action == "--help":
        usage()

    if action == "search":
        if not args:
            print("Usage: mcp search <query>", file=sys.stderr)
            sys.exit(1)
        results = client.search(args[0])
        print(format_output(results, fmt))

    elif action == "entities":
        entity_type = args[0] if args else ""
        results = client.list_entities(entity_type)
        print(format_output(results, fmt))

    elif action == "entity":
        if len(args) < 2:
            print("Usage: mcp entity <type> <key>", file=sys.stderr)
            sys.exit(1)
        result = client.get_entity(args[0], args[1])
        print(format_output(result, fmt))

    elif action == "scoreboards":
        results = client.scoreboards()
        print(format_output(results, fmt))

    elif action == "scores":
        if not args:
            print("Usage: mcp scores <game> [limit]", file=sys.stderr)
            sys.exit(1)
        limit = int(args[1]) if len(args) > 1 else 10
        results = client.scores(args[0], limit)
        print(format_output(results, fmt))

    elif action == "games":
        results = client.arcade_games()
        print(format_output(results, fmt))

    elif action == "archive":
        results = client.archive_pages()
        print(format_output(results, fmt))

    elif action == "bots":
        results = client.bots()
        print(format_output(results, fmt))

    elif action == "bot-status":
        if not args:
            print("Usage: mcp bot-status <name>", file=sys.stderr)
            sys.exit(1)
        result = client.bot_status(args[0])
        print(result)

    elif action == "trigger":
        if not args:
            print("Usage: mcp trigger <name>", file=sys.stderr)
            sys.exit(1)
        result = client.trigger_bot(args[0])
        print(result)

    elif action == "bot-runs":
        if not args:
            print("Usage: mcp bot-runs <name> [limit]", file=sys.stderr)
            sys.exit(1)
        limit = int(args[1]) if len(args) > 1 else 10
        result = client.bot_runs(args[0], limit)
        print(result)

    elif action == "discogs":
        if not args:
            print("Usage: mcp discogs <query> [type]", file=sys.stderr)
            sys.exit(1)
        search_type = args[1] if len(args) > 1 else "release"
        results = client.discogs_search(args[0], search_type)
        print(format_output(results, fmt))

    elif action == "jukebox":
        result = client.jukebox_songs()
        print(result)

    elif action == "tv":
        result = client.tv_channels()
        print(result)

    elif action == "themes":
        result = client.themes()
        print(result)

    elif action == "plays":
        results = client.play_counts()
        print(format_output(results, fmt))

    elif action == "artist-plays":
        if not args:
            print("Usage: mcp artist-plays <name>", file=sys.stderr)
            sys.exit(1)
        result = client.artist_play_counts(args[0])
        print(result)

    else:
        print(f"Unknown MCP action: {action!r}", file=sys.stderr)
        print("Run 'magmascript mcp --help' for available actions.", file=sys.stderr)
        sys.exit(1)


def _dispatch_pi(action: str, args: list[str], client, fmt: str):
    """Dispatch Pi subcommands."""
    if not action or action == "--help":
        usage()

    if action == "status":
        results = client.services()
        print(format_output(results, fmt))

    elif action == "logs":
        if not args:
            print("Usage: pi logs <service> [lines]", file=sys.stderr)
            sys.exit(1)
        lines = int(args[1]) if len(args) > 1 else 50
        result = client.logs(args[0], lines)
        print(result)

    elif action == "logs-errors":
        lines = int(args[0]) if args else 100
        result = client.logs_errors(lines)
        print(result)

    elif action == "logs-today":
        result = client.logs_today()
        print(result)

    elif action == "restart":
        if not args:
            print("Usage: pi restart <service>", file=sys.stderr)
            sys.exit(1)
        result = client.restart(args[0])
        print(result)

    elif action == "restart-all":
        result = client.restart_all()
        print(result)

    elif action == "info":
        result = client.info()
        print(format_output(result, fmt))

    elif action == "traffic":
        lines = int(args[0]) if args else 1000
        result = client.traffic(lines)
        print(f"=== Top IPs ===\n{result.top_ips}")
        print(f"\n=== Status Codes ===\n{result.status_codes}")
        print(f"\n=== User Agents ===\n{result.user_agents}")
        print(f"\n=== Total Requests ===\n{result.total_requests}")

    elif action == "deploy":
        if not args:
            print("Usage: pi deploy <path> [service]", file=sys.stderr)
            sys.exit(1)
        service = args[1] if len(args) > 1 else ""
        result = client.deploy(args[0], service)
        print(result)

    elif action == "reboot":
        result = client.reboot()
        print(result)

    elif action == "shutdown":
        result = client.shutdown()
        print(result)

    else:
        print(f"Unknown Pi action: {action!r}", file=sys.stderr)
        print("Run 'magmascript pi --help' for available actions.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
