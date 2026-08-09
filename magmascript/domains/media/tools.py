"""Typed result dataclasses for the Media domain."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MediaDimensions:
    """Image/video dimensions."""

    width: int
    height: int


@dataclass
class MediaResult:
    """A single media search result, normalized across all providers."""

    id: str
    title: str
    thumbnail: str
    full_url: str
    source: str
    license: str
    license_url: str
    type: str  # "image", "video", "audio"
    author: str
    source_url: str
    dimensions: MediaDimensions | None = None


@dataclass
class MediaSearchResponse:
    """Aggregated search response from one or more providers."""

    results: list[MediaResult]
    total: int
    page: int
    has_more: bool
    provider_totals: dict[str, int] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)  # provider -> error message


@dataclass
class MediaProvider:
    """Metadata about a media provider."""

    key: str
    label: str
    color: str
    needs_key: bool
    types: list[str]
