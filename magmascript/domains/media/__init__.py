"""Media domain — exposes MediaClient and registers with the domain registry."""

from magmascript.domains.media.client import MediaClient
from magmascript.domains.media.tools import (
    MediaDimensions,
    MediaProvider,
    MediaResult,
    MediaSearchResponse,
)
from magmascript.core.registry import register_domain

# Register this domain
register_domain("media", MediaClient)

__all__ = [
    "MediaClient",
    "MediaDimensions",
    "MediaProvider",
    "MediaResult",
    "MediaSearchResponse",
]
