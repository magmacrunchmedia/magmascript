"""Scores domain — SSH to Pi to read score files directly.

Bypasses the MCP server — reads JSON files directly via SSH.
Caches results for faster repeated queries.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone

from magmascript.core.cache import CacheStore, get_cache
from magmascript.core.config import Config, get_config
from magmascript.core.exceptions import SSHError
from magmascript.domains.scores.tools import (
    PlayerStats,
    ScoreEntry,
    Scoreboard,
    ScoresReport,
)

SCORES_DIR = "~/arcade/admin/scores"


class ScoresClient:
    """Direct SSH client for reading score files from the Pi.

    Raises SSHError on connection failures.
    Caches results for faster repeated queries.
    """

    def __init__(self, config: Config | None = None):
        cfg = config or get_config()
        self._host = cfg.pi.host
        self._user = cfg.pi.user
        self._cache = get_cache(enabled=cfg.cache.enabled)
        self._cache_ttl = cfg.cache.ttl_scores

    def _ssh(self, cmd: str, *, timeout: int = 15) -> str:
        """Run a command on the Pi via SSH. Returns stdout."""
        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-o", "ConnectTimeout=5",
                    "-o", "StrictHostKeyChecking=no",
                    f"{self._user}@{self._host}",
                    cmd,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0:
                raise SSHError(
                    f"SSH failed (exit {result.returncode}): {result.stderr.strip()}",
                    host=self._host,
                    code=result.returncode,
                )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise SSHError(f"SSH to {self._host} timed out", host=self._host)
        except SSHError:
            raise
        except Exception as e:
            raise SSHError(f"SSH to {self._host} failed: {e}", host=self._host)

    def _read_json(self, filename: str) -> dict:
        """Read and parse a JSON file from the scores directory."""
        stdout = self._ssh(f"cat {SCORES_DIR}/{filename}")
        return json.loads(stdout)

    def _list_files(self) -> list[str]:
        """List all .json files in the scores directory."""
        stdout = self._ssh(f"ls {SCORES_DIR}/*.json 2>/dev/null || true")
        if not stdout:
            return []
        return [f.split("/")[-1] for f in stdout.splitlines()]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_scoreboards(self, *, use_cache: bool = True) -> list[Scoreboard]:
        """List all games with entry counts and top scores."""
        cache_key = CacheStore.make_key("list_scoreboards")
        if use_cache:
            cached = self._cache.get("scores", cache_key)
            if cached is not None:
                return [Scoreboard(**b) for b in cached]

        files = self._list_files()
        boards = []
        for fn in files:
            try:
                data = self._read_json(fn)
                scores = data.get("scores", [])
                top = None
                if scores:
                    s = scores[0]
                    top = ScoreEntry(
                        rank=1,
                        initials=s.get("initials", "?"),
                        score=s.get("score") or s.get("totalScore", 0),
                    )
                boards.append(Scoreboard(
                    game=data.get("game", fn.removesuffix(".json")),
                    game_id=data.get("gameId", fn.removesuffix(".json")),
                    entries=len(scores),
                    top=top,
                ))
            except Exception:
                continue
        result = sorted(boards, key=lambda b: b.game)

        if use_cache:
            self._cache.set("scores", cache_key, [asdict(b) for b in result], ttl=self._cache_ttl)

        return result

    def get_scores(self, game: str, limit: int = 20, *, use_cache: bool = True) -> list[ScoreEntry]:
        """Get leaderboard for a specific game."""
        cache_key = CacheStore.make_key("get_scores", game=game, limit=limit)
        if use_cache:
            cached = self._cache.get("scores", cache_key)
            if cached is not None:
                return [ScoreEntry(**e) for e in cached]

        data = self._read_json(f"{game}.json")
        raw = data.get("scores", [])[:limit]
        entries = []
        for i, s in enumerate(raw, 1):
            entries.append(ScoreEntry(
                rank=i,
                initials=s.get("initials", "?"),
                score=s.get("score") or s.get("totalScore", 0),
                level=s.get("level"),
                difficulty=s.get("difficulty"),
                time=s.get("time"),
                moves=s.get("moves"),
                won=s.get("won"),
                value_reached=s.get("valueReached"),
                timestamp=s.get("timestamp"),
                date=s.get("date"),
                total_score=s.get("totalScore"),
                rounds=s.get("rounds"),
                escaped=s.get("escaped"),
            ))

        if use_cache:
            self._cache.set("scores", cache_key, [asdict(e) for e in entries], ttl=self._cache_ttl)

        return entries

    def report(self) -> ScoresReport:
        """Generate a full scores report across all games."""
        boards = self.list_scoreboards()
        all_entries: dict[str, list] = {}

        for board in boards:
            entries = self.get_scores(board.game_id, limit=100)
            for e in entries:
                if e.initials not in all_entries:
                    all_entries[e.initials] = []
                all_entries[e.initials].append({
                    "game_id": board.game_id,
                    "score": e.score,
                })

        player_stats = []
        for name, plays in sorted(all_entries.items(), key=lambda x: -len(x[1])):
            games = set(p["game_id"] for p in plays)
            player_stats.append(PlayerStats(
                name=name,
                total_entries=len(plays),
                games_played=len(games),
            ))

        total_scores = sum(b.entries for b in boards)
        return ScoresReport(
            generated_at=datetime.now(timezone.utc).strftime("%B %d, %Y"),
            total_games=len(boards),
            total_scores=total_scores,
            scoreboards=boards,
            player_stats=player_stats,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
