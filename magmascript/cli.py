"""CLI entry point for magmascript.

Usage:
    magmascript mcp search "aphex twin"
    magmascript mcp scores tetris
    magmascript pi status
    magmascript pi logs arcade-chat
"""

from __future__ import annotations

import json
import sys

from magmascript.core.config import get_config
from magmascript.core.exceptions import MagmascriptError
from magmascript.core.output import format_output


def _generate_channels_js(channels: list[dict]) -> str:
    """Generate visual/tv/channels.js from TV channel data."""
    lines = []
    for ch in channels:
        lines.append(
            '    { title: ' + json.dumps(ch.get("title", "")) +
            ', artist: ' + json.dumps(ch.get("artist", "")) +
            ', id: ' + json.dumps(ch.get("id", "")) +
            ', year: ' + json.dumps(ch.get("year", "")) + ' }'
        )
    return 'window.TV_CHANNELS = [\n' + ',\n'.join(lines) + '\n];\n'


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
    archive     Archive page operations
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
    jukebox save <file>         Save songs from JSON file
    jukebox save <file> --deploy  Save + commit to GitHub
    tv                          List TV channels
    tv save <file>              Save channels from JSON file
    tv save <file> --deploy     Save + commit to GitHub (JSON + channels.js)
    themes                      List theme catalog
    themes save <file>          Save themes from JSON file
    themes save <file> --deploy  Save + commit to GitHub
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
    backup musicbrainz          Run MusicBrainz backup + commit to GitHub
    backup tmdb                 Run TMDB backup + commit to GitHub

GitHub Actions:
    workflows                   List all workflows with status
    workflow <name>             Recent runs for one workflow
    trigger <name>              Trigger a workflow
    issues [label] [state]      List issues
    issue create <title> [body] Create an issue
    issue close <number>        Close an issue
    file <path>                 Read a file from the repo
    repo                        Repo info (test connection)
    sync                        Diff local data vs GitHub, commit changes
    sync --dry-run              Preview changes without committing
    sync --message "..."        Custom commit message

Media Search:
    search <query>              Search all providers
    search <query> --source s   Search specific provider
    providers                   List available providers
    image <id> --source <src>   Get single result by ID

Scores:
    list                        List all games with entry counts
    get <game> [limit]          Get leaderboard for a game (default top 20)
    report                      Generate full markdown report
    reset <game>                Reset scores for one game (backup created)
    reset-all                   Reset all game scores

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

