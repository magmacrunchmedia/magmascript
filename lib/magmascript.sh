#!/usr/bin/env bash
# magmascript shell helpers — source this file for quick MCP + Pi access
#
# Usage:
#   source lib/magmascript.sh
#   mcp_search "aphex twin"
#   pi_status
#   pi_logs arcade-chat

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Check if magmascript is installed
if command -v magmascript &>/dev/null; then
    _MAGMASCRIPT="magmascript"
else
    _MAGMASCRIPT="python3 -m magmascript.cli"
fi

# ── MCP helpers ──────────────────────────────────────────────────────────────

mcp_search() {
    $_MAGMASCRIPT mcp search "$@"
}

mcp_entities() {
    $_MAGMASCRIPT mcp entities "$@"
}

mcp_entity() {
    $_MAGMASCRIPT mcp entity "$@"
}

mcp_scoreboards() {
    $_MAGMASCRIPT mcp scoreboards
}

mcp_scores() {
    $_MAGMASCRIPT mcp scores "$@"
}

mcp_games() {
    $_MAGMASCRIPT mcp games
}

mcp_archive() {
    $_MAGMASCRIPT mcp archive
}

mcp_bots() {
    $_MAGMASCRIPT mcp bots
}

mcp_bot_status() {
    $_MAGMASCRIPT mcp bot-status "$@"
}

mcp_trigger() {
    $_MAGMASCRIPT mcp trigger "$@"
}

mcp_discogs() {
    $_MAGMASCRIPT mcp discogs "$@"
}

mcp_jukebox() {
    $_MAGMASCRIPT mcp jukebox
}

mcp_tv() {
    $_MAGMASCRIPT mcp tv
}

mcp_themes() {
    $_MAGMASCRIPT mcp themes
}

mcp_plays() {
    $_MAGMASCRIPT mcp plays
}

mcp_artist_plays() {
    $_MAGMASCRIPT mcp artist-plays "$@"
}

# ── Pi helpers ───────────────────────────────────────────────────────────────

pi_status() {
    $_MAGMASCRIPT pi status
}

pi_logs() {
    $_MAGMASCRIPT pi logs "$@"
}

pi_logs_errors() {
    $_MAGMASCRIPT pi logs-errors "$@"
}

pi_logs_today() {
    $_MAGMASCRIPT pi logs-today
}

pi_restart() {
    $_MAGMASCRIPT pi restart "$@"
}

pi_restart_all() {
    $_MAGMASCRIPT pi restart-all
}

pi_info() {
    $_MAGMASCRIPT pi info
}

pi_traffic() {
    $_MAGMASCRIPT pi traffic "$@"
}

pi_deploy() {
    $_MAGMASCRIPT pi deploy "$@"
}

pi_reboot() {
    $_MAGMASCRIPT pi reboot
}

pi_shutdown() {
    $_MAGMASCRIPT pi shutdown
}

# ── GitHub helpers ───────────────────────────────────────────────────────────

gh_workflows() {
    $_MAGMASCRIPT gh workflows
}

gh_workflow() {
    $_MAGMASCRIPT gh workflow "$@"
}

gh_trigger() {
    $_MAGMASCRIPT gh trigger "$@"
}

gh_issues() {
    $_MAGMASCRIPT gh issues "$@"
}

gh_issue_create() {
    $_MAGMASCRIPT gh issue create "$@"
}

gh_issue_close() {
    $_MAGMASCRIPT gh issue close "$@"
}

gh_file() {
    $_MAGMASCRIPT gh file "$@"
}

gh_repo() {
    $_MAGMASCRIPT gh repo
}

# ── Media helpers ────────────────────────────────────────────────────────────

media_search() {
    $_MAGMASCRIPT media search "$@"
}

media_providers() {
    $_MAGMASCRIPT media providers
}

media_image() {
    $_MAGMASCRIPT media image "$@"
}

# ── Scores helpers ───────────────────────────────────────────────────────────

scores_list() {
    $_MAGMASCRIPT scores list
}

scores_get() {
    $_MAGMASCRIPT scores get "$@"
}

scores_report() {
    $_MAGMASCRIPT scores report
}

echo "magmascript shell helpers loaded."
echo "MCP: mcp_search, mcp_scoreboards, mcp_scores, mcp_bots, ..."
echo "Pi:  pi_status, pi_logs, pi_restart, pi_info, pi_traffic, ..."
echo "GH:  gh_workflows, gh_trigger, gh_issues, gh_file, ..."
echo "Media: media_search, media_providers, ..."
echo "Scores: scores_list, scores_get, scores_report"

# ── Test domain for scaffolding helpers ────────────────────────────────────────────────────

test-domain_search() {
    $_MAGMASCRIPT test-domain search "$@"
}
