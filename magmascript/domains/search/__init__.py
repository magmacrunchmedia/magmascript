"""Search domain — site search index builder."""

from magmascript.domains.search.client import SearchClient
from magmascript.core.registry import register_domain

# Register this domain
register_domain("search", SearchClient)

__all__ = ["SearchClient"]
