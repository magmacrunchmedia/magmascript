#!/usr/bin/env bash
# magmascript shell helpers — source this file for quick MCP access
#
# Usage:
#   source lib/magmascript.sh
#   mcp_search "aphex twin"
#   mcp_scores tetris
#   mcp_scoreboards

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Check if magmascript is installed
if command -v magmascript &>/dev/null; then
    _MAGMASCRIPT="magmascript"
else
    _MAGMASCRIPT="python3 -m magmascript.cli"
fi

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

mcp_pi_status() {
    $_MAGMASCRIPT mcp pi-status
}

mcp_pi_logs() {
    $_MAGMASCRIPT mcp pi-logs "$@"
}

mcp_pi_restart() {
    $_MAGMASCRIPT mcp pi-restart "$@"
}

mcp_pi_info() {
    $_MAGMASCRIPT mcp pi-info
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

echo "magmascript shell helpers loaded. Type mcp_ and press TAB for available commands."