Archive:
    check-format                Validate archive HTML formatting
    bake-cache [--dry-run]      Inlines MusicBrainz cache into HTML pages
    generate-stubs              Generate stub HTML for new archive entities

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

        elif domain == "archive":
            from magmascript.domains.archive import ArchiveClient
            client = ArchiveClient()
            try:
                _dispatch_archive(action, rest, client, fmt)
            finally:
                pass  # ArchiveClient doesn't have a close method

        elif domain == "cache":
            _dispatch_cache(action, rest, fmt)

        else:
            print(f"Unknown domain: {domain!r}. Available: mcp, pi, gh, media, scores, rights, archive, cache", file=sys.stderr)
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
        _dispatch_jukebox(args, client, fmt)

    elif action == "tv":
        _dispatch_tv(args, client, fmt)

    elif action == "themes":
        _dispatch_themes(args, client, fmt)

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

    elif action == "backup":
        if not args or args[0] not in ("musicbrainz", "tmdb"):
            print("Usage: pi backup <musicbrainz|tmdb>", file=sys.stderr)
            sys.exit(1)
        backup_type = args[0]
        message = ""
        if "--message" in args:
            idx = args.index("--message")
            if idx + 1 < len(args):
                message = args[idx + 1]

        print(f"Running {backup_type} backup on Pi...")
        result = client.run_backup(backup_type, timeout=600)
        print(result)

        # Pull changed files from Pi and commit
        from magmascript.core.config import get_config
        config = get_config()
        pi_host = config.pi.host
        pi_user = config.pi.user

        print("Pulling cache from Pi...")
        import subprocess
        subprocess.run(
            ["rsync", "-avz",
             f"{pi_user}@{pi_host}:~/website/archive/_cache/", "archive/_cache/"],
            capture_output=True, text=True, timeout=60,
        )

        # Check for changes
        git_result = subprocess.run(
            ["git", "diff", "--name-only", "archive/_cache/"],
            capture_output=True, text=True, timeout=10,
        )
        changed = [f for f in git_result.stdout.strip().splitlines() if f]

        if not changed:
            print("No cache files changed.")
            return

        print(f"Found {len(changed)} changed file(s). Committing...")
        from magmascript.domains.gh import GHClient
        gh = GHClient(config)
        try:
            files = []
            for path in changed:
                try:
                    with open(path) as f:
                        files.append({"path": path, "content": f.read()})
                except Exception:
                    continue
            if files:
                msg = message or f"Update {backup_type} cache via magmascript"
                result = gh.commit_multiple(files, msg)
                print(result)
        finally:
            gh.close()

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

    elif action == "sync":
        message = ""
        dry_run = False
        if "--dry-run" in args:
            dry_run = True
            args.remove("--dry-run")
        if "--message" in args:
            idx = args.index("--message")
            if idx + 1 < len(args):
                message = args[idx + 1]
        result = client.sync_all(message=message, dry_run=dry_run)
        print(result)

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
        # Parse flags
        discord_mode = "--discord" in args
        post_discussion = "--post-discussion" in args
        post_discord = "--post-discord" in args

        if discord_mode:
            # Output Discord JSON payload
            payload = client.report_discord()
            print(json.dumps({"embeds": payload.embeds}, indent=2))
        else:
            # Generate markdown report
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
            markdown = "\n".join(lines)
            print(markdown)

            # Post to GitHub Discussion if requested
            if post_discussion:
                from magmascript.core.config import get_config
                from magmascript.domains.gh import GHClient
                config = get_config()
                gh = GHClient(config)
                try:
                    date = datetime.now().strftime("%Y-%m-%d")
                    title = f"Weekly High Scores — {date}"
                    result = gh.create_discussion(title, markdown, "high-scores")
                    print(result)
                finally:
                    gh.close()

        # Post to Discord if requested
        if post_discord:
            from magmascript.core.config import get_config
            config = get_config()
            webhook_url = config.discord.webhook_url if hasattr(config, 'discord') else None
            if not webhook_url:
                print("Error: Discord webhook URL not configured", file=sys.stderr)
                sys.exit(1)
            
            # Get Discord payload
            payload = client.report_discord()
            import httpx
            try:
                resp = httpx.post(
                    webhook_url,
                    json={"embeds": payload.embeds},
                    headers={"Content-Type": "application/json"},
                    timeout=10.0,
                )
                resp.raise_for_status()
                print("✓ Posted to Discord")
            except Exception as e:
                print(f"Error posting to Discord: {e}", file=sys.stderr)
                sys.exit(1)

    elif action == "reset":
        if not args:
            print("Usage: scores reset <game>", file=sys.stderr)
            sys.exit(1)
        confirm = input(f"Reset all scores for {args[0]}? This creates a backup. [y/N] ")
        if confirm.lower() != "y":
            print("Cancelled.")
            sys.exit(0)
        result = client.reset(args[0])
        print(result)

    elif action == "reset-all":
        confirm = input("Reset ALL high scores across ALL games? This creates backups. [y/N] ")
        if confirm.lower() != "y":
            print("Cancelled.")
            sys.exit(0)
        result = client.reset_all()
        print(result)

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


def _dispatch_archive(action: str, args: list[str], client, fmt: str):
    """Dispatch Archive subcommands."""
    if not action or action == "--help":
        print("""Archive page operations.

Usage:
    magmascript archive check-format        Validate archive HTML formatting
    magmascript archive bake-cache          Inlines MusicBrainz cache into HTML pages
    magmascript archive bake-cache --dry-run  Preview changes without writing
    magmascript archive generate-stubs      Generate stub HTML for new archive entities
""")
        sys.exit(0)

    if action == "check-format":
        warnings = client.check_format()
        if fmt == "json":
            print(json.dumps([{"file": w.file, "line": w.line, "msg": w.msg} for w in warnings], indent=2))
        else:
            if not warnings:
                print("all checks passed")
            else:
                for w in warnings:
                    print(f"\nWARN  {w.file}:{w.line}")
                    print(f"      {w.msg}")
                print(f"\n{len(warnings)} warning{'s' if len(warnings) != 1 else ''} found")
        if warnings:
            sys.exit(1)

    elif action == "bake-cache":
        dry_run = "--dry-run" in args
        result = client.bake_cache(dry_run=dry_run)
        if fmt == "json":
            print(json.dumps({"baked": result.baked, "skipped": result.skipped, "errors": result.errors}, indent=2))
        else:
            print(f"\nDone! {result.baked} pages baked, {result.skipped} skipped.")
            if dry_run:
                print("(dry run — no files were written)")
            if result.errors:
                print(f"\nErrors:")
                for err in result.errors:
                    print(f"  {err}")

    elif action == "generate-stubs":
        result = client.generate_stubs()
        if fmt == "json":
            print(json.dumps(result, indent=2))
        else:
            print(f"Generated {result['generated']} stubs, skipped {result['skipped']}")

    else:
        print(f"Unknown archive action: {action!r}", file=sys.stderr)
        print("Run 'magmascript archive --help' for available actions.", file=sys.stderr)
        sys.exit(1)


