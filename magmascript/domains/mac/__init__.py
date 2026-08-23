"""Mac domain — exposes MacClient and registers with the domain registry."""

from magmascript.domains.mac.client import MacClient
from magmascript.domains.mac.tools import (
    MacProcess,
    MacSystemInfo,
)
from magmascript.core.registry import register_domain

# Register this domain
register_domain("mac", MacClient)

__all__ = [
    "MacClient",
    "MacProcess",
    "MacSystemInfo",
]
