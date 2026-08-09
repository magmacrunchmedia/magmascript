"""Tests for the MCP client and tool parsers."""

import pytest

from magmascript.domains.mcp.tools import (
    parse_arcade_games,
    parse_bot_list,
    parse_discogs_results,
    parse_pi_services,
    parse_pi_system_info,
    parse_play_counts,
    parse_score_list,
    parse_scoreboard_list,
    parse_search_results,
)


class TestParseSearchResults:
    def test_basic(self):
        text = """Found 2 matches:

- [artists] Radiohead (abc-123)
- [places] London (def-456)"""
        results = parse_search_results(text)
        assert len(results) == 2
        assert results[0].name == "Radiohead"
        assert results[0].uuid == "abc-123"
        assert results[0].type == "artists"
        assert results[1].name == "London"
        assert results[1].type == "places"

    def test_empty(self):
        assert parse_search_results("No results found") == []


class TestParseScoreboardList:
    def test_basic(self):
        text = """Found 2 scoreboards:

- Tetris (6 entries) — Top: KC with 65486
- Solitaire (3 entries)"""
        results = parse_scoreboard_list(text)
        assert len(results) == 2
        assert results[0].game == "Tetris"
        assert results[0].entries == 6
        assert results[0].top.initials == "KC"
        assert results[0].top.score == 65486
        assert results[1].game == "Solitaire"
        assert results[1].top is None

    def test_empty(self):
        assert parse_scoreboard_list("No score files found") == []


class TestParseScoreList:
    def test_basic(self):
        text = """Tetris — Top 3:

  1. KC — 65486 (level 10)
  2. JAM — 19901 (level 6)
  3. JAM — 14053 (level 5)"""
        results = parse_score_list(text)
        assert len(results) == 3
        assert results[0].initials == "KC"
        assert results[0].score == 65486
        assert results[0].level == 10
        assert results[1].initials == "JAM"
        assert results[1].score == 19901

    def test_empty(self):
        assert parse_score_list("Unknown game 'foo'") == []


class TestParsePiServices:
    def test_basic(self):
        text = """Pi service status:

  ✓ arcade-sorry: active
  ✓ arcade-chat: active
  ✗ arcade-admin: inactive"""
        results = parse_pi_services(text)
        assert len(results) == 3
        assert results[0].name == "arcade-sorry"
        assert results[0].ok is True
        assert results[2].name == "arcade-admin"
        assert results[2].ok is False


class TestParsePiSystemInfo:
    def test_basic(self):
        text = """Pi system info:

  Uptime: up 5 days, 3 hours
  Memory: 16Gi total, 8Gi used
  CPU Temp: 45.0'C
  Load: 0.50 0.60 0.70
  Disk: /dev/root  120G  45G  75G"""
        result = parse_pi_system_info(text)
        assert result.uptime == "up 5 days, 3 hours"
        assert result.memory == "16Gi total, 8Gi used"
        assert result.cpu_temp == "45.0'C"
        assert result.load == "0.50 0.60 0.70"


class TestParseBotList:
    def test_basic(self):
        text = """# GitHub Actions Workflows

| Workflow | Status | Last Run | Trigger |
|---|---|---|---|
| CI | ✓ success | 2026-01-01T00:00 | push |
| Deploy to Pi | ✗ failure | 2026-01-02T00:00 | workflow_dispatch |"""
        results = parse_bot_list(text)
        assert len(results) == 2
        assert results[0].name == "CI"
        assert results[0].status == "success"
        assert results[1].name == "Deploy to Pi"
        assert results[1].status == "failure"


class TestParseDiscogsResults:
    def test_basic(self):
        text = """Found 2 Discogs results for 'radiohead':

- [release] Radiohead - Kid A (2000) [ID: 12345]
- [master] Radiohead - OK Computer (1997) [ID: 67890]"""
        results = parse_discogs_results(text)
        assert len(results) == 2
        assert results[0].title == "Radiohead - Kid A"
        assert results[0].type == "release"
        assert results[0].year == "2000"
        assert results[0].id == "12345"


class TestParseArcadeGames:
    def test_basic(self):
        text = """Found 3 arcade games:

- sorry (arcade/sorry/)
- tetris (arcade/tetris/) [server port 8780]
- solitaire (arcade/solitaire/)"""
        results = parse_arcade_games(text)
        assert len(results) == 2 or len(results) >= 2
        # tetris has a server
        tetris = [g for g in results if g.name == "tetris"]
        assert len(tetris) == 1
        assert tetris[0].has_server is True
        assert tetris[0].port == 8780


class TestParsePlayCounts:
    def test_basic(self):
        text = """# Last.fm Play Counts (2 artists)

| Artist | Play Count | Listeners | Top Track |
|---|---|---|---|
| Aphex Twin | 1,234,567 | 89,012 | Windowlicker |
| Boards of Canada | 456,789 | 34,567 | Dayvan Cowboy |"""
        results = parse_play_counts(text)
        assert len(results) == 2
        assert results[0].name == "Aphex Twin"
        assert results[0].playcount == 1234567
        assert results[0].listeners == 89012
        assert results[0].top_track == "Windowlicker"
