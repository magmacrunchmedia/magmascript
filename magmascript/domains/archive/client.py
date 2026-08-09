"""Archive domain — archive page operations.

Provides tools for validating, caching, and generating archive pages.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from magmascript.core.exceptions import MagmascriptError


@dataclass
class FormatWarning:
    """A formatting warning from archive validation."""

    file: str
    line: int
    msg: str


@dataclass
class BakeResult:
    """Result of baking cache into archive pages."""

    baked: int
    skipped: int
    errors: list[str]


class ArchiveClient:
    """Client for archive page operations.

    Provides methods for validating format, baking cache, and generating stubs.
    """

    def __init__(self, project_root: Path | None = None):
        """Initialize the archive client.

        Args:
            project_root: Path to the magmacrunch.com project root.
                         Defaults to current working directory.
        """
        self._root = project_root or Path.cwd()
        self._archive_dir = self._root / "archive"
        self._cache_dir = self._archive_dir / "_cache"

    # ------------------------------------------------------------------
    # Format validation
    # ------------------------------------------------------------------

    def check_format(self) -> list[FormatWarning]:
        """Validate formatting consistency across archive HTML files.

        Returns a list of FormatWarning objects.
        """
        warnings = []
        html_files = self._find_html_files(self._archive_dir)

        for file_path in html_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                lines = content.split("\n")
                self._check_sub_nav_classes(file_path, lines, warnings)
                self._check_orphan_divs(file_path, lines, warnings)
            except Exception as e:
                warnings.append(FormatWarning(
                    file=str(file_path.relative_to(self._root)),
                    line=0,
                    msg=f"Error reading file: {e}",
                ))

        return warnings

    def _find_html_files(self, dir_path: Path) -> list[Path]:
        """Find all HTML files in a directory recursively."""
        html_files = []
        try:
            for entry in dir_path.iterdir():
                if entry.name in ("node_modules", ".git"):
                    continue
                if entry.is_dir():
                    html_files.extend(self._find_html_files(entry))
                elif entry.suffix == ".html":
                    html_files.append(entry)
        except PermissionError:
            pass
        return html_files

    def _check_sub_nav_classes(self, file_path: Path, lines: list[str], warnings: list[FormatWarning]):
        """Check that sub-nav CSS classes match link text."""
        # Canonical mapping: link text → expected CSS class
        text_to_class = {
            "about": "c-about",
            "events": "c-events",
            "games": "c-games",
            "links": "c-links",
            "music videos": "c-music-videos",
            "network": "c-network",
            "documentary": "c-documentary",
            "personnel": "c-personnel",
            "photography": "c-photography",
            "recordings": "c-recordings",
            "releases": "c-releases",
            "works": "c-works",
        }

        # Load CSS classes for this page
        css_classes = self._load_css_classes(file_path.parent)

        # Extract sub-nav blocks
        navs = self._extract_sub_navs(lines)
        for nav in navs:
            cards = self._extract_cards(nav["lines"])
            for card in cards:
                if card["cls"] == "c-back":
                    continue
                expected = text_to_class.get(card["text"])
                if expected and card["cls"] != expected:
                    # Only warn if the target class is actually defined in CSS
                    if expected not in css_classes:
                        continue
                    line_num = nav["start_line"] + card["line_offset"] + 1
                    warnings.append(FormatWarning(
                        file=str(file_path.relative_to(self._root)),
                        line=line_num,
                        msg=f'sub-nav class mismatch: "{card["text"]}" link uses {card["cls"]}, expected {expected}',
                    ))

    def _load_css_classes(self, dir_path: Path) -> set[str]:
        """Load CSS class definitions from a directory's stylesheets."""
        classes = set()

        # Collect CSS files
        css_files = []
        try:
            for f in dir_path.iterdir():
                if f.suffix == ".css":
                    css_files.append(f)
        except PermissionError:
            pass
        css_files.append(self._root / "style.css")

        for css_file in css_files:
            try:
                css = css_file.read_text(encoding="utf-8")
                # Match .nav-card.c-classname patterns
                for match in re.finditer(r"\.nav-card\.([\w-]+)", css):
                    classes.add(match.group(1))
            except Exception:
                pass

        return classes

    def _extract_sub_navs(self, lines: list[str]) -> list[dict]:
        """Extract sub-nav blocks with surrounding line context."""
        navs = []
        for i, line in enumerate(lines):
            if '<div class="sub-nav"' in line:
                depth = 0
                end = i
                for j in range(i, len(lines)):
                    open_tags = len(re.findall(r"<div[\s>]", lines[j]))
                    close_tags = len(re.findall(r"</div>", lines[j]))
                    depth += open_tags - close_tags
                    if depth <= 0:
                        end = j
                        break
                navs.append({
                    "start_line": i,
                    "end_line": end,
                    "lines": lines[i:end + 1],
                })
        return navs

    def _extract_cards(self, nav_lines: list[str]) -> list[dict]:
        """Extract nav-card links from sub-nav lines."""
        cards = []
        for i, line in enumerate(nav_lines):
            match = re.search(
                r'<a\s+href="([^"]+)"\s+class="nav-card\s+(c-[\w-]+)"[^>]*>([^<]+)</a>',
                line,
            )
            if match:
                cards.append({
                    "href": match.group(1),
                    "cls": match.group(2),
                    "text": match.group(3).strip(),
                    "line_offset": i,
                })
        return cards

    def _check_orphan_divs(self, file_path: Path, lines: list[str], warnings: list[FormatWarning]):
        """Check for orphan closing div tags."""
        opens = sum(len(re.findall(r"<div[\s>]", line)) for line in lines)
        closes = sum(len(re.findall(r"</div>", line)) for line in lines)

        if opens != closes:
            depth = 0
            for i in range(len(lines) - 1, -1, -1):
                open_tags = len(re.findall(r"<div[\s>]", lines[i]))
                close_tags = len(re.findall(r"</div>", lines[i]))
                depth += close_tags - open_tags
                if depth > 0:
                    warnings.append(FormatWarning(
                        file=str(file_path.relative_to(self._root)),
                        line=i + 1,
                        msg=f"orphan closing </div> tag ({opens} opens, {closes} closes)",
                    ))
                    return
            warnings.append(FormatWarning(
                file=str(file_path.relative_to(self._root)),
                line=1,
                msg=f"mismatched div tags: {opens} opens, {closes} closes",
            ))

    # ------------------------------------------------------------------
    # Cache baking
    # ------------------------------------------------------------------

    def bake_cache(self, dry_run: bool = False) -> BakeResult:
        """Inlines MusicBrainz cache JSON into archive stub pages.

        Args:
            dry_run: If True, show what would change without writing files.

        Returns:
            BakeResult with counts and any errors.
        """
        # Config variable names for each entity type
        config_patterns = {
            "by-artist": {"regex": r"window\.ARTIST_CONFIG\s*=\s*(\{[^}]+\})", "cache_type": "artists", "id_key": "id"},
            "by-artist-collective": {"regex": r"window\.COLLECTIVE_CONFIG\s*=\s*(\{[\s\S]*?\})\s*;", "cache_type": "collectives", "id_key": "slug"},
            "by-place": {"regex": r"window\.PLACE_CONFIG\s*=\s*(\{[^}]+\})", "cache_type": "places", "id_key": "id"},
            "by-contributor": {"regex": r"window\.__CONTRIBUTOR_CONFIG\s*=\s*(\{[^}]+\})", "cache_type": "contributors", "id_key": "MB_ID"},
            "by-label": {"regex": r"window\.__LABEL_CONFIG\s*=\s*(\{[^}]+\})", "cache_type": "labels", "id_key": "MB_ID"},
        }

        # Directories to scan for archive stubs
        archive_dirs = [
            self._archive_dir / "by-artist",
            self._archive_dir / "by-place",
            self._archive_dir / "by-contributor",
            self._archive_dir / "by-label",
        ]

        result = BakeResult(baked=0, skipped=0, errors=[])

        for dir_path in archive_dirs:
            stubs = self._find_stubs(dir_path)
            for stub_path in stubs:
                try:
                    self._process_stub(stub_path, config_patterns, dry_run, result)
                except Exception as e:
                    result.errors.append(f"{stub_path.relative_to(self._root)}: {e}")

        return result

    def _find_stubs(self, dir_path: Path) -> list[Path]:
        """Find all HTML stubs in subdirectories."""
        stubs = []
        try:
            for entity_dir in dir_path.iterdir():
                if not entity_dir.is_dir():
                    continue
                for file_path in entity_dir.glob("*.html"):
                    stubs.append(file_path)
        except PermissionError:
            pass
        return stubs

    def _process_stub(self, file_path: Path, config_patterns: dict, dry_run: bool, result: BakeResult):
        """Process a single stub file."""
        content = file_path.read_text(encoding="utf-8")

        # Find matching pattern
        cache_type = None
        pattern = None
        for name, p in config_patterns.items():
            if re.search(p["regex"], content):
                pattern = p
                cache_type = p["cache_type"]
                break

        if not pattern:
            return

        # Extract identifier
        id_match = re.search(pattern["regex"], content)
        if not id_match:
            return

        config_str = id_match.group(1)
        id_key = pattern["id_key"]
        id_match = re.search(rf'{id_key}\s*:\s*[\'"]([^\'"]+)[\'"]', config_str)
        if not id_match:
            return

        entity_id = id_match.group(1)

        # Load cache data
        cache_file = self._cache_dir / cache_type / f"{entity_id}.json"
        if not cache_file.exists():
            return

        try:
            cache_data = json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            return

        # Check if already baked
        if "window.__MB_CACHE" in content:
            result.skipped += 1
            return

        # Find the template script tag
        template_script_match = re.search(r'<script src="[^"]*templates/[^"]+\.js"></script>', content)
        if not template_script_match:
            return

        # Inject cache before the template script
        cache_script = f"<script>\nwindow.__MB_CACHE = {json.dumps(cache_data)};\n</script>\n"
        new_content = content.replace(template_script_match.group(0), cache_script + template_script_match.group(0))

        if dry_run:
            size_kb = len(json.dumps(cache_data)) / 1024
            print(f"  [dry-run] would bake: {file_path.relative_to(self._root)} ({size_kb:.1f} KB)")
        else:
            file_path.write_text(new_content, encoding="utf-8")
            print(f"  baked: {file_path.relative_to(self._root)}")

        result.baked += 1

    # ------------------------------------------------------------------
    # Stubs generation (placeholder - full implementation would port generate-archive-stubs.mjs)
    # ------------------------------------------------------------------

    def generate_stubs(self, config_file: Path | None = None) -> dict:
        """Generate stub HTML files for new archive entities.

        This is a placeholder implementation. The full implementation would
        port the logic from scripts/generate-archive-stubs.mjs.

        Args:
            config_file: Path to archive-stubs.json config file.

        Returns:
            Dict with counts of generated files.
        """
        # TODO: Port generate-archive-stubs.mjs logic
        return {"generated": 0, "skipped": 0, "errors": []}
