"""Rights domain — music rights metadata client.

Provides typed access to ISRC, ISWC, and ASCAP ID data from the MusicBrainz cache.
Wraps MCP tools with typed dataclasses.
"""

from __future__ import annotations

import json

from magmascript.core.config import Config, get_config
from magmascript.core.exceptions import MCPError
from magmascript.core.rpc import RPCClient, RPCError
from magmascript.domains.rights.tools import (
    RecordingRights,
    RightsCatalog,
    RightsExportRow,
    RightsMatch,
    WorkRights,
)


def _wrap_mcp_error(e: Exception, context: str = "") -> Exception:
    """Wrap RPC exceptions into typed magmascript errors."""
    if isinstance(e, RPCError):
        return MCPError(f"MCP error: {e.message}", code=e.code, data=e.data)
    if isinstance(e, RuntimeError):
        return MCPError(str(e))
    if isinstance(e, Exception):
        msg = str(e) if not context else f"{context}: {e}"
        return MCPError(msg)
    return MCPError(str(e) if not context else f"{context}: {e}")


def _parse_search_results(text: str) -> list[RightsMatch]:
    """Parse the text output of search_rights into RightsMatch objects."""
    matches = []
    current = None

    for line in text.splitlines():
        line = line.strip()

        if line.startswith("[recording]") or line.startswith("[work]"):
            kind = line.split("]")[0].lstrip("[")
            title = line.split("] ", 1)[1] if "] " in line else ""
            current = RightsMatch(kind=kind, title=title, uuid="")
            matches.append(current)

        elif current and line.startswith("uuid:") or (current and line.startswith("mbid:")):
            val = line.split(":", 1)[1].strip()
            if current:
                current.uuid = val

        elif current and line.startswith("ISRC:"):
            val = line.split(":", 1)[1].strip()
            current.identifiers["isrcs"] = [v.strip() for v in val.split(",") if v.strip() and v.strip() != "n/a"]

        elif current and line.startswith("ISWC:"):
            val = line.split(":", 1)[1].strip()
            current.identifiers["iswcs"] = [v.strip() for v in val.split(",") if v.strip() and v.strip() not in ("n/a", "pending")]

        elif current and line.startswith("ASCAP:"):
            val = line.split(":", 1)[1].strip()
            current.identifiers["ascap_ids"] = [v.strip() for v in val.split(",") if v.strip() and v.strip() != "n/a"]

        elif current and line.startswith("artist:"):
            val = line.split(":", 1)[1].strip()
            current.artists = [val]

        elif current and line.startswith("composers:"):
            val = line.split(":", 1)[1].strip()
            current.artists = [v.strip() for v in val.split(",") if v.strip()]

    return matches


def _parse_recording_rights(text: str) -> RecordingRights:
    """Parse the text output of get_recording_rights into a RecordingRights."""
    title = ""
    artist = ""
    uuid = ""
    isrcs = []
    releases = []

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Recording:"):
            title = line.split(":", 1)[1].strip()
        elif line.startswith("Artist:"):
            artist = line.split(":", 1)[1].strip()
        elif line.startswith("ISRC:"):
            val = line.split(":", 1)[1].strip()
            isrcs = [v.strip() for v in val.split(",") if v.strip() and v.strip() != "none"]
        elif line.startswith("Releases:"):
            val = line.split(":", 1)[1].strip()
            releases = [v.strip() for v in val.split(",") if v.strip() and v.strip() != "none"]
        elif line.startswith("MusicBrainz:"):
            val = line.split(":", 1)[1].strip()
            # Extract UUID from URL
            if "/recording/" in val:
                uuid = val.split("/recording/")[-1]

    return RecordingRights(title=title, uuid=uuid, artist=artist, isrcs=isrcs, releases=releases)


def _parse_work_rights(text: str) -> WorkRights:
    """Parse the text output of get_work_rights into a WorkRights."""
    title = ""
    uuid = ""
    composers = []
    iswcs = []
    ascap_ids = []

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Work:"):
            title = line.split(":", 1)[1].strip()
        elif line.startswith("Composers:"):
            val = line.split(":", 1)[1].strip()
            composers = [v.strip() for v in val.split(",") if v.strip() and v.strip() != "unknown"]
        elif line.startswith("ISWC:"):
            val = line.split(":", 1)[1].strip()
            iswcs = [v.strip() for v in val.split(",") if v.strip() and v.strip() not in ("n/a", "pending")]
        elif line.startswith("ASCAP ID:"):
            val = line.split(":", 1)[1].strip()
            ascap_ids = [v.strip() for v in val.split(",") if v.strip() and v.strip() != "n/a"]
        elif line.startswith("MusicBrainz:"):
            val = line.split(":", 1)[1].strip()
            if "/work/" in val:
                uuid = val.split("/work/")[-1]

    return WorkRights(title=title, uuid=uuid, composers=composers, iswcs=iswcs, ascap_ids=ascap_ids)


