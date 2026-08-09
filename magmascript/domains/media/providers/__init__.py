"""Base provider protocol for media search providers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from magmascript.domains.media.tools import MediaProvider, MediaResult, MediaSearchResponse


@runtime_checkable
class BaseProvider(Protocol):
    """Protocol that all media providers must implement."""

    @property
    def info(self) -> MediaProvider:
        """Provider metadata."""
        ...

    def search(
        self,
        query: str,
        *,
        page: int = 1,
        per_page: int = 24,
        media_type: str = "",
        orientation: str = "",
    ) -> MediaSearchResponse:
        """Search this provider. Returns normalized results."""
        ...

    def get(self, result_id: str) -> MediaResult | None:
        """Get a single result by ID."""
        ...
