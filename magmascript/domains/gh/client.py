"""GitHub domain — direct API client for GitHub operations.

Uses core/github.py as the shared HTTP layer.
Raises APIError on HTTP failures.
"""

from __future__ import annotations

import httpx

from magmascript.core.config import Config, get_config
from magmascript.core.exceptions import APIError, AuthError, RateLimitError
from magmascript.core.github import WORKFLOWS, GitHubClient
from magmascript.domains.gh.tools import (
    Issue,
    Workflow,
    WorkflowRun,
    parse_issues,
    parse_workflow_runs,
)


def _wrap_api_error(e: Exception, context: str = "") -> APIError:
    """Wrap httpx exceptions into typed APIError."""
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        msg = f"GitHub API error {status}"
        if context:
            msg = f"{context}: {msg}"
        if status in (401, 403):
            return AuthError(msg, status_code=status)
        if status == 429:
            return RateLimitError(msg, status_code=status)
        return APIError(msg, status_code=status)
    if isinstance(e, httpx.ConnectError):
        return APIError(f"GitHub connection failed: {e}" if not context else f"{context}: connection failed")
    if isinstance(e, httpx.TimeoutException):
        return APIError(f"GitHub request timed out" if not context else f"{context}: timed out")
    if isinstance(e, KeyError):
        return APIError(f"Unknown workflow: {e}" if not context else f"{context}: {e}")
    return APIError(f"GitHub API error: {e}" if not context else f"{context}: {e}")


class GHClient:
    """GitHub operations client.

    Wraps core/github.py with domain-specific methods that return typed results.
    Raises APIError on HTTP failures.
    """

    def __init__(self, config: Config | None = None):
        cfg = config or get_config()
        self._client = GitHubClient(
            token=cfg.gh.token,
            owner=cfg.gh.owner,
            repo=cfg.gh.repo,
        )

    # ------------------------------------------------------------------
    # Workflows
    # ------------------------------------------------------------------

    def workflows(self) -> list[Workflow]:
        """List all known workflows with their latest run status."""
        try:
            runs = self._client.list_workflow_runs(limit=100)
        except Exception as e:
            raise _wrap_api_error(e, "list workflows")
        return parse_workflow_runs(runs, WORKFLOWS)

    def workflow_runs(self, name: str, limit: int = 10) -> list[WorkflowRun]:
        """Get recent runs for a specific workflow."""
        try:
            workflow_file = self._client.get_workflow_file(name)
            data = self._client.get(
                f"{self._client._repo_path}/actions/workflows/{workflow_file}/runs?per_page={limit}"
            )
        except Exception as e:
            raise _wrap_api_error(e, f"get runs for {name}")
        runs = data.get("workflow_runs", [])
        return [
            WorkflowRun(
                id=r["id"],
                status=r.get("status", "unknown"),
                conclusion=r.get("conclusion", ""),
                event=r.get("event", ""),
                created_at=r.get("created_at", ""),
                html_url=r.get("html_url", ""),
                name=r.get("name", ""),
            )
            for r in runs
        ]

    def trigger(self, name: str) -> str:
        """Trigger a workflow. Returns confirmation message."""
        try:
            self._client.trigger_workflow(name)
            return f"✓ Triggered {name}"
        except Exception as e:
            raise _wrap_api_error(e, f"trigger {name}")

    # ------------------------------------------------------------------
    # Issues
    # ------------------------------------------------------------------

    def issues(self, *, labels: str = "", state: str = "open", limit: int = 30) -> list[Issue]:
        """List issues with optional filters."""
        try:
            raw = self._client.list_issues(labels=labels, state=state, limit=limit)
        except Exception as e:
            raise _wrap_api_error(e, "list issues")
        return parse_issues(raw)

    def create_issue(self, title: str, body: str = "", labels: list[str] | None = None) -> Issue:
        """Create a new issue."""
        try:
            raw = self._client.create_issue(title, body, labels)
        except Exception as e:
            raise _wrap_api_error(e, "create issue")
        return Issue(
            number=raw["number"],
            title=raw["title"],
            state=raw.get("state", "open"),
            created_at=raw.get("created_at", ""),
            labels=[l.get("name", "") for l in raw.get("labels", [])],
            html_url=raw.get("html_url", ""),
        )

    def close_issue(self, number: int) -> str:
        """Close an issue."""
        try:
            self._client.close_issue(number)
            return f"✓ Closed issue #{number}"
        except Exception as e:
            raise _wrap_api_error(e, f"close issue #{number}")

    # ------------------------------------------------------------------
    # Files
    # ------------------------------------------------------------------

    def get_file(self, path: str) -> tuple[str, str]:
        """Read a file from the repo. Returns (content, sha)."""
        try:
            return self._client.get_file(path)
        except Exception as e:
            raise _wrap_api_error(e, f"get file {path}")

    def put_file(self, path: str, content: str, message: str) -> str:
        """Create or update a file in the repo."""
        sha = None
        try:
            _, sha = self._client.get_file(path)
        except Exception:
            pass  # File doesn't exist yet — that's fine
        try:
            self._client.put_file(path, content, message, sha)
            return f"✓ Updated {path}"
        except Exception as e:
            raise _wrap_api_error(e, f"update {path}")

    # ------------------------------------------------------------------
    # Repo
    # ------------------------------------------------------------------

    def repo_info(self) -> dict:
        """Get repository metadata."""
        try:
            return self._client.repo_info()
        except Exception as e:
            raise _wrap_api_error(e, "get repo info")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