def _parse_catalog(text: str) -> RightsCatalog:
    """Parse the text output of artist_rights_catalog into a RightsCatalog."""
    artist = ""
    uuid = ""
    recordings = []
    works = []

    section = None
    current_rec = None
    current_work = None

    for line in text.splitlines():
        line = line.strip()

        if line.startswith("# Rights Catalog:"):
            artist = line.split(":", 1)[1].strip()
        elif line.startswith("MusicBrainz:"):
            val = line.split(":", 1)[1].strip()
            if "/artist/" in val:
                uuid = val.split("/artist/")[-1]
        elif line.startswith("## Recordings"):
            section = "recordings"
        elif line.startswith("## Works"):
            section = "works"
        elif section == "recordings" and line and not line.startswith("##"):
            # Format: "  Title: ISRC1, ISRC2"
            if ": " in line:
                title, isrc_str = line.split(": ", 1)
                isrcs = [v.strip() for v in isrc_str.split(",") if v.strip()]
                recordings.append(RecordingRights(
                    title=title.strip(),
                    uuid="",
                    artist=artist,
                    isrcs=isrcs,
                    releases=[],
                ))
        elif section == "works" and line.startswith("ISWC:"):
            # We're in a work block; this is the ISWC line
            val = line.split(":", 1)[1].strip()
            iswcs = [v.strip() for v in val.split(",") if v.strip() and v.strip() not in ("n/a", "pending")]
            if current_work:
                current_work.iswcs = iswcs
        elif section == "works" and line.startswith("ASCAP:"):
            val = line.split(":", 1)[1].strip()
            ascap_ids = [v.strip() for v in val.split(",") if v.strip() and v.strip() != "n/a"]
            if current_work:
                current_work.ascap_ids = ascap_ids
                works.append(current_work)
                current_work = None
        elif section == "works" and line and not line.startswith("##") and not line.startswith("ISWC:") and not line.startswith("ASCAP:"):
            # This is a work title line (indented, "  Title:")
            title = line.lstrip()
            if title:
                current_work = WorkRights(
                    title=title,
                    uuid="",
                    composers=[],
                    iswcs=[],
                    ascap_ids=[],
                )

    return RightsCatalog(artist=artist, uuid=uuid, recordings=recordings, works=works)


def _parse_export_rows(text: str) -> list[RightsExportRow]:
    """Parse TSV output of export_rights_catalog into RightsExportRow objects."""
    rows = []
    lines = text.splitlines()
    if not lines:
        return rows

    # Skip header
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) >= 6:
            rows.append(RightsExportRow(
                title=parts[0],
                type=parts[1],
                artist_composer=parts[2],
                isrc=parts[3],
                iswc=parts[4],
                ascap_id=parts[5],
            ))

    return rows


class RightsClient:
    """Typed client for music rights metadata.

    Wraps MCP tools with typed dataclasses for ISRC, ISWC, and ASCAP ID lookups.
    Raises MCPError on server failures.
    """

    def __init__(self, config: Config | None = None):
        cfg = config or get_config()
        self._rpc = RPCClient(url=cfg.mcp.url, api_key=cfg.mcp.api_key)

    def _call(self, tool: str, args: dict | None = None) -> str:
        """Call an MCP tool and return the text result."""
        try:
            return self._rpc.call_tool(tool, args or {})
        except Exception as e:
            raise _wrap_mcp_error(e, tool)

    def search(self, query: str, *, artist: str = "") -> list[RightsMatch]:
        """Search by title, ISRC, ISWC, or ASCAP ID.

        Args:
            query: Search string (title, ISRC, ISWC, or ASCAP ID)
            artist: Optional artist name to filter results
        """
        args = {"query": query}
        if artist:
            args["artist"] = artist
        text = self._call("search_rights", args)
        return _parse_search_results(text)

    def isrc(self, code: str) -> RecordingRights | None:
        """Look up a recording by ISRC code."""
        matches = self.search(code)
        for m in matches:
            if m.kind == "recording" and code.upper() in [i.upper() for i in m.identifiers.get("isrcs", [])]:
                return RecordingRights(
                    title=m.title,
                    uuid=m.uuid,
                    artist=m.artists[0] if m.artists else "unknown",
                    isrcs=m.identifiers.get("isrcs", []),
                    releases=[],
                )
        return None

    def iswc(self, code: str) -> WorkRights | None:
        """Look up a work by ISWC code."""
        matches = self.search(code)
        for m in matches:
            if m.kind == "work" and code.upper() in [i.upper() for i in m.identifiers.get("iswcs", [])]:
                return WorkRights(
                    title=m.title,
                    uuid=m.uuid,
                    composers=m.artists,
                    iswcs=m.identifiers.get("iswcs", []),
                    ascap_ids=m.identifiers.get("ascap_ids", []),
                )
        return None

    def ascap(self, id: str) -> WorkRights | None:
        """Look up a work by ASCAP ID."""
        matches = self.search(id)
        for m in matches:
            if m.kind == "work" and id in m.identifiers.get("ascap_ids", []):
                return WorkRights(
                    title=m.title,
                    uuid=m.uuid,
                    composers=m.artists,
                    iswcs=m.identifiers.get("iswcs", []),
                    ascap_ids=m.identifiers.get("ascap_ids", []),
                )
        return None

    def catalog(self, artist: str) -> RightsCatalog:
        """Get full rights catalog for an artist by name or UUID."""
        text = self._call("artist_rights_catalog", {"artist": artist})
        return _parse_catalog(text)

    def export(self, *, use_cache: bool = True) -> list[RightsExportRow]:
        """Export all rights data as TSV-ready rows."""
        text = self._call("export_rights_catalog")
        return _parse_export_rows(text)

    def recording(self, uuid: str) -> RecordingRights:
        """Get rights data for a specific recording by UUID."""
        text = self._call("get_recording_rights", {"recording_uuid": uuid})
        return _parse_recording_rights(text)

    def work(self, uuid: str) -> WorkRights:
        """Get rights data for a specific work by UUID."""
        text = self._call("get_work_rights", {"work_uuid": uuid})
        return _parse_work_rights(text)

    def close(self):
        """Close the underlying HTTP client."""
        self._rpc.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
