"""Shared GitHub API client — used by the gh domain and potentially other domains."""

from __future__ import annotations

import base64
from typing import Any

import httpx


# Canonical workflow name-to-file mapping (single source of truth)
WORKFLOWS: dict[str, str] = {
    "CI": "ci.yml",
    "Deploy to Pi": "deploy-pi.yml",
    "Check Links": "check-links.yml",
    "Check Archive Format": "check-archive-format.yml",
    "Check Pi Services": "check-services.yml",
    "Rebuild Search Index": "rebuild-search-index.yml",
    "Generate Archive Stubs": "generate-stubs.yml",
    "Bake Cache": "bake-cache.yml",
    "Weekly High Scores": "weekly-scores.yml",
    "Arcade Smoke Test": "smoke-test.yml",
    "MusicBrainz Backup": "backup-musicbrainz.yml",
    "TMDB Backup": "backup-tmdb.yml",
    "Bot Status Report": "bot-status.yml",
}


class GitHubClient:
    """Lightweight GitHub REST API client.

    Provides authenticated HTTP methods for the GitHub API.
    Used by the gh domain and available for other modules.
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str, owner: str = "magmacrunchmedia", repo: str = "magmacrunch.com"):
        self.token = token
        self.owner = owner
        self.repo = repo
        self._http = httpx.Client(
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    @property
    def _repo_path(self) -> str:
        return f"/repos/{self.owner}/{self.repo}"

    def _url(self, path: str) -> str:
        """Build full URL from a relative path."""
        if path.startswith("http"):
            return path
        return f"{self.BASE_URL}{path}"

    def get(self, path: str) -> dict:
        """Send a GET request to the GitHub API."""
        url = self._url(path)
        resp = self._http.get(url)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, data: dict | None = None) -> dict | None:
        """Send a POST request to the GitHub API."""
        url = self._url(path)
        resp = self._http.post(url, json=data)
        if resp.status_code == 204:
            return None
        resp.raise_for_status()
        return resp.json()

    def patch(self, path: str, data: dict | None = None) -> dict:
        """Send a PATCH request to the GitHub API."""
        url = self._url(path)
        resp = self._http.patch(url, json=data)
        resp.raise_for_status()
        return resp.json()

    def put(self, path: str, data: dict | None = None) -> dict:
        """Send a PUT request to the GitHub API."""
        url = self._url(path)
        resp = self._http.put(url, json=data)
        resp.raise_for_status()
        return resp.json()

    def delete(self, path: str) -> None:
        """Send a DELETE request to the GitHub API."""
        url = self._url(path)
        resp = self._http.delete(url)
        resp.raise_for_status()

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def repo_info(self) -> dict:
        """Get repository metadata."""
        return self.get(self._repo_path)

    def get_file(self, path: str) -> tuple[str, str]:
        """Read a file's content and SHA from the repo.

        Returns (content, sha). SHA is needed for updates.
        """
        data = self.get(f"{self._repo_path}/contents/{path}")
        content = base64.b64decode(data["content"]).decode("utf-8")
        return content, data["sha"]

    def put_file(self, path: str, content: str, message: str, sha: str | None = None) -> dict:
        """Create or update a single file in the repo."""
        payload: dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        }
        if sha:
            payload["sha"] = sha
        return self.put(f"{self._repo_path}/contents/{path}", payload)

    def list_workflow_runs(self, limit: int = 100) -> list[dict]:
        """List recent workflow runs."""
        data = self.get(f"{self._repo_path}/actions/runs?per_page={limit}")
        return data.get("workflow_runs", [])

    def get_workflow_file(self, name: str) -> str:
        """Resolve a friendly workflow name to its file name."""
        # Try exact match first
        if name in WORKFLOWS:
            return WORKFLOWS[name]
        # Try case-insensitive match
        name_lower = name.lower()
        for friendly, filename in WORKFLOWS.items():
            if friendly.lower() == name_lower:
                return filename
        # Try partial match
        for friendly, filename in WORKFLOWS.items():
            if name_lower in friendly.lower():
                return filename
        raise KeyError(f"Unknown workflow: {name!r}. Available: {', '.join(WORKFLOWS.keys())}")

    def trigger_workflow(self, name: str, ref: str = "main") -> None:
        """Trigger a workflow_dispatch event."""
        workflow_file = self.get_workflow_file(name)
        self.post(
            f"{self._repo_path}/actions/workflows/{workflow_file}/dispatches",
            {"ref": ref},
        )

    def list_issues(self, *, labels: str = "", state: str = "open", limit: int = 30) -> list[dict]:
        """List issues with optional filters."""
        params = f"state={state}&per_page={limit}"
        if labels:
            params += f"&labels={labels}"
        return self.get(f"{self._repo_path}/issues?{params}")

    def create_issue(self, title: str, body: str = "", labels: list[str] | None = None) -> dict:
        """Create a new issue."""
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        return self.post(f"{self._repo_path}/issues", payload)

    def close_issue(self, number: int) -> dict:
        """Close an issue."""
        return self.patch(f"{self._repo_path}/issues/{number}", {"state": "closed"})

    def close(self):
        """Close the HTTP client."""
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
