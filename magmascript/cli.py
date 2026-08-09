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
from magmascript.core.exceptions import MagmascriptError
from magmascript.core.output import format_output


def usage():
    print("""magmascript — scripting toolkit with domain-first subcommands

Usage:
    magmascript <domain> <action> [args...]

Domains:
    mcp         MagmaCrunch MCP server tools
    pi          Raspberry Pi management (direct SSH)
    gh          GitHub operations (direct API)
    media       Multi-provider media search
    scores      Game high scores (direct SSH)
    rights      Music rights metadata (ISRC, ISWC, ASCAP)
    cache       Cache management (stats, clear)

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

GitHub Actions:
    workflows                   List all workflows with status
    workflow <name>             Recent runs for one workflow
    trigger <name>              Trigger a workflow
    issues [label] [state]      List issues
    issue create <title> [body] Create an issue
    issue close <number>        Close an issue
    file <path>                 Read a file from the repo
    repo                        Repo info (test connection)

Media Search:
    search <query>              Search all providers
    search <query> --source s   Search specific provider
    providers                   List available providers
    image <id> --source <src>   Get single result by ID

Scores:
    list                        List all games with entry counts
    get <game> [limit]          Get leaderboard for a game (default top 20)
    report                      Generate full markdown report

Rights:
    search <query>              Search by title, ISRC, ISWC, or ASCAP ID
    search <query> --artist a   Search filtered by artist
    isrc <code>                 Look up recording by ISRC
    iswc <code>                 Look up work by ISWC
    ascap <id>                  Look up work by ASCAP ID
    catalog <artist>            Full rights catalog for an artist
    recording <uuid>            Rights data for a recording
    work <uuid>                 Rights data for a work
    export                      TSV export of all rights data

Cache:
    stats                       Show cache statistics
    clear [--domain <name>]     Clear cache entries

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

    # Parse --no-cache flag
    no_cache = False
    if "--no-cache" in rest:
        no_cache = True
        rest.remove("--no-cache")

    config = get_config()

    try:
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

        elif domain == "gh":
            from magmascript.domains.gh import GHClient
            client = GHClient(config)
            try:
                _dispatch_gh(action, rest, client, fmt)
            finally:
                client.close()

        elif domain == "media":
            from magmascript.domains.media import MediaClient
            client = MediaClient(config)
            try:
                _dispatch_media(action, rest, client, fmt)
            finally:
                client.close()

        elif domain == "scores":
            from magmascript.domains.scores import ScoresClient
            client = ScoresClient(config)
            try:
                _dispatch_scores(action, rest, client, fmt)
            finally:
                client.close()

        elif domain == "rights":
            from magmascript.domains.rights import RightsClient
            client = RightsClient(config)
            try:
                _dispatch_rights(action, rest, client, fmt)
            finally:
                client.close()

        elif domain == "cache":
            _dispatch_cache(action, rest, fmt)

        else:
            print(f"Unknown domain: {domain!r}. Available: mcp, pi, gh, media, scores, rights, cache", file=sys.stderr)
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except MagmascriptError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Invalid input: {e}", file=sys.stderr)
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


def _dispatch_gh(action: str, args: list[str], client, fmt: str):
    """Dispatch GitHub subcommands."""
    if not action or action == "--help":
        usage()

    if action == "workflows":
        results = client.workflows()
        print(format_output(results, fmt))

    elif action == "workflow":
        if not args:
            print("Usage: gh workflow <name>", file=sys.stderr)
            sys.exit(1)
        limit = int(args[1]) if len(args) > 1 else 10
        results = client.workflow_runs(args[0], limit)
        print(format_output(results, fmt))

    elif action == "trigger":
        if not args:
            print("Usage: gh trigger <name>", file=sys.stderr)
            sys.exit(1)
        result = client.trigger(args[0])
        print(result)

    elif action == "issues":
        labels = args[0] if args else ""
        state = args[1] if len(args) > 1 else "open"
        results = client.issues(labels=labels, state=state)
        print(format_output(results, fmt))

    elif action == "issue":
        if not args:
            print("Usage: gh issue create <title> [body] | gh issue close <number>", file=sys.stderr)
            sys.exit(1)
        sub = args[0]
        if sub == "create":
            if len(args) < 2:
                print("Usage: gh issue create <title> [body]", file=sys.stderr)
                sys.exit(1)
            title = args[1]
            body = args[2] if len(args) > 2 else ""
            result = client.create_issue(title, body)
            print(format_output(result, fmt))
        elif sub == "close":
            if len(args) < 2:
                print("Usage: gh issue close <number>", file=sys.stderr)
                sys.exit(1)
            result = client.close_issue(int(args[1]))
            print(result)
        else:
            print(f"Unknown issue action: {sub!r}. Use 'create' or 'close'.", file=sys.stderr)
            sys.exit(1)

    elif action == "file":
        if not args:
            print("Usage: gh file <path>", file=sys.stderr)
            sys.exit(1)
        content, sha = client.get_file(args[0])
        print(content)

    elif action == "repo":
        info = client.repo_info()
        print(f"  Name: {info.get('full_name', '?')}")
        print(f"  Private: {info.get('private', '?')}")
        print(f"  Default branch: {info.get('default_branch', '?')}")
        print(f"  Stars: {info.get('stargazers_count', '?')}")
        print(f"  Forks: {info.get('forks_count', '?')}")

    else:
        print(f"Unknown GitHub action: {action!r}", file=sys.stderr)
        print("Run 'magmascript gh --help' for available actions.", file=sys.stderr)
        sys.exit(1)


def _dispatch_media(action: str, args: list[str], client, fmt: str):
    """Dispatch media search subcommands."""
    if not action or action == "--help":
        usage()

    if action == "search":
        if not args:
            print("Usage: media search <query> [--source <provider>]", file=sys.stderr)
            sys.exit(1)

        query = args[0]
        source = ""
        media_type = ""
        orientation = ""
        page = 1
        per_page = 24

        i = 1
        while i < len(args):
            if args[i] == "--source" and i + 1 < len(args):
                source = args[i + 1]
                i += 2
            elif args[i] == "--type" and i + 1 < len(args):
                media_type = args[i + 1]
                i += 2
            elif args[i] == "--orientation" and i + 1 < len(args):
                orientation = args[i + 1]
                i += 2
            elif args[i] == "--page" and i + 1 < len(args):
                page = int(args[i + 1])
                i += 2
            elif args[i] == "--per-page" and i + 1 < len(args):
                per_page = int(args[i + 1])
                i += 2
            else:
                i += 1

        result = client.search(
            query, source=source, media_type=media_type,
            orientation=orientation, page=page, per_page=per_page,
        )

        parts = [f"{len(result.results)} results"]
        if result.provider_totals:
            detail = ", ".join(f"{k}: {v}" for k, v in result.provider_totals.items())
            parts.append(f"({detail})")
        print("  ".join(parts))

        if result.errors:
            for provider, error in result.errors.items():
                print(f"  ⚠ {provider}: {error}", file=sys.stderr)

        print()
        print(format_output(result.results, fmt))

    elif action == "providers":
        providers = client.list_providers()
        for p in providers:
            key_marker = " (needs key)" if p.needs_key else ""
            types_str = ", ".join(p.types)
            print(f"  {p.key:<15} {p.label:<15} [{types_str}]{key_marker}")

    elif action == "image":
        if len(args) < 2:
            print("Usage: media image <id> --source <provider>", file=sys.stderr)
            sys.exit(1)
        result_id = args[0]
        source = ""
        i = 1
        while i < len(args):
            if args[i] == "--source" and i + 1 < len(args):
                source = args[i + 1]
                i += 2
            else:
                i += 1
        if not source:
            print("Usage: media image <id> --source <provider>", file=sys.stderr)
            sys.exit(1)
        result = client.get(result_id, source)
        if result:
            print(format_output(result, fmt))
        else:
            print(f"Not found: {result_id} from {source}", file=sys.stderr)
            sys.exit(1)

    else:
        print(f"Unknown media action: {action!r}", file=sys.stderr)
        print("Run 'magmascript media --help' for available actions.", file=sys.stderr)
        sys.exit(1)


def _dispatch_scores(action: str, args: list[str], client, fmt: str):
    """Dispatch Scores subcommands."""
    if not action or action == "--help":
        usage()

    if action == "list":
        results = client.list_scoreboards()
        print(format_output(results, fmt))

    elif action == "get":
        if not args:
            print("Usage: scores get <game> [limit]", file=sys.stderr)
            sys.exit(1)
        limit = int(args[1]) if len(args) > 1 else 20
        results = client.get_scores(args[0], limit)
        print(format_output(results, fmt))

    elif action == "report":
        report = client.report()
        lines = [f"# Weekly High Scores — {report.generated_at}", ""]
        lines.append("## Leaderboards")
        lines.append("")
        for board in report.scoreboards:
            lines.append(f"### {board.game}")
            lines.append("")
            lines.append("| Rank | Player | Score |")
            lines.append("|------|--------|-------|")
            entries = client.get_scores(board.game_id, limit=5)
            for e in entries:
                parts = [str(e.score)]
                if e.level:
                    parts.append(f"L{e.level}")
                if e.difficulty:
                    parts.append(f"D{e.difficulty}")
                if e.time:
                    parts.append(e.time)
                if e.moves:
                    parts.append(f"{e.moves} moves")
                if e.won is False:
                    parts.append("lost")
                lines.append(f"| {e.rank} | {e.initials} | {' · '.join(parts)} |")
            if board.entries == 0:
                lines.append("| - | No scores yet | - |")
            lines.append("")

        lines.append("## Stats")
        lines.append("")
        lines.append(f"- **Games tracked**: {report.total_games}")
        lines.append(f"- **Total scores**: {report.total_scores}")
        if report.player_stats:
            top = report.player_stats[0]
            game_word = "game" if top.games_played == 1 else "games"
            lines.append(f"- **Most active player**: {top.name} ({top.total_entries} scores across {top.games_played} {game_word})")
            names = ", ".join(p.name for p in report.player_stats)
            lines.append(f"- **Players**: {names}")
        print("\n".join(lines))

    else:
        print(f"Unknown scores action: {action!r}", file=sys.stderr)
        print("Run 'magmascript scores --help' for available actions.", file=sys.stderr)
        sys.exit(1)


def _dispatch_rights(action: str, args: list[str], client, fmt: str):
    """Dispatch music rights subcommands."""
    if not action or action == "--help":
        print("""Music rights metadata (ISRC, ISWC, ASCAP).

Usage:
    magmascript rights search <query>         Search by title, ISRC, ISWC, or ASCAP ID
    magmascript rights isrc <code>            Look up recording by ISRC
    magmascript rights iswc <code>            Look up work by ISWC
    magmascript rights ascap <id>             Look up work by ASCAP ID
    magmascript rights catalog <artist>       Full rights catalog for an artist
    magmascript rights recording <uuid>       Rights data for a recording
    magmascript rights work <uuid>            Rights data for a work
    magmascript rights export                 TSV export of all rights data

Options:
    --artist <name>              Filter search by artist name
""")
        sys.exit(0)

    if action == "search":
        if not args:
            print("Usage: rights search <query> [--artist <name>]", file=sys.stderr)
            sys.exit(1)
        query = args[0]
        artist = ""
        if "--artist" in args:
            idx = args.index("--artist")
            if idx + 1 < len(args):
                artist = args[idx + 1]
            else:
                print("Usage: rights search <query> --artist <name>", file=sys.stderr)
                sys.exit(1)
        results = client.search(query, artist=artist)
        print(format_output(results, fmt))

    elif action == "isrc":
        if not args:
            print("Usage: rights isrc <code>", file=sys.stderr)
            sys.exit(1)
        result = client.isrc(args[0])
        if result:
            print(format_output(result, fmt))
        else:
            print(f"No recording found with ISRC: {args[0]}")
            sys.exit(1)

    elif action == "iswc":
        if not args:
            print("Usage: rights iswc <code>", file=sys.stderr)
            sys.exit(1)
        result = client.iswc(args[0])
        if result:
            print(format_output(result, fmt))
        else:
            print(f"No work found with ISWC: {args[0]}")
            sys.exit(1)

    elif action == "ascap":
        if not args:
            print("Usage: rights ascap <id>", file=sys.stderr)
            sys.exit(1)
        result = client.ascap(args[0])
        if result:
            print(format_output(result, fmt))
        else:
            print(f"No work found with ASCAP ID: {args[0]}")
            sys.exit(1)

    elif action == "catalog":
        if not args:
            print("Usage: rights catalog <artist>", file=sys.stderr)
            sys.exit(1)
        result = client.catalog(args[0])
        print(format_output(result, fmt))

    elif action == "recording":
        if not args:
            print("Usage: rights recording <uuid>", file=sys.stderr)
            sys.exit(1)
        result = client.recording(args[0])
        print(format_output(result, fmt))

    elif action == "work":
        if not args:
            print("Usage: rights work <uuid>", file=sys.stderr)
            sys.exit(1)
        result = client.work(args[0])
        print(format_output(result, fmt))

    elif action == "export":
        results = client.export()
        if fmt == "json":
            print(format_output(results, fmt))
        else:
            # TSV format
            print("Title\tType\tArtist/Composer\tISRC\tISWC\tASCAP ID")
            for row in results:
                print(f"{row.title}\t{row.type}\t{row.artist_composer}\t{row.isrc}\t{row.iswc}\t{row.ascap_id}")

    else:
        print(f"Unknown rights action: {action!r}", file=sys.stderr)
        print("Run 'magmascript rights --help' for available actions.", file=sys.stderr)
        sys.exit(1)


def _dispatch_cache(action: str, args: list[str], fmt: str):
    """Dispatch cache subcommands."""
    from magmascript.core.cache import get_cache

    cache = get_cache()

    if not action or action == "--help":
        print("""Cache management.

Usage:
    magmascript cache stats              Show cache statistics
    magmascript cache clear              Clear all cache
    magmascript cache clear --domain m   Clear specific domain (media/scores/gh)
""")
        sys.exit(0)

    if action == "stats":
        data = cache.file_stats()
        print(format_output(data, fmt))

    elif action == "clear":
        domain = None
        if "--domain" in args:
            idx = args.index("--domain")
            if idx + 1 < len(args):
                domain = args[idx + 1]
            else:
                print("Usage: cache clear --domain <name>", file=sys.stderr)
                sys.exit(1)
        count = cache.clear(domain=domain)
        label = f" domain '{domain}'" if domain else ""
        print(f"Cleared {count} cache entries{label}.")

    else:
        print(f"Unknown cache action: {action!r}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
