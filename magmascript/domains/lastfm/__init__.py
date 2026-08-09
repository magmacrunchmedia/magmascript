"""Last.fm domain — Last.fm API client."""

from magmascript.domains.lastfm.client import LastFmClient
from magmascript.core.registry import register_domain

# Register this domain
register_domain("lastfm", LastFmClient)

__all__ = ["LastFmClient"]
