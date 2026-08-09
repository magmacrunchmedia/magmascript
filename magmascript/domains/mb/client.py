"""MusicBrainz domain — MusicBrainz API client.

Provides a Python client for the MusicBrainz API with rate limiting,
caching, and entity-specific backup functionality.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from magmascript.core.exceptions import MagmascriptError


@dataclass
class Entity:
    """A MusicBrainz entity (artist, place, etc.)."""

    name: str
    uuid: str | None = None
    slug: str | None = None
    ids: list[str] | None = None


@dataclass
class BackupResult:
    """Result of a backup operation."""

    completed: int
    skipped: int
    elapsed_seconds: int
    errors: list[str]


class MusicBrainzClient:
    """MusicBrainz API client with rate limiting and caching.

    Provides methods for fetching and caching MusicBrainz data.
    """

    API_BASE = "https://musicbrainz.org/ws/2"
    DELAY_MS = 1100
    STALE_DAYS = 30
    MAX_SNAPSHOTS = 4

    # Entity definitions
    ARTISTS = [
        Entity(name="DDT LLC", uuid="0335c576-94a4-4adb-a323-6effff5914e0"),
        Entity(name="woah", uuid="0cb54a5f-3c60-4635-abb3-e6bc60fa7d9f"),
        Entity(name="SVFP", uuid="260e4953-a937-4355-8389-d1baaf24eca5"),
        Entity(name="Jon McCoy", uuid="33c830f0-d5be-4baf-b8db-3dc754e74c16"),
        Entity(name="C.P. Rutledge", uuid="44c1e0bd-be4c-4a0b-8f06-864c8e2fedcc"),
        Entity(name="THLD", uuid="4d945923-9deb-4cd0-a477-6e1474cb306c"),
        Entity(name="Dino Spumoni", uuid="5b954c0a-1375-40de-ae5f-a245e4f942c6"),
        Entity(name="Dag Henderson", uuid="605cc914-2aff-4e2b-9657-524c7009cb18"),
        Entity(name="The Four Bs", uuid="bdf6e0d0-6886-4801-b7ce-c9ced5d377a8"),
        Entity(name="Juanito Thompson", uuid="ddcbeb01-edb5-4e74-b5cd-23d1b64d3086"),
        Entity(name="Bottle Boys Collective", uuid="e33d1006-01a5-4266-aade-b7f6c1dff8e3"),
    ]

    PLACES = [
        Entity(name="Green St. Apt", uuid="1fc551c6-d3d5-43d0-a3bb-9e5606bdbebe"),
        Entity(name="Irvin House", uuid="26cbb244-48c7-49e5-863c-5dde5388dde1"),
        Entity(name="Frogwood Manor", uuid="362e9df6-ce39-4805-841e-c113e4e2a7c9"),
        Entity(name="The Tuna Can", uuid="3ecebfcc-6824-46a9-9e1a-ecc26f69a4a2"),
        Entity(name="College Green Apt", uuid="c6c69d44-8408-4a0a-9dbf-8b3ee903bc5f"),
        Entity(name="Marvin Gardens G12", uuid="d8a1b49b-3573-4117-ae93-794816c57d4d"),
        Entity(name="Twin Maples", uuid="e697fa03-e300-421a-8fd3-3b026d8d4f13"),
        Entity(name="Melrose House", uuid="f30be60e-94b4-465a-8e75-8cbdefaffbc8"),
    ]

    CONTRIBUTORS = [
        Entity(name="Jake McCoy", uuid="32bc1ac7-efd0-44f2-8645-8fecf6a40edb"),
        Entity(name="Judah Unmuth-Yockey", uuid="054fd43c-d028-42d6-8857-20f7d2d0bd0a"),
        Entity(name="Ben Nikitas", uuid="03a5593d-7cb7-4e22-9f1f-a1ce216ee972"),
        Entity(name="David Hayes", uuid="94a0d47c-5c34-4552-838d-c006b2a0d83b"),
        Entity(name="Alex S.", uuid="0bfa85f1-5138-4790-8439-e709399944df"),
        Entity(name="Chuck J'OB", uuid="c8ba82bf-cfa1-49a0-98bf-0cf8f931099f"),
        Entity(name="D. Rob Robinson", uuid="8b0a17a4-fb29-49b4-82e2-2e50e0be50fd"),
        Entity(name="James McCoy", uuid="d0a8ae01-3443-42da-b258-490300f1249c"),
        Entity(name="Elias Grey", uuid="aa5ccc77-a82e-465e-a9d5-79cf4098a926"),
        Entity(name="Jake Thomas", uuid="a492cd5d-b090-48e3-8bbb-0f8f5cefc34a"),
        Entity(name="Stephen McMillan", uuid="205acdc4-99a4-4f91-bf6d-43a7f1f8028e"),
        Entity(name="Rho K.", uuid="b0d4d4fd-d500-4439-b401-5c15f231e41f"),
        Entity(name="Rob Tomer", uuid="9b9aaa44-76da-4745-8bdb-b5869c9301b3"),
    ]

    LABELS = [
        Entity(name="magmacrunch music", uuid="c78b5612-2300-4ee1-8663-299ddcf9ce25"),
        Entity(name="The Slop Collective", uuid="ad82d124-e41e-49e8-9bf9-53e836b44336"),
        Entity(name="magmacrunch media", uuid="39446d03-fe9c-47d0-81a9-2b42d34fb400"),
        Entity(name="magmacrunch arcade", uuid="1d3190cc-b700-4409-bdb4-2ee8b93f3d8c"),
    ]

    WORKS = [
        Entity(name="pay2play", uuid="b5d8ec34-e488-4e94-8aa7-af05136e9322"),
        Entity(name="try", uuid="e31f5986-649d-42f2-9f02-54989b12957c"),
        Entity(name="starting again", uuid="4c19c4b8-e84d-4e7a-8be0-db3600a03aa6"),
        Entity(name="gone by", uuid="b8717e83-8f30-4a37-b681-834a99f11110"),
        Entity(name="space", uuid="4952512f-3d3f-48af-934f-222ebdfcdb4e"),
        Entity(name="somewhere", uuid="27b2fa99-1404-4f12-b9c8-5fe7e90a1769"),
        Entity(name="i only feel the rain", uuid="8b195014-6814-4293-9363-b7e838f348ca"),
        Entity(name="contemplate the plate tectonic", uuid="9143547e-3632-4835-b78c-0751cbb713d3"),
    ]

    COLLECTIVES = [
        Entity(
            name="texas hold'em lava dome, et al.",
            slug="thld",
            ids=[
                "4d945923-9deb-4cd0-a477-6e1474cb306c",
                "e1e53b08-af12-4d5a-8508-c620d5279ba3",
                "30d9cd20-3f5c-4a83-b13b-58ba8c690e2e",
            ],
        ),
        Entity(
            name="Audio Sound Paper, et al.",
            slug="audio-sound-paper-et-al",
            ids=[
                "76708e20-5d88-4699-adf6-a1f2118ef661",
                "0296c377-7f97-4099-9c83-e2edb5552eda",
                "5c860d63-acfa-4584-82db-4a76339b2f1e",
                "8b11928f-4013-4ac9-a39b-826bbc01b25c",
            ],
        ),
        Entity(
            name="Vinny Bobarino, et al.",
            slug="vinny-bobarino",
            ids=[
                "f701c2bc-6eb6-4e7b-b950-f0c2426cb91c",
                "856f7f94-8c21-49cb-9364-e1f7b429f9ef",
                "246bff13-d203-4879-a22b-9ad6b5ddae7c",
                "d9179190-dcf2-469e-b4c8-3624b97dc11a",
            ],
        ),
        Entity(
            name="Fruity Loops Debauchery Bros.",
            slug="fruity-loops-debauchery-collective",
            ids=[
                "b7846e25-306e-4ca9-8db1-0391ab159a36",
                "ce22522c-1193-4298-badf-0df5cdfa0415",
                "3c3bc6e8-9d72-457f-a192-b6ef263fe4ae",
            ],
        ),
    ]

    def __init__(self, project_root: Path | None = None):
        """Initialize the MusicBrainz client.

        Args:
            project_root: Path to the magmacrunch.com project root.
                         Defaults to current working directory.
        """
        self._root = project_root or Path.cwd()
        self._cache_dir = self._root / "archive" / "_cache"
        self._snapshots_dir = self._cache_dir / "snapshots"
        self._last_fetch = 0.0
        self._indent = 0
        self._http = httpx.Client(
            headers={"User-Agent": "magmacrunch-backup/1.0 (https://magmacrunch.com)"},
            timeout=30.0,
        )

    def _log(self, msg: str) -> None:
        """Log a message with current indentation."""
        print("  " * self._indent + msg)

    def _log_entity(self, entity_type: str, name: str) -> None:
        """Log an entity being processed."""
        self._log(f"[{entity_type}] {name}")

    async def _fetch_mb(self, path: str) -> Any:
        """Fetch from MusicBrainz API with rate limiting and retry."""
        import time
        import asyncio

        # Rate limiting
        now = time.time()
        elapsed = now - self._last_fetch
        if elapsed < self.DELAY_MS / 1000:
            await asyncio.sleep((self.DELAY_MS / 1000) - elapsed)
        self._last_fetch = time.time()

        # Build URL
        url = path if path.startswith("http") else f"{self.API_BASE}/{path}"

        # Retry logic
        for attempt in range(4):
            try:
                response = self._http.get(url)
                if response.status_code in (429, 503):
                    wait = 2000 * (attempt + 1)
                    self._log(f"  rate-limited ({response.status_code}), waiting {wait}ms...")
                    await asyncio.sleep(wait / 1000)
                    continue
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if attempt == 3:
                    raise
                await asyncio.sleep(1.5 * (attempt + 1))

    def _fetch_mb_sync(self, path: str) -> Any:
        """Synchronous version of _fetch_mb for use in non-async contexts."""
        import time

        # Rate limiting
        now = time.time()
        elapsed = now - self._last_fetch
        if elapsed < self.DELAY_MS / 1000:
            time.sleep((self.DELAY_MS / 1000) - elapsed)
        self._last_fetch = time.time()

        # Build URL
        url = path if path.startswith("http") else f"{self.API_BASE}/{path}"

        # Retry logic
        for attempt in range(4):
            try:
                response = self._http.get(url)
                if response.status_code in (429, 503):
                    wait = 2000 * (attempt + 1)
                    self._log(f"  rate-limited ({response.status_code}), waiting {wait}ms...")
                    time.sleep(wait / 1000)
                    continue
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if attempt == 3:
                    raise
                time.sleep(1.5 * (attempt + 1))

    # ------------------------------------------------------------------
    # Cache operations
    # ------------------------------------------------------------------

    def _write_cache(self, entity_type: str, key: str, data: dict) -> None:
        """Write data to cache file with snapshot backup."""
        cache_dir = self._cache_dir / entity_type
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{key}.json"

        # Snapshot existing cache before overwriting
        self._snapshot_cache(entity_type, key)

        # Write atomically using temp file
        tmp_file = cache_file.with_suffix(".json.tmp")
        tmp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_file.rename(cache_file)

        size_kb = len(json.dumps(data)) / 1024
        self._log(f"  cached {size_kb:.1f} KB → {entity_type}/{key}.json")

    def _snapshot_cache(self, entity_type: str, key: str) -> None:
        """Create a timestamped snapshot of a cache file."""
        cache_file = self._cache_dir / entity_type / f"{key}.json"
        if not cache_file.exists():
            return

        date_str = datetime.now().strftime("%Y-%m-%d")
        snap_dir = self._snapshots_dir / date_str / entity_type
        snap_dir.mkdir(parents=True, exist_ok=True)
        dest = snap_dir / f"{key}.json"

        if dest.exists():
            return  # already snapshotted today

        shutil.copy2(cache_file, dest)
        self._log(f"  snapshotted → snapshots/{date_str}/{entity_type}/{key}.json")

    def _clean_old_snapshots(self) -> None:
        """Keep only the last MAX_SNAPSHOTS snapshot dates."""
        if not self._snapshots_dir.exists():
            return

        dates = sorted(
            [d.name for d in self._snapshots_dir.iterdir() if d.is_dir() and len(d.name) == 10],
            reverse=True,
        )

        for old_date in dates[self.MAX_SNAPSHOTS:]:
            old_dir = self._snapshots_dir / old_date
            shutil.rmtree(old_dir)
            self._log(f"  cleaned old snapshot: {old_date}")

    def _cache_exists(self, entity_type: str, key: str) -> bool:
        """Check if a cache file exists."""
        return (self._cache_dir / entity_type / f"{key}.json").exists()

    def _cache_is_stale(self, entity_type: str, key: str) -> bool:
        """Check if a cache file is older than STALE_DAYS."""
        cache_file = self._cache_dir / entity_type / f"{key}.json"
        if not cache_file.exists():
            return True
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            fetched_at = data.get("fetchedAt")
            if not fetched_at:
                return True
            fetched_dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - fetched_dt
            return age > timedelta(days=self.STALE_DAYS)
        except Exception:
            return True

    # ------------------------------------------------------------------
    # Backup operations
    # ------------------------------------------------------------------

    def backup(
        self,
        *,
        dry_run: bool = False,
        skip_existing: bool = False,
        stale_only: bool = False,
    ) -> BackupResult:
        """Run full MusicBrainz backup for all entities.

        Args:
            dry_run: If True, show what would be done without writing files.
            skip_existing: If True, skip entities that already have cache files.
            stale_only: If True, only refresh caches older than STALE_DAYS.

        Returns:
            BackupResult with counts and elapsed time.
        """
        import time

        start = time.time()
        completed = 0
        skipped = 0
        errors: list[str] = []

        if dry_run:
            print("[DRY RUN — no files will be written]\n")
        if stale_only:
            print(f"[STALE ONLY — only refreshing caches older than {self.STALE_DAYS} days]\n")
        elif skip_existing:
            print("[SKIP EXISTING — already-cached entities will be skipped]\n")

        # Process each entity type
        for entity in self.ARTISTS:
            if self._should_skip(entity.uuid, "artists", stale_only, skip_existing):
                completed += 1
                skipped += 1
                continue
            try:
                self._backup_artist(entity, dry_run)
                completed += 1
            except Exception as e:
                errors.append(f"artist {entity.name}: {e}")
                completed += 1

        for entity in self.PLACES:
            if self._should_skip(entity.uuid, "places", stale_only, skip_existing):
                completed += 1
                skipped += 1
                continue
            try:
                self._backup_place(entity, dry_run)
                completed += 1
            except Exception as e:
                errors.append(f"place {entity.name}: {e}")
                completed += 1

        for entity in self.CONTRIBUTORS:
            if self._should_skip(entity.uuid, "contributors", stale_only, skip_existing):
                completed += 1
                skipped += 1
                continue
            try:
                self._backup_contributor(entity, dry_run)
                completed += 1
            except Exception as e:
                errors.append(f"contributor {entity.name}: {e}")
                completed += 1

        for entity in self.LABELS:
            if self._should_skip(entity.uuid, "labels", stale_only, skip_existing):
                completed += 1
                skipped += 1
                continue
            try:
                self._backup_label(entity, dry_run)
                completed += 1
            except Exception as e:
                errors.append(f"label {entity.name}: {e}")
                completed += 1

        for entity in self.WORKS:
            if self._should_skip(entity.uuid, "works", stale_only, skip_existing):
                completed += 1
                skipped += 1
                continue
            try:
                self._backup_work(entity, dry_run)
                completed += 1
            except Exception as e:
                errors.append(f"work {entity.name}: {e}")
                completed += 1

        for entity in self.COLLECTIVES:
            key = entity.slug or entity.uuid
            if self._should_skip(key, "collectives", stale_only, skip_existing):
                completed += 1
                skipped += 1
                continue
            try:
                self._backup_collective(entity, dry_run)
                completed += 1
            except Exception as e:
                errors.append(f"collective {entity.name}: {e}")
                completed += 1

        elapsed = int(time.time() - start)
        min_str = elapsed // 60
        sec_str = elapsed % 60
        print(f"\nDone! {completed - skipped} entities backed up, {skipped} skipped in {min_str}m {sec_str}s")
        if dry_run:
            print("(dry run — no files were written)")

        # Clean old snapshots
        if not dry_run:
            self._clean_old_snapshots()

        return BackupResult(
            completed=completed,
            skipped=skipped,
            elapsed_seconds=elapsed,
            errors=errors,
        )

    def _should_skip(self, key: str, entity_type: str, stale_only: bool, skip_existing: bool) -> bool:
        """Determine if an entity should be skipped."""
        if stale_only and not self._cache_is_stale(entity_type, key):
            self._log(f"[{entity_type}] {key} — cache is fresh, skipping")
            return True
        if not stale_only and skip_existing and self._cache_exists(entity_type, key):
            self._log(f"[{entity_type}] {key} — already cached, skipping")
            return True
        return False

    def _backup_artist(self, entity: Entity, dry_run: bool) -> None:
        """Backup a single artist entity."""
        self._log_entity("artist", entity.name)
        self._indent += 1

        cache = {
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
            "entityType": "artist",
            "uuid": entity.uuid,
            "name": entity.name,
            "subpages": {},
        }

        cache["subpages"]["events"] = self._backup_artist_events(entity.uuid)
        cache["subpages"]["releases"] = self._backup_artist_releases(entity.uuid)
        cache["subpages"]["recordings"] = self._backup_artist_recordings(entity.uuid)
        cache["subpages"]["works"] = self._backup_artist_works(entity.uuid)
        cache["subpages"]["members"] = self._backup_artist_members(entity.uuid)

        self._indent -= 1
        if not dry_run:
            self._write_cache("artists", entity.uuid, cache)

    def _backup_artist_events(self, uuid: str) -> dict:
        """Backup artist events."""
        self._log("  events...")

        # Paginated list
        all_events = []
        offset = 0
        while True:
            data = self._fetch_mb_sync(f"event?artist={uuid}&limit=100&offset={offset}&fmt=json")
            events = data.get("events", [])
            all_events.extend(events)
            if len(events) < 100:
                break
            offset += 100
            import time
            time.sleep(1)

        cache = {"list": {"event-count": len(all_events), "events": all_events}, "details": {}, "areaChains": {}}

        # Detail for each event
        for i, event in enumerate(all_events):
            self._log(f"  event detail {i + 1}/{len(all_events)}: {event['name']}")
            detail = self._fetch_mb_sync(f"event/{event['id']}?inc=place-rels+artist-rels&fmt=json")
            cache["details"][event["id"]] = detail

            # Pre-resolve area chains for places
            place_rel = next((r for r in detail.get("relations", []) if r.get("type") == "held at"), None)
            area_id = place_rel.get("place", {}).get("area", {}).get("id") if place_rel else None
            if area_id and area_id not in cache["areaChains"]:
                try:
                    names = []
                    seen = set()
                    current_id = area_id
                    while current_id and current_id not in seen:
                        seen.add(current_id)
                        area_data = self._fetch_mb_sync(f"area/{current_id}?inc=area-rels&fmt=json")
                        if area_data.get("name") and area_data.get("type") != "County":
                            names.append(area_data["name"])
                        if area_data.get("type") == "Country" or len(names) >= 4:
                            break
                        part_of = next(
                            (r for r in area_data.get("relations", []) if r.get("type") == "part of" and r.get("target-type") == "area"),
                            None,
                        )
                        current_id = part_of.get("area", {}).get("id") if part_of else None
                    cache["areaChains"][area_id] = ", ".join(names)
                except Exception:
                    cache["areaChains"][area_id] = ""

        return cache

    def _backup_artist_releases(self, uuid: str) -> dict:
        """Backup artist releases."""
        self._log("  releases...")

        all_releases = []
        offset = 0
        while True:
            data = self._fetch_mb_sync(f"release?artist={uuid}&limit=100&offset={offset}&fmt=json")
            releases = data.get("releases", [])
            all_releases.extend(releases)
            if len(releases) < 100:
                break
            offset += 100
            import time
            time.sleep(1)

        cache = {"list": {"release-count": len(all_releases), "releases": all_releases}, "details": {}, "releaseGroups": {}}

        for i, release in enumerate(all_releases):
            self._log(f"  release detail {i + 1}/{len(all_releases)}: {release['title']}")
            detail = self._fetch_mb_sync(f"release/{release['id']}?inc=artists+labels+recordings+release-groups&fmt=json")
            cache["details"][release["id"]] = detail

            # Fetch release group if available
            rg_id = detail.get("release-group", {}).get("id")
            if rg_id and rg_id not in cache["releaseGroups"]:
                try:
                    rg = self._fetch_mb_sync(f"release-group/{rg_id}?inc=tags&fmt=json")
                    cache["releaseGroups"][rg_id] = rg
                except Exception:
                    pass

        return cache

    def _backup_artist_recordings(self, uuid: str) -> dict:
        """Backup artist recordings."""
        self._log("  recordings...")

        all_recordings = []
        offset = 0
        while True:
            data = self._fetch_mb_sync(f"recording?artist={uuid}&limit=100&offset={offset}&fmt=json")
            recordings = data.get("recordings", [])
            all_recordings.extend(recordings)
            if len(recordings) < 100:
                break
            offset += 100
            import time
            time.sleep(1)

        cache = {"list": {"recordings": all_recordings}, "details": {}}

        for i, recording in enumerate(all_recordings):
            self._log(f"  recording detail {i + 1}/{len(all_recordings)}: {recording['title']}")
            cache["details"][recording["id"]] = self._fetch_mb_sync(
                f"recording/{recording['id']}?inc=artists+isrcs+tags+artist-rels+place-rels+releases+work-rels+aliases+recording-rels&fmt=json"
            )

        return cache

    def _backup_artist_works(self, uuid: str) -> dict:
        """Backup artist works."""
        self._log("  works...")

        artist_data = self._fetch_mb_sync(f"artist/{uuid}?inc=work-rels&fmt=json")
        cache = {"artistWorkRels": artist_data, "details": {}, "recordingFlags": {}}

        work_rels = [r for r in artist_data.get("relations", []) if r.get("target-type") == "work"]
        seen = set()

        for rel in work_rels:
            work_id = rel.get("work", {}).get("id")
            if not work_id or work_id in seen:
                continue
            seen.add(work_id)
            self._log(f"  work detail {len(seen)}/{len(work_rels)}: {rel.get('work', {}).get('title')}")

            work_data = self._fetch_mb_sync(f"work/{work_id}?inc=artist-rels+label-rels+url-rels+place-rels+tags+work-rels+aliases+recording-rels&fmt=json")
            cache["details"][work_id] = work_data

            # Pre-fetch recording flags
            rec_rels = [r for r in work_data.get("relations", []) if r.get("target-type") == "recording" and r.get("type") == "performance"]
            for rec_rel in rec_rels:
                rec_id = rec_rel.get("recording", {}).get("id")
                if not rec_id or rec_id in cache["recordingFlags"]:
                    continue
                try:
                    rec_data = self._fetch_mb_sync(f"recording/{rec_id}?fmt=json")
                    cache["recordingFlags"][rec_id] = {"video": rec_data.get("video", False), "disambiguation": rec_data.get("disambiguation", "")}
                except Exception:
                    cache["recordingFlags"][rec_id] = {"video": False, "disambiguation": ""}

        return cache

    def _backup_artist_members(self, uuid: str) -> dict:
        """Backup artist members."""
        self._log("  members...")

        data = self._fetch_mb_sync(f"artist/{uuid}?inc=artist-rels&fmt=json")
        cache = {"main": data, "subgroups": {}}

        subgroups = [
            r for r in data.get("relations", [])
            if r.get("target-type") == "artist" and r.get("artist") and r.get("type") == "subgroup"
        ]

        for sg in subgroups:
            self._log(f"  subgroup: {sg['artist']['name']}")
            cache["subgroups"][sg["artist"]["id"]] = self._fetch_mb_sync(f"artist/{sg['artist']['id']}?inc=artist-rels&fmt=json")

        return cache

    def _backup_place(self, entity: Entity, dry_run: bool) -> None:
        """Backup a single place entity."""
        self._log_entity("place", entity.name)
        self._indent += 1

        cache = {
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
            "entityType": "place",
            "uuid": entity.uuid,
            "name": entity.name,
            "subpages": {},
        }

        cache["subpages"]["events"] = self._backup_place_events(entity.uuid)
        cache["subpages"]["recordings"] = self._backup_place_recordings(entity.uuid)
        cache["subpages"]["works"] = self._backup_place_works(entity.uuid)
        cache["subpages"]["personnel"] = self._backup_place_personnel(entity.uuid)

        self._indent -= 1
        if not dry_run:
            self._write_cache("places", entity.uuid, cache)

    def _backup_place_events(self, uuid: str) -> dict:
        """Backup place events."""
        self._log("  events...")

        all_events = []
        offset = 0
        while True:
            data = self._fetch_mb_sync(f"event?place={uuid}&limit=100&offset={offset}&fmt=json")
            events = data.get("events", [])
            all_events.extend(events)
            if len(events) < 100:
                break
            offset += 100
            import time
            time.sleep(1)

        cache = {"list": {"event-count": len(all_events), "events": all_events}, "details": {}}

        for i, event in enumerate(all_events):
            self._log(f"  event detail {i + 1}/{len(all_events)}: {event['name']}")
            cache["details"][event["id"]] = self._fetch_mb_sync(f"event/{event['id']}?inc=place-rels+artist-rels&fmt=json")

        return cache

    def _backup_place_recordings(self, uuid: str) -> dict:
        """Backup place recordings."""
        self._log("  recordings...")

        place_data = self._fetch_mb_sync(f"place/{uuid}?inc=recording-rels&fmt=json")
        cache = {"placeData": place_data, "details": {}}

        rec_rels = [r for r in place_data.get("relations", []) if r.get("target-type") == "recording"]
        seen = {}
        for rel in rec_rels:
            rec_id = rel.get("recording", {}).get("id")
            if rec_id and rec_id not in seen:
                seen[rec_id] = rel

        for i, rec_id in enumerate(seen):
            self._log(f"  recording detail {i + 1}/{len(seen)}")
            cache["details"][rec_id] = self._fetch_mb_sync(
                f"recording/{rec_id}?inc=artists+isrcs+tags+artist-rels+place-rels+releases+work-rels+aliases+recording-rels&fmt=json"
            )

        return cache

    def _backup_place_works(self, uuid: str) -> dict:
        """Backup place works."""
        self._log("  works...")

        place_data = self._fetch_mb_sync(f"place/{uuid}?inc=work-rels&fmt=json")
        cache = {"placeData": place_data, "details": {}, "recordingFlags": {}}

        work_rels = [r for r in place_data.get("relations", []) if r.get("target-type") == "work"]
        seen = set()

        for rel in work_rels:
            work_id = rel.get("work", {}).get("id")
            if not work_id or work_id in seen:
                continue
            seen.add(work_id)
            self._log(f"  work detail {len(seen)}/{len(work_rels)}: {rel.get('work', {}).get('title')}")

            work_data = self._fetch_mb_sync(f"work/{work_id}?inc=artist-rels+label-rels+url-rels+place-rels+tags+work-rels+aliases+recording-rels&fmt=json")
            cache["details"][work_id] = work_data

            rec_rels = [r for r in work_data.get("relations", []) if r.get("target-type") == "recording" and r.get("type") == "performance"]
            for rec_rel in rec_rels:
                rec_id = rec_rel.get("recording", {}).get("id")
                if not rec_id or rec_id in cache["recordingFlags"]:
                    continue
                try:
                    rec_data = self._fetch_mb_sync(f"recording/{rec_id}?fmt=json")
                    cache["recordingFlags"][rec_id] = {"video": rec_data.get("video", False), "disambiguation": rec_data.get("disambiguation", "")}
                except Exception:
                    cache["recordingFlags"][rec_id] = {"video": False, "disambiguation": ""}

        return cache

    def _backup_place_personnel(self, uuid: str) -> dict:
        """Backup place personnel."""
        self._log("  personnel...")

        place_data = self._fetch_mb_sync(f"place/{uuid}?inc=artist-rels&fmt=json")
        cache = {"placeData": place_data, "details": {}}

        artist_rels = [r for r in place_data.get("relations", []) if r.get("target-type") == "artist"]
        seen = set()

        for rel in artist_rels:
            artist_id = rel.get("artist", {}).get("id")
            if not artist_id or artist_id in seen:
                continue
            seen.add(artist_id)
            self._log(f"  artist detail {len(seen)}/{len(artist_rels)}: {rel.get('artist', {}).get('name')}")

            cache["details"][artist_id] = self._fetch_mb_sync(
                f"artist/{artist_id}?inc=artist-rels+label-rels+url-rels+place-rels+tags+work-rels+aliases+recording-rels+release-groups&fmt=json"
            )

        return cache

    def _backup_contributor(self, entity: Entity, dry_run: bool) -> None:
        """Backup a single contributor entity."""
        self._log_entity("contributor", entity.name)
        self._indent += 1

        cache = {
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
            "entityType": "contributor",
            "uuid": entity.uuid,
            "name": entity.name,
            "responses": {},
        }

        inc_params = ["artist-rels", "recording-rels", "work-rels", "release-rels", "label-rels", "place-rels", "event-rels"]
        for inc in inc_params:
            self._log(f"  {inc}...")
            cache["responses"][inc] = self._fetch_mb_sync(f"artist/{entity.uuid}?fmt=json&inc={inc}")

        self._indent -= 1
        if not dry_run:
            self._write_cache("contributors", entity.uuid, cache)

    def _backup_label(self, entity: Entity, dry_run: bool) -> None:
        """Backup a single label entity."""
        self._log_entity("label", entity.name)
        self._indent += 1

        cache = {
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
            "entityType": "label",
            "uuid": entity.uuid,
            "name": entity.name,
            "responses": {},
        }

        inc_params = ["artist-rels", "label-rels", "event-rels", "recording-rels", "work-rels", "release-rels"]
        for inc in inc_params:
            self._log(f"  {inc}...")
            cache["responses"][inc] = self._fetch_mb_sync(f"label/{entity.uuid}?fmt=json&inc={inc}")

        self._indent -= 1
        if not dry_run:
            self._write_cache("labels", entity.uuid, cache)

    def _backup_work(self, entity: Entity, dry_run: bool) -> None:
        """Backup a single work entity."""
        self._log_entity("work", entity.name)
        self._indent += 1

        cache = {
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
            "entityType": "work",
            "uuid": entity.uuid,
            "name": entity.name,
            "data": None,
            "recordings": {},
        }

        self._log("  work detail...")
        cache["data"] = self._fetch_mb_sync(f"work/{entity.uuid}?inc=artist-rels+recording-rels+place-rels+tags+aliases&fmt=json")

        # Fetch recording details
        rec_rels = [r for r in cache["data"].get("relations", []) if r.get("target-type") == "recording" and r.get("type") == "performance"]
        for rec_rel in rec_rels:
            rec_id = rec_rel.get("recording", {}).get("id")
            if not rec_id or rec_id in cache["recordings"]:
                continue
            self._log(f"  recording: {rec_rel.get('recording', {}).get('title')}")
            try:
                cache["recordings"][rec_id] = self._fetch_mb_sync(f"recording/{rec_id}?inc=releases+place-rels+event-rels&fmt=json")
            except Exception:
                cache["recordings"][rec_id] = None

        self._indent -= 1
        if not dry_run:
            self._write_cache("works", entity.uuid, cache)

    def _backup_collective(self, entity: Entity, dry_run: bool) -> None:
        """Backup a collective entity."""
        self._log_entity("collective", entity.name)
        self._indent += 1

        cache = {
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
            "entityType": "collective",
            "slug": entity.slug,
            "name": entity.name,
            "ids": entity.ids,
            "works": {"artistWorkRels": None, "details": {}, "recordingFlags": {}},
            "recordings": {"list": [], "details": {}},
            "releases": {"list": [], "details": {}, "releaseGroups": {}},
        }

        # Works
        self._log("works...")
        all_work_rels = []
        work_seen = set()
        for artist_id in (entity.ids or []):
            self._log(f"  work-rels for {artist_id[:8]}...")
            artist_data = self._fetch_mb_sync(f"artist/{artist_id}?inc=work-rels&fmt=json")
            rels = [r for r in artist_data.get("relations", []) if r.get("target-type") == "work"]
            for rel in rels:
                wid = rel.get("work", {}).get("id")
                if wid and wid not in work_seen:
                    work_seen.add(wid)
                    all_work_rels.append(rel)

        cache["works"]["artistWorkRels"] = {"relations": all_work_rels}

        for rel in all_work_rels:
            work_id = rel.get("work", {}).get("id")
            if not work_id:
                continue
            self._log(f"  work detail {work_id[:8]}: {rel.get('work', {}).get('title')}")
            work_data = self._fetch_mb_sync(f"work/{work_id}?inc=artist-rels+label-rels+url-rels+place-rels+tags+work-rels+aliases+recording-rels&fmt=json")
            cache["works"]["details"][work_id] = work_data

            rec_rels = [r for r in work_data.get("relations", []) if r.get("target-type") == "recording" and r.get("type") == "performance"]
            for rec_rel in rec_rels:
                rec_id = rec_rel.get("recording", {}).get("id")
                if not rec_id or rec_id in cache["works"]["recordingFlags"]:
                    continue
                try:
                    rec_data = self._fetch_mb_sync(f"recording/{rec_id}?fmt=json")
                    cache["works"]["recordingFlags"][rec_id] = {"video": rec_data.get("video", False), "disambiguation": rec_data.get("disambiguation", "")}
                except Exception:
                    cache["works"]["recordingFlags"][rec_id] = {"video": False, "disambiguation": ""}

        # Recordings
        self._log("recordings...")
        all_recordings = []
        rec_seen = set()
        for artist_id in (entity.ids or []):
            offset = 0
            has_more = True
            while has_more:
                self._log(f"  recording list {artist_id[:8]} offset={offset}...")
                data = self._fetch_mb_sync(f"recording?artist={artist_id}&limit=100&offset={offset}&fmt=json")
                recordings = data.get("recordings", [])
                for rec in recordings:
                    if rec["id"] not in rec_seen:
                        rec_seen.add(rec["id"])
                        all_recordings.append(rec)
                if len(recordings) == 100:
                    offset += 100
                    import time
                    time.sleep(1)
                else:
                    has_more = False

        cache["recordings"]["list"] = all_recordings

        for i, rec in enumerate(all_recordings):
            self._log(f"  recording detail {i + 1}/{len(all_recordings)}: {rec['title']}")
            cache["recordings"]["details"][rec["id"]] = self._fetch_mb_sync(
                f"recording/{rec['id']}?inc=artists+isrcs+tags+artist-rels+place-rels+releases+work-rels+aliases+recording-rels&fmt=json"
            )

        # Releases
        self._log("releases...")
        all_releases = []
        rel_seen = set()
        for artist_id in (entity.ids or []):
            offset = 0
            while True:
                self._log(f"  release list {artist_id[:8]} offset={offset}...")
                data = self._fetch_mb_sync(f"release?artist={artist_id}&limit=100&offset={offset}&fmt=json")
                releases = data.get("releases", [])
                for rel in releases:
                    if rel["id"] not in rel_seen:
                        rel_seen.add(rel["id"])
                        all_releases.append(rel)
                if len(releases) < 100:
                    break
                offset += 100
                import time
                time.sleep(1)

        cache["releases"]["list"] = all_releases

        for i, rel in enumerate(all_releases):
            self._log(f"  release detail {i + 1}/{len(all_releases)}: {rel['title']}")
            detail = self._fetch_mb_sync(f"release/{rel['id']}?inc=artists+labels+recordings+release-groups&fmt=json")
            cache["releases"]["details"][rel["id"]] = detail

            rg_id = detail.get("release-group", {}).get("id")
            if rg_id and rg_id not in cache["releases"]["releaseGroups"]:
                try:
                    rg = self._fetch_mb_sync(f"release-group/{rg_id}?inc=tags&fmt=json")
                    cache["releases"]["releaseGroups"][rg_id] = rg
                except Exception:
                    pass

        self._indent -= 1
        if not dry_run:
            self._write_cache("collectives", entity.slug, cache)

    def close(self) -> None:
        """Close the HTTP client."""
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
