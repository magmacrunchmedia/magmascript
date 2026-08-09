"""Last.fm domain — Last.fm API client.

Provides a Python client for the Last.fm API with rate limiting,
MBID resolution, and play count fetching.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from magmascript.core.exceptions import MagmascriptError


@dataclass
class ArtistConfig:
    """Artist configuration from play-counts.json."""

    name: str
    mbid: str | None = None
    resolved_name: str | None = None


@dataclass
class TopTrack:
    """A top track from Last.fm."""

    name: str
    playcount: int
    listeners: int


@dataclass
class ArtistPlayCounts:
    """Play count data for an artist from Last.fm."""

    name: str
    mbid: str | None
    fetched_at: str
    stats: dict[str, int]
    top_tracks: list[TopTrack]


@dataclass
class FetchResult:
    """Result of a fetch operation."""

    completed: int
    skipped: int
    resolved: int
    errors: list[str]


class LastFmClient:
    """Last.fm API client with rate limiting and caching.

    Provides methods for fetching play counts and artist data.
    """

    API_BASE = "https://ws.audioscrobbler.com/2.0/"
    DELAY_MS = 250
    TOP_TRACKS_LIMIT = 50
    HISTORY_KEEP = 12

    def __init__(
        self,
        project_root: Path | None = None,
        api_key: str | None = None,
    ):
        """Initialize the Last.fm client.

        Args:
            project_root: Path to the magmacrunch.com project root.
                         Defaults to current working directory.
            api_key: Last.fm API key. If not provided, reads from
                    LASTFM_API_KEY environment variable.
        """
        self._root = project_root or Path.cwd()
        self._cache_dir = self._root / "arcade" / "admin" / "stats" / "lastfm"
        self._history_dir = self._cache_dir / "history"
        self._artists_file = self._root / "scripts" / "play-counts.json"
        self._last_fetch = 0.0
        self._indent = 0

        # Get API key
        import os
        self._api_key = api_key or os.environ.get("LASTFM_API_KEY", "")
        if not self._api_key:
            raise MagmascriptError("LASTFM_API_KEY environment variable is required")

        self._http = httpx.Client(timeout=30.0)

    def _log(self, msg: str) -> None:
        """Log a message with current indentation."""
        print("  " * self._indent + msg)

    def _lastfm_fetch(self, method: str, params: dict[str, str] | None = None) -> Any:
        """Fetch from Last.fm API with rate limiting and retry."""
        # Rate limiting
        now = time.time()
        elapsed = now - self._last_fetch
        if elapsed < self.DELAY_MS / 1000:
            time.sleep((self.DELAY_MS / 1000) - elapsed)
        self._last_fetch = time.time()

        # Build URL
        url = httpx.URL(self.API_BASE, params={
            "api_key": self._api_key,
            "method": method,
            "format": "json",
            **(params or {}),
        })

        # Retry logic
        for attempt in range(4):
            try:
                response = self._http.get(url)
                if response.status_code == 429:
                    wait = 2000 * (attempt + 1)
                    self._log(f"  rate-limited, waiting {wait}ms...")
                    time.sleep(wait / 1000)
                    continue
                response.raise_for_status()
                data = response.json()
                if "error" in data:
                    raise MagmascriptError(f"Last.fm error {data.get('message', 'Unknown error')}")
                return data
            except Exception as e:
                if attempt == 3:
                    raise
                time.sleep(1.5 * (attempt + 1))

    # ------------------------------------------------------------------
    # MBID resolution
    # ------------------------------------------------------------------

    def resolve_mbid(self, artist_name: str) -> tuple[str | None, str] | None:
        """Resolve an artist name to a MusicBrainz ID via Last.fm search.

        Returns:
            Tuple of (mbid, resolved_name) or None if not found.
        """
        self._log(f'  searching Last.fm for "{artist_name}"...')
        data = self._lastfm_fetch("artist.search", {"artist": artist_name})
        results = data.get("results", {}).get("artistmatches", {}).get("artist", [])

        if not results:
            self._log("  no results found")
            return None

        # Pick the best match: prefer exact name, then highest listeners
        exact = next(
            (a for a in results if a.get("name", "").lower() == artist_name.lower()),
            None,
        )
        match = exact or results[0]
        mbid = match.get("mbid") or None
        resolved_name = match.get("name", artist_name)
        self._log(f'  matched: "{resolved_name}" ({match.get("listeners", 0)} listeners, mbid={mbid or "none"})')

        return mbid, resolved_name

    # ------------------------------------------------------------------
    # Fetch artist data
    # ------------------------------------------------------------------

    def fetch_artist(self, artist: ArtistConfig) -> ArtistPlayCounts | None:
        """Fetch play count data for a single artist.

        Args:
            artist: ArtistConfig with name and optional mbid.

        Returns:
            ArtistPlayCounts or None if resolution failed.
        """
        self._log(f"[{artist.name}]")

        # Step 1: resolve name/MBID if needed
        mbid = artist.mbid
        resolved_name = artist.resolved_name or artist.name

        if mbid:
            self._log(f"  using cached mbid: {mbid}")
        else:
            self._indent += 1
            result = self.resolve_mbid(artist.name)
            self._indent -= 1
            if not result:
                self._log("  ⚠ no match found, skipping")
                return None
            mbid, resolved_name = result

        # Step 2: fetch artist info (listeners + playcount)
        self._log("  fetching artist info...")
        info_params = {"mbid": mbid} if mbid else {"artist": resolved_name}
        info = self._lastfm_fetch("artist.getInfo", info_params)
        stats = info.get("artist", {}).get("stats", {})
        listeners = int(stats.get("listeners", 0))
        playcount = int(stats.get("playcount", 0))
        self._log(f"  {listeners:,} listeners, {playcount:,} plays")

        # Step 3: fetch top tracks
        self._log("  fetching top tracks...")
        tracks_params = {"limit": str(self.TOP_TRACKS_LIMIT)}
        if mbid:
            tracks_params["mbid"] = mbid
        else:
            tracks_params["artist"] = resolved_name
        tracks_data = self._lastfm_fetch("artist.getTopTracks", tracks_params)
        tracks = [
            TopTrack(
                name=t.get("name", ""),
                playcount=int(t.get("playcount", 0)),
                listeners=int(t.get("listeners", 0)),
            )
            for t in tracks_data.get("toptracks", {}).get("track", [])
        ]
        self._log(f"  {len(tracks)} top tracks fetched")

        return ArtistPlayCounts(
            name=resolved_name,
            mbid=mbid,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            stats={"listeners": listeners, "playcount": playcount},
            top_tracks=tracks,
        )

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def _save_cache(self, artist_name: str, data: ArtistPlayCounts) -> None:
        """Save artist data to cache file."""
        slug = self._slugify(artist_name)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self._cache_dir / f"{slug}.json"

        # Convert to dict for JSON serialization
        cache_data = {
            "name": data.name,
            "mbid": data.mbid,
            "fetchedAt": data.fetched_at,
            "stats": data.stats,
            "topTracks": [
                {"name": t.name, "playcount": t.playcount, "listeners": t.listeners}
                for t in data.top_tracks
            ],
        }
        cache_file.write_text(json.dumps(cache_data, indent=2), encoding="utf-8")

    def _save_history(self, artist_name: str, data: ArtistPlayCounts) -> None:
        """Save artist data to history directory."""
        today = datetime.now().strftime("%Y-%m-%d")
        slug = self._slugify(artist_name)
        history_dir = self._history_dir / today
        history_dir.mkdir(parents=True, exist_ok=True)
        history_file = history_dir / f"{slug}.json"

        cache_data = {
            "name": data.name,
            "mbid": data.mbid,
            "fetchedAt": data.fetched_at,
            "stats": data.stats,
            "topTracks": [
                {"name": t.name, "playcount": t.playcount, "listeners": t.listeners}
                for t in data.top_tracks
            ],
        }
        history_file.write_text(json.dumps(cache_data, indent=2), encoding="utf-8")

    def _prune_history(self, keep: int | None = None) -> None:
        """Keep only the most recent history snapshots."""
        keep = keep or self.HISTORY_KEEP
        if not self._history_dir.exists():
            return

        dirs = sorted(
            [d.name for d in self._history_dir.iterdir() if d.is_dir() and len(d.name) == 10],
        )

        for old_date in dirs[:-keep]:
            old_dir = self._history_dir / old_date
            import shutil
            shutil.rmtree(old_dir)
            self._log(f"pruned old snapshot: {old_date}")

    def _slugify(self, name: str) -> str:
        """Convert artist name to a filename-safe slug."""
        import re
        slug = name.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")
        return slug

    # ------------------------------------------------------------------
    # Main fetch operation
    # ------------------------------------------------------------------

    def fetch(
        self,
        *,
        dry_run: bool = False,
        skip_existing: bool = False,
    ) -> FetchResult:
        """Fetch play counts for all artists.

        Args:
            dry_run: If True, show what would be done without writing files.
            skip_existing: If True, skip artists that already have cache files.

        Returns:
            FetchResult with counts and any errors.
        """
        self._log("Fetching Last.fm play counts...")
        self._log("")

        # Read artist list
        if not self._artists_file.exists():
            raise MagmascriptError(f"Artists file not found: {self._artists_file}")

        config = json.loads(self._artists_file.read_text(encoding="utf-8"))
        artists = [ArtistConfig(**a) for a in config.get("artists", [])]
        changed = False
        completed = 0
        skipped = 0
        resolved = 0
        errors: list[str] = []

        for artist in artists:
            self._indent = 0

            # Check for existing cache
            slug = self._slugify(artist.name)
            cache_path = self._cache_dir / f"{slug}.json"
            if skip_existing and cache_path.exists():
                self._log(f"[{artist.name}] cached, skipping")
                skipped += 1
                completed += 1
                continue

            try:
                self._indent += 1
                data = self.fetch_artist(artist)
                self._indent -= 1

                if not data:
                    completed += 1
                    continue

                if not dry_run:
                    self._save_cache(artist.name, data)
                    self._save_history(artist.name, data)

                # Update MBID in config if newly resolved
                if not artist.mbid and data.mbid:
                    artist.mbid = data.mbid
                    artist.resolved_name = data.name
                    changed = True
                    resolved += 1
                    self._log(f"  resolved MBID: {data.mbid}")

                completed += 1
            except Exception as e:
                errors.append(f"{artist.name}: {e}")
                completed += 1

        # Save updated config with resolved MBIDs
        if changed and not dry_run:
            config["artists"] = [
                {"name": a.name, "mbid": a.mbid, "resolvedName": a.resolved_name}
                for a in artists
            ]
            self._artists_file.write_text(
                json.dumps(config, indent=2) + "\n",
                encoding="utf-8",
            )
            self._log("Updated play-counts.json with resolved MBIDs")

        if not dry_run:
            self._prune_history()

        self._log("Done.")

        return FetchResult(
            completed=completed,
            skipped=skipped,
            resolved=resolved,
            errors=errors,
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
