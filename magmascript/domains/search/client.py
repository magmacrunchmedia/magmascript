"""Search domain — site search index builder.

Provides a Python client for building the site search index
used by Fuse.js for client-side search.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from magmascript.core.exceptions import MagmascriptError


@dataclass
class SearchEntry:
    """A single search index entry."""

    t: str  # title
    c: str  # category
    u: str  # url (relative)
    d: str  # description
    b: str  # body text


@dataclass
class BuildResult:
    """Result of building the search index."""

    total_entries: int
    deduplicated: int
    output_file: str


class SearchClient:
    """Site search index builder.

    Scans the magmacrunch.com site and generates search-index.json
    for client-side search with Fuse.js.
    """

    def __init__(self, project_root: Path | None = None):
        """Initialize the search client.

        Args:
            project_root: Path to the magmacrunch.com project root.
                         Defaults to current working directory.
        """
        self._root = project_root or Path.cwd()
        self._index: list[SearchEntry] = []
        self._url_index: dict[str, int] = {}

    def _add_item(self, title: str, category: str, url: str, description: str = "", body: str = "") -> None:
        """Add an item to the search index."""
        entry = SearchEntry(
            t=title,
            c=category,
            u="/" + url,
            d=description,
            b=body,
        )
        self._url_index["/" + url] = len(self._index)
        self._index.append(entry)

    def _extract_body_text(self, html: str, max_length: int = 600) -> str:
        """Extract plain text from HTML for search indexing."""
        text = html
        # Remove script, style, nav, footer tags
        text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<nav[\s\S]*?</nav>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<footer[\s\S]*?</footer>", "", text, flags=re.IGNORECASE)
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Decode HTML entities
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        # Truncate
        if len(text) > max_length:
            text = text[:max_length] + "..."
        return text

    def _extract_title(self, html: str) -> str | None:
        """Extract title from HTML."""
        match = re.search(r"<title>([^<]+)</title>", html)
        if not match:
            return None
        title = match.group(1)
        # Split on em dash or en dash and take first part
        title = re.split(r"[—–]", title)[0].strip()
        return title

    def _pretty_name(self, slug: str) -> str:
        """Convert a slug to a readable name."""
        return re.sub(r"\b\w", lambda m: m.group(0).upper(), slug.replace("-", " "))

    def _find_html_files(self, dir_path: Path) -> list[Path]:
        """Find all HTML files in a directory recursively."""
        results = []
        if not dir_path.exists():
            return results
        for entry in dir_path.iterdir():
            if entry.is_dir():
                results.extend(self._find_html_files(entry))
            elif entry.suffix == ".html":
                results.append(entry)
        return results

    # ------------------------------------------------------------------
    # Section parsers
    # ------------------------------------------------------------------

    def _parse_main_pages(self) -> None:
        """Parse main/hub pages."""
        pages = [
            {"file": "index.html", "title": "Home", "desc": "magmacrunch media homepage"},
            {"file": "home/about.html", "title": "About", "desc": "About magmacrunch media"},
            {"file": "home/guestbook.html", "title": "Guestbook", "desc": "Sign the guestbook"},
            {"file": "music/index.html", "title": "Music Hub", "desc": "Music landing page"},
            {"file": "music/distributed-music/index.html", "title": "Distributed Music", "desc": "Stream and download releases"},
            {"file": "music/jukebox/index.html", "title": "Jukebox", "desc": "Audio jukebox player"},
            {"file": "music/physical-media/index.html", "title": "Physical Media", "desc": "CDs, tapes, and floppy disks"},
            {"file": "music/physical-media/cd/index.html", "title": "CD Releases", "desc": "CD releases catalog"},
            {"file": "music/physical-media/tape/index.html", "title": "Tape Releases", "desc": "Cassette tape releases"},
            {"file": "music/physical-media/floppy-disk/index.html", "title": "Floppy Disk", "desc": "Floppy disk releases"},
            {"file": "music/music-videos.html", "title": "Music Videos", "desc": "MTV-style music videos"},
            {"file": "visual/index.html", "title": "Visual Hub", "desc": "Visual art landing page"},
            {"file": "visual/collage.html", "title": "Collage", "desc": "Editorial magazine collage art"},
            {"file": "visual/photography/index.html", "title": "Photography", "desc": "Photography gallery"},
            {"file": "visual/tv/index.html", "title": "Teevee", "desc": "Television-style content"},
            {"file": "archive/index.html", "title": "Archive Hub", "desc": "MusicBrainz archive"},
            {"file": "archive/by-artist/index.html", "title": "Artists", "desc": "Browse by artist"},
            {"file": "archive/by-place/index.html", "title": "Places", "desc": "Browse by place"},
            {"file": "archive/by-label/index.html", "title": "Labels", "desc": "Browse by label"},
            {"file": "archive/by-contributor/index.html", "title": "Contributors", "desc": "Browse by contributor"},
            {"file": "arcade/index.html", "title": "Arcade Hub", "desc": "Pixel games and multiplayer"},
            {"file": "arcade/server.html", "title": "Arcade Server", "desc": "Server status and info"},
            {"file": "arcade/board-games/index.html", "title": "Board Games", "desc": "Chess, checkers, backgammon, and more"},
            {"file": "arcade/card-games/index.html", "title": "Card Games", "desc": "Solitaire, cribbage, poker"},
            {"file": "arcade/puzzles/index.html", "title": "Puzzles", "desc": "2048, Tetris, and brain teasers"},
            {"file": "arcade/action/index.html", "title": "Action Games", "desc": "Drift, race, and survive"},
            {"file": "press/index.html", "title": "Press Hub", "desc": "Journals and writing"},
            {"file": "press/scientific/index.html", "title": "Scientific Journal", "desc": "Academic writing and physics"},
            {"file": "press/experimental/index.html", "title": "Experimental Journal", "desc": "Experimental and literary writing"},
            {"file": "press/lyrics/index.html", "title": "Lyrics", "desc": "Song lyrics by artist"},
            {"file": "tools/index.html", "title": "Tools Hub", "desc": "Creative web tools"},
        ]

        for p in pages:
            file_path = self._root / p["file"]
            if not file_path.exists():
                continue
            html = file_path.read_text(encoding="utf-8")
            title = self._extract_title(html) or p["title"]
            body = self._extract_body_text(html)
            self._add_item(title, "page", p["file"], p["desc"], body)

    def _parse_distributed_music(self) -> None:
        """Parse distributed music releases."""
        index_file = self._root / "music" / "distributed-music" / "index.html"
        if not index_file.exists():
            return

        html = index_file.read_text(encoding="utf-8")
        card_regex = r'<!-- ═══ (.+?) ═══ -->[\s\S]*?id="([^"]+)"[\s\S]*?dist-title">([^<]+)<[\s\S]*?dist-artist">by <a href="([^"]+)">([^<]+)<[\s\S]*?dist-description">\s*<p>\s*([\s\S]*?)\s*</p>'
        for match in re.finditer(card_regex, html):
            _, id_, title, _, artist_name, desc = match.groups()
            clean_desc = re.sub(r"\s+", " ", desc).strip()
            self._add_item(title, "music", f"music/distributed-music/#{id_}", f"{artist_name} — {clean_desc}")

    def _parse_jukebox_songs(self) -> None:
        """Parse jukebox songs."""
        songs_file = self._root / "music" / "jukebox" / "songs.json"
        if not songs_file.exists():
            return

        songs = json.loads(songs_file.read_text(encoding="utf-8"))
        visible = [s for s in songs if not s.get("hidden")]
        for song in visible:
            self._add_item(song["title"], "song", "music/jukebox/", f"{song['artist']} — {song['duration']}")

    def _parse_physical_media(self) -> None:
        """Parse physical media (floppy disk sub-pages)."""
        floppy_dir = self._root / "music" / "physical-media" / "floppy-disk"
        releases = ["iou-american-spirits", "pay2play-2025"]
        for release in releases:
            release_dir = floppy_dir / release
            files = self._find_html_files(release_dir)
            for file_path in files:
                html = file_path.read_text(encoding="utf-8")
                title = self._extract_title(html)
                if not title:
                    continue
                rel_path = file_path.relative_to(self._root).as_posix()
                body = self._extract_body_text(html)
                self._add_item(title, "music", rel_path, "Floppy disk release", body)

    def _parse_archive_section(self, section_type: str) -> None:
        """Parse an archive section (by-artist, by-place, etc.)."""
        dir_path = self._root / "archive" / section_type
        if not dir_path.exists():
            return

        category_map = {
            "by-artist": "artist",
            "by-place": "place",
            "by-label": "label",
            "by-contributor": "contributor",
        }
        category = category_map.get(section_type, section_type)
        sub_type = section_type.replace("by-", "")

        entries = [e for e in dir_path.iterdir() if e.is_dir() and not e.name.startswith("_")]

        for entry in entries:
            files = self._find_html_files(entry)
            for file_path in files:
                html = file_path.read_text(encoding="utf-8")
                title = self._extract_title(html)
                if not title:
                    continue

                rel_path = file_path.relative_to(self._root).as_posix()
                body = self._extract_body_text(html)
                entity_name = self._pretty_name(entry.name)

                # Build a descriptive label based on sub-page type
                file_name = file_path.stem
                if file_name != "index":
                    desc = f"{entity_name} — {self._pretty_name(file_name)}"
                else:
                    desc = f"{sub_type} archive — recordings, works, events, releases"

                self._add_item(title, category, rel_path, desc, body)

    def _parse_arcade_games(self) -> None:
        """Parse arcade games."""
        game_dirs = [
            "chess", "checkers", "backgammon", "parchisi", "chinese-checkers",
            "solitaire", "cribbage", "scandinavian-stud", "solitaire_THLD", "tarot",
            "2^N", "george-boole", "fifteen-puzzle", "threes", "klotski", "tetris",
            "moonlight-drift", "very-long-boards", "roderick-tron", "SORRY",
            "aggravation",
        ]

        categories = {
            "board": ["chess", "checkers", "backgammon", "parchisi", "chinese-checkers", "aggravation"],
            "card": ["solitaire", "cribbage", "scandinavian-stud", "solitaire_THLD", "tarot"],
            "puzzle": ["2^N", "george-boole", "fifteen-puzzle", "threes", "klotski", "tetris"],
            "action": ["moonlight-drift", "very-long-boards", "roderick-tron"],
            "other": ["SORRY"],
        }

        cat_labels = {
            "board": "Board Game",
            "card": "Card Game",
            "puzzle": "Puzzle Game",
            "action": "Action Game",
            "other": "Game",
        }

        for game in game_dirs:
            index_file = self._root / "arcade" / game / "index.html"
            if not index_file.exists():
                continue

            html = index_file.read_text(encoding="utf-8")
            title = self._extract_title(html) or self._pretty_name(game)

            desc_match = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html)
            cat = next(
                (cat_labels[cat_name] for cat_name, games in categories.items() if game in games),
                "Game",
            )

            self._add_item(title, "arcade", f"arcade/{game}/", desc_match.group(1) if desc_match else cat)

    def _parse_press(self) -> None:
        """Parse press section."""
        press_dir = self._root / "press"
        files = self._find_html_files(press_dir)

        for file_path in files:
            html = file_path.read_text(encoding="utf-8")
            title = self._extract_title(html)
            if not title:
                continue

            rel_path = file_path.relative_to(self._root).as_posix()
            body = self._extract_body_text(html)

            # Categorize based on path
            desc = "Press"
            if "scientific" in rel_path:
                desc = "Scientific journal"
            elif "experimental" in rel_path:
                desc = "Experimental journal"
            elif "lyrics" in rel_path:
                desc = "Lyrics"
            elif "submissions" in rel_path:
                desc = "Submission guidelines"

            self._add_item(title, "press", rel_path, desc, body)

    def _parse_tools(self) -> None:
        """Parse tools section."""
        tool_dirs = ["album-art-maker", "media-search", "pixel-process"]
        for tool in tool_dirs:
            index_file = self._root / "tools" / tool / "index.html"
            if not index_file.exists():
                continue
            html = index_file.read_text(encoding="utf-8")
            title = self._extract_title(html) or self._pretty_name(tool)
            body = self._extract_body_text(html)
            self._add_item(title, "tool", f"tools/{tool}/", "Creative web tool", body)

    def _parse_musicbrainz_cache(self) -> None:
        """Parse MusicBrainz cache to enrich archive entries."""
        cache_dir = self._root / "archive" / "_cache"
        entity_map_path = self._root / "templates" / "entity-map.js"

        if not entity_map_path.exists():
            return

        # Parse entity-map.js to get UUID → relative path mapping
        entity_map_src = entity_map_path.read_text(encoding="utf-8")
        uuid_map: dict[str, str] = {}
        uuid_regex = r"['\"]([0-9a-f-]{36})['\"]\s*:\s*['\"]([^'\"]+)['\"]"
        for match in re.finditer(uuid_regex, entity_map_src):
            uuid_val = match.group(1)
            rel_path = match.group(2)
            rel_path = re.sub(r"^\.\./\.\./", "archive/", rel_path)
            uuid_map[uuid_val] = rel_path

        # Parse artist cache files
        artist_dir = cache_dir / "artists"
        if not artist_dir.exists():
            return

        for file_path in artist_dir.glob("*.json"):
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                if not data.get("name") or not data.get("uuid"):
                    continue

                base_path = uuid_map.get(data["uuid"])
                if not base_path:
                    continue

                prefix = re.sub(r"index\.html$", "", base_path)

                # Enrich recordings page
                recs = data.get("subpages", {}).get("recordings", {}).get("list", {}).get("recordings", [])
                if recs:
                    rec_url = "/" + prefix + "recordings.html"
                    idx = self._url_index.get(rec_url)
                    if idx is not None:
                        titles = ", ".join(r.get("title", "") for r in recs if r.get("title"))
                        self._index[idx].b = (self._index[idx].b + " " if self._index[idx].b else "") + titles

                # Enrich releases page
                rels = data.get("subpages", {}).get("releases", {}).get("list", {}).get("releases", [])
                if rels:
                    rel_url = "/" + prefix + "releases.html"
                    idx = self._url_index.get(rel_url)
                    if idx is not None:
                        titles = ", ".join(r.get("title", "") for r in rels if r.get("title"))
                        self._index[idx].b = (self._index[idx].b + " " if self._index[idx].b else "") + titles

                # Enrich works page
                works = data.get("subpages", {}).get("works", {}).get("list", {}).get("works", [])
                if works:
                    work_url = "/" + prefix + "works.html"
                    idx = self._url_index.get(work_url)
                    if idx is not None:
                        titles = ", ".join(w.get("title", "") for w in works if w.get("title"))
                        self._index[idx].b = (self._index[idx].b + " " if self._index[idx].b else "") + titles
            except Exception:
                continue

    # ------------------------------------------------------------------
    # Main build operation
    # ------------------------------------------------------------------

    def build(self) -> BuildResult:
        """Build the search index.

        Returns:
            BuildResult with counts and output file path.
        """
        self._index = []
        self._url_index = {}

        # Parse all sections
        self._parse_main_pages()
        self._parse_distributed_music()
        self._parse_jukebox_songs()
        self._parse_physical_media()
        self._parse_archive_section("by-artist")
        self._parse_archive_section("by-place")
        self._parse_archive_section("by-label")
        self._parse_archive_section("by-contributor")
        self._parse_arcade_games()
        self._parse_press()
        self._parse_tools()
        self._parse_musicbrainz_cache()

        # Deduplicate by URL (keep first occurrence)
        seen: set[str] = set()
        deduped: list[SearchEntry] = []
        for entry in self._index:
            if entry.u not in seen:
                seen.add(entry.u)
                deduped.append(entry)

        # Write output
        out_path = self._root / "search-index.json"
        out_data = [
            {"t": e.t, "c": e.c, "u": e.u, "d": e.d, "b": e.b}
            for e in deduped
        ]
        out_path.write_text(json.dumps(out_data, indent=2), encoding="utf-8")

        return BuildResult(
            total_entries=len(self._index),
            deduplicated=len(deduped),
            output_file=str(out_path),
        )

    def preview(self, limit: int = 10) -> list[SearchEntry]:
        """Build and preview the search index without writing.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of SearchEntry objects.
        """
        # Store original index
        original_index = self._index.copy()
        original_url_index = self._url_index.copy()

        # Build
        self._index = []
        self._url_index = {}

        self._parse_main_pages()
        self._parse_distributed_music()
        self._parse_jukebox_songs()
        self._parse_physical_media()
        self._parse_archive_section("by-artist")
        self._parse_archive_section("by-place")
        self._parse_archive_section("by-label")
        self._parse_archive_section("by-contributor")
        self._parse_arcade_games()
        self._parse_press()
        self._parse_tools()
        self._parse_musicbrainz_cache()

        result = self._index[:limit]

        # Restore original state
        self._index = original_index
        self._url_index = original_url_index

        return result
