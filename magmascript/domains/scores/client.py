"""Scores domain — read score files from the Pi.

Supports both SSH (remote) and local execution modes.
Caches results for faster repeated queries.
"""

from __future__ import annotations

import glob
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from magmascript.core.cache import CacheStore, get_cache
from magmascript.core.config import Config, get_config
from magmascript.core.exceptions import SSHError
from magmascript.core.runner import CommandRunner
from magmascript.domains.scores.tools import (
    DiscordPayload,
    PlayerStats,
    ScoreEntry,
    Scoreboard,
    ScoresReport,
)

SCORES_DIR = "~/arcade/admin/scores"


class ScoresClient:
    """Client for reading score files from the Pi.

    Supports local mode (direct file I/O) and remote mode (SSH).
    Raises SSHError on connection failures.
    Caches results for faster repeated queries.
    """

    def __init__(self, config: Config | None = None, *, local: bool = False):
        cfg = config or get_config()
        self._host = cfg.pi.host
        self._user = cfg.pi.user
        self._local = local
        self._runner = CommandRunner(cfg.pi.host, cfg.pi.user, local=local)
        self._cache = get_cache(enabled=cfg.cache.enabled)
        self._cache_ttl = cfg.cache.ttl_scores

    def _read_json(self, filename: str) -> dict:
        """Read and parse a JSON file from the scores directory."""
        if self._local:
            path = Path(SCORES_DIR).expanduser() / filename
            return json.loads(path.read_text())
        stdout = self._runner.run(f"cat {SCORES_DIR}/{filename}")
        return json.loads(stdout)

    def _list_files(self) -> list[str]:
        """List all .json files in the scores directory."""
        if self._local:
            path = Path(SCORES_DIR).expanduser()
            if not path.is_dir():
                return []
            return [f.name for f in sorted(path.glob("*.json"))]
        stdout = self._runner.run(f"ls {SCORES_DIR}/*.json 2>/dev/null || true")
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

    def report_discord(self) -> DiscordPayload:
        """Generate a Discord embed payload for high scores."""
        report = self.report()
        medals = ["🥇", "🥈", "🥉"]
        fields = []

        for board in report.scoreboards:
            entries = self.get_scores(board.game_id, limit=5)
            if not entries:
                value = "*No scores yet*"
            else:
                value_lines = []
                for i, e in enumerate(entries):
                    rank = medals[i] if i < 3 else f"{i + 1}."
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
                    value_lines.append(f"{rank} **{e.initials}** — {' · '.join(parts)}")
                value = "\n".join(value_lines)

            fields.append({"name": board.game, "value": value, "inline": True})

        footer_parts = [f"{report.total_games} games", f"{report.total_scores} scores"]
        if report.player_stats:
            footer_parts.append(f"{len(report.player_stats)} players")

        return DiscordPayload(
            embeds=[{
                "title": f"Weekly High Scores — {report.generated_at}",
                "fields": fields,
                "footer": {"text": " · ".join(footer_parts)},
                "color": 0xFF3D6E,
            }],
            footer_text=" · ".join(footer_parts),
        )

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def reset(self, game_id: str) -> str:
        """Reset scores for one game. Creates a timestamped backup first.

        Args:
            game_id: Game ID (e.g. "tetris", "george-boole")
        """
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_dir = f"{SCORES_DIR}/backup"

        if self._local:
            scores_path = Path(SCORES_DIR).expanduser() / f"{game_id}.json"
            backup_path = Path(backup_dir).expanduser()
            backup_path.mkdir(parents=True, exist_ok=True)
            if scores_path.exists():
                import shutil
                shutil.copy2(scores_path, backup_path / f"{game_id}-{ts}.json")
            scores_path.write_text(json.dumps({"game": game_id, "scores": []}))
        else:
            self._runner.run(
                f"mkdir -p {backup_dir} && "
                f"cp {SCORES_DIR}/{game_id}.json {backup_dir}/{game_id}-{ts}.json && "
                f'echo \'{{"game":"{game_id}","scores":[]}}\' > {SCORES_DIR}/{game_id}.json'
            )
        # Clear cache so next read reflects the reset
        self._cache.clear(domain="scores")
        return f"✓ Reset {game_id} (backup: {game_id}-{ts}.json)"

    def reset_all(self) -> str:
        """Reset all game scores. Creates timestamped backups for each."""
        files = self._list_files()
        if not files:
            return "No score files found"

        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_dir = f"{SCORES_DIR}/backup"
        reset_games = []

        if self._local:
            import shutil
            backup_path = Path(backup_dir).expanduser()
            backup_path.mkdir(parents=True, exist_ok=True)
            for fn in files:
                game_id = fn.removesuffix(".json")
                try:
                    src = Path(SCORES_DIR).expanduser() / fn
                    shutil.copy2(src, backup_path / f"{game_id}-{ts}.json")
                    src.write_text(json.dumps({"game": game_id, "scores": []}))
                    reset_games.append(game_id)
                except Exception:
                    continue
        else:
            for fn in files:
                game_id = fn.removesuffix(".json")
                try:
                    self._runner.run(
                        f"mkdir -p {backup_dir} && "
                        f"cp {SCORES_DIR}/{fn} {backup_dir}/{game_id}-{ts}.json && "
                        f'echo \'{{"game":"{game_id}","scores":[]}}\' > {SCORES_DIR}/{fn}'
                    )
                    reset_games.append(game_id)
                except SSHError:
                    continue

        self._cache.clear(domain="scores")
        return f"✓ Reset {len(reset_games)} games: {', '.join(reset_games)}"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
