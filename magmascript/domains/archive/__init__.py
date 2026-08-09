"""Archive domain — archive page operations."""

from magmascript.domains.archive.client import ArchiveClient
from magmascript.core.registry import register_domain

# Register this domain
register_domain("archive", ArchiveClient)

__all__ = ["ArchiveClient"]
