"""Typed result dataclasses for the Rights domain."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RecordingRights:
    """Rights data for a single recording (ISRCs + releases)."""

    title: str
    uuid: str
    artist: str
    isrcs: list[str]
    releases: list[str]


@dataclass
class WorkRights:
    """Rights data for a single work (ISWCs + ASCAP IDs)."""

    title: str
    uuid: str
    composers: list[str]
    iswcs: list[str]
    ascap_ids: list[str]


@dataclass
class RightsCatalog:
    """Full rights catalog for an artist."""

    artist: str
    uuid: str
    recordings: list[RecordingRights]
    works: list[WorkRights]


@dataclass
class RightsMatch:
    """A single search result from rights lookup."""

    kind: str  # "recording" or "work"
    title: str
    uuid: str
    identifiers: dict = field(default_factory=dict)
    artists: list[str] = field(default_factory=list)


@dataclass
class RightsExportRow:
    """A single row for TSV export."""

    title: str
    type: str  # "recording" or "work"
    artist_composer: str
    isrc: str
    iswc: str
    ascap_id: str
