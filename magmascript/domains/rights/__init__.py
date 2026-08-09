"""Rights domain — exposes RightsClient and registers with the domain registry."""

from magmascript.domains.rights.client import RightsClient
from magmascript.domains.rights.tools import (
    RecordingRights,
    RightsCatalog,
    RightsExportRow,
    RightsMatch,
    WorkRights,
)
from magmascript.core.registry import register_domain

# Register this domain
register_domain("rights", RightsClient)

__all__ = [
    "RightsClient",
    "RecordingRights",
    "RightsCatalog",
    "RightsExportRow",
    "RightsMatch",
    "WorkRights",
]
