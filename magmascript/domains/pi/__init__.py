"""Pi domain — exposes PIClient and registers with the domain registry."""

from magmascript.domains.pi.client import PIClient
from magmascript.domains.pi.tools import (
    NginxTraffic,
    PiServiceStatus,
    PiSystemInfo,
)
from magmascript.core.registry import register_domain

# Register this domain
register_domain("pi", PIClient)

__all__ = [
    "PIClient",
    "NginxTraffic",
    "PiServiceStatus",
    "PiSystemInfo",
]
