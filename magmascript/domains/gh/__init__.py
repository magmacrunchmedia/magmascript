"""GitHub domain — exposes GHClient and registers with the domain registry."""

from magmascript.domains.gh.client import GHClient
from magmascript.domains.gh.tools import Issue, Workflow, WorkflowRun
from magmascript.core.registry import register_domain

# Register this domain
register_domain("gh", GHClient)

__all__ = [
    "GHClient",
    "Issue",
    "Workflow",
    "WorkflowRun",
]
