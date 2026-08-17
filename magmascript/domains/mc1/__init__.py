"""MC1 domain — exposes MC1Client and registers with the domain registry."""

from magmascript.domains.mc1.client import MC1Client
from magmascript.domains.mc1.tools import MC1ServiceStatus, MC1SystemInfo, MC1PowerSettings
from magmascript.core.registry import register_domain

# Register this domain
register_domain("mc1", MC1Client)

__all__ = [
    "MC1Client",
    "MC1ServiceStatus",
    "MC1SystemInfo",
    "MC1PowerSettings",
]