def _dispatch_jukebox(args: list[str], client, fmt: str):
    """Dispatch jukebox subcommands."""
    if args and args[0] == "--help":
        print("""Jukebox management.

Usage:
    magmascript mcp jukebox                        List songs
    magmascript mcp jukebox save <file.json>       Save songs from JSON file
    magmascript mcp jukebox save <file.json> --deploy  Save + commit to GitHub
""")
        sys.exit(0)

    if not args or args[0] == "list":
        result = client.jukebox_songs()
        print(result)
        return

    sub = args[0]
    rest = args[1:]

    if sub == "save":
        if not rest:
            print("Usage: mcp jukebox save <file.json> [--deploy]", file=sys.stderr)
            sys.exit(1)
        file_path = rest[0]
        deploy = "--deploy" in rest

        try:
            with open(file_path) as f:
                songs = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading {file_path}: {e}", file=sys.stderr)
            sys.exit(1)

        songs_json = json.dumps(songs, indent=2)
        result = client.update_jukebox_songs(songs_json)
        print(result)

        if deploy:
            from magmascript.domains.gh import GHClient
            config = get_config()
            gh = GHClient(config)
            try:
                msg = "Update jukebox songs via magmascript"
                result = gh.commit_multiple(
                    [{"path": "arcade/admin/jukebox-songs.json", "content": songs_json}],
                    msg,
                )
                print(result)
            finally:
                gh.close()


def _dispatch_tv(args: list[str], client, fmt: str):
    """Dispatch TV channel subcommands."""
    if args and args[0] == "--help":
        print("""TV channel management.

Usage:
    magmascript mcp tv                         List channels
    magmascript mcp tv save <file.json>        Save channels from JSON file
    magmascript mcp tv save <file.json> --deploy  Save + commit (JSON + channels.js)
""")
        sys.exit(0)

    if not args or args[0] == "list":
        result = client.tv_channels()
        print(result)
        return

    sub = args[0]
    rest = args[1:]

    if sub == "save":
        if not rest:
            print("Usage: mcp tv save <file.json> [--deploy]", file=sys.stderr)
            sys.exit(1)
        file_path = rest[0]
        deploy = "--deploy" in rest

        try:
            with open(file_path) as f:
                channels = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading {file_path}: {e}", file=sys.stderr)
            sys.exit(1)

        channels_json = json.dumps(channels, indent=2)
        result = client.update_tv_channels(channels_json)
        print(result)

        if deploy:
            from magmascript.domains.gh import GHClient
            config = get_config()
            gh = GHClient(config)
            try:
                channels_js = _generate_channels_js(channels)
                msg = "Update TV channels via magmascript"
                result = gh.commit_multiple(
                    [
                        {"path": "arcade/admin/tv-channels.json", "content": channels_json},
                        {"path": "visual/tv/channels.js", "content": channels_js},
                    ],
                    msg,
                )
                print(result)
            finally:
                gh.close()


def _dispatch_themes(args: list[str], client, fmt: str):
    """Dispatch theme subcommands."""
    if args and args[0] == "--help":
        print("""Theme management.

Usage:
    magmascript mcp themes                       List themes
    magmascript mcp themes save <file.json>      Save themes from JSON file
    magmascript mcp themes save <file.json> --deploy  Save + commit to GitHub
""")
        sys.exit(0)

    if not args or args[0] == "list":
        result = client.themes()
        print(result)
        return

    sub = args[0]
    rest = args[1:]

    if sub == "save":
        if not rest:
            print("Usage: mcp themes save <file.json> [--deploy]", file=sys.stderr)
            sys.exit(1)
        file_path = rest[0]
        deploy = "--deploy" in rest

        try:
            with open(file_path) as f:
                themes = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading {file_path}: {e}", file=sys.stderr)
            sys.exit(1)

        themes_json = json.dumps(themes, indent=2)
        result = client.update_themes(themes_json)
        print(result)

        if deploy:
            from magmascript.domains.gh import GHClient
            config = get_config()
            gh = GHClient(config)
            try:
                msg = "Update themes via magmascript"
                result = gh.commit_multiple(
                    [{"path": "arcade/admin/themes.json", "content": themes_json}],
                    msg,
                )
                print(result)
            finally:
                gh.close()


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
