"""MusicBrainz domain — MusicBrainz API client."""

from magmascript.domains.mb.client import MusicBrainzClient
from magmascript.core.registry import register_domain

# Register this domain
register_domain("mb", MusicBrainzClient)

__all__ = ["MusicBrainzClient"]
