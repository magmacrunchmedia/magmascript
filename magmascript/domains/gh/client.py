"""GitHub domain — direct API client for GitHub operations.

Uses core/github.py as the shared HTTP layer.
Raises APIError on HTTP failures.
Caches workflow data to avoid rate limits.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
from dataclasses import asdict

from magmascript.core.cache import CacheStore, get_cache
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


def _generate_channels_js(channels: list[dict]) -> str:
    """Generate visual/tv/channels.js from TV channel data."""
    lines = []
    for ch in channels:
        lines.append(
            '    { title: ' + json.dumps(ch.get("title", "")) +
            ', artist: ' + json.dumps(ch.get("artist", "")) +
            ', id: ' + json.dumps(ch.get("id", "")) +
            ', year: ' + json.dumps(ch.get("year", "")) + ' }'
        )
    return 'window.TV_CHANNELS = [\n' + ',\n'.join(lines) + '\n];\n'


class GHClient:
    """GitHub operations client.

    Wraps core/github.py with domain-specific methods that return typed results.
    Raises APIError on HTTP failures.
    Caches workflow data to avoid rate limits.
    """

    def __init__(self, config: Config | None = None):
        cfg = config or get_config()
        self._client = GitHubClient(
            token=cfg.gh.token,
            owner=cfg.gh.owner,
            repo=cfg.gh.repo,
        )
        self._cache = get_cache(enabled=cfg.cache.enabled)
        self._cache_ttl = cfg.cache.ttl_gh

    # ------------------------------------------------------------------
    # Workflows
    # ------------------------------------------------------------------

    def workflows(self, *, use_cache: bool = True) -> list[Workflow]:
        """List all known workflows with their latest run status."""
        cache_key = CacheStore.make_key("workflows")
        if use_cache:
            cached = self._cache.get("gh", cache_key)
            if cached is not None:
                return [Workflow(**w) for w in cached]

        try:
            runs = self._client.list_workflow_runs(limit=100)
        except Exception as e:
            raise _wrap_api_error(e, "list workflows")
        result = parse_workflow_runs(runs, WORKFLOWS)

        if use_cache:
            self._cache.set("gh", cache_key, [asdict(w) for w in result], ttl=self._cache_ttl)

        return result

    def workflow_runs(self, name: str, limit: int = 10, *, use_cache: bool = True) -> list[WorkflowRun]:
        """Get recent runs for a specific workflow."""
        cache_key = CacheStore.make_key("workflow_runs", name=name, limit=limit)
        if use_cache:
            cached = self._cache.get("gh", cache_key)
            if cached is not None:
                return [WorkflowRun(**w) for w in cached]

        try:
            workflow_file = self._client.get_workflow_file(name)
            data = self._client.get(
                f"{self._client._repo_path}/actions/workflows/{workflow_file}/runs?per_page={limit}"
            )
        except Exception as e:
            raise _wrap_api_error(e, f"get runs for {name}")
        runs = data.get("workflow_runs", [])
        result = [
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

        if use_cache:
            self._cache.set("gh", cache_key, [asdict(w) for w in result], ttl=self._cache_ttl)

        return result

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

    def create_discussion(self, title: str, body: str, category_slug: str = "high-scores") -> str:
        """Create a GitHub Discussion using GraphQL."""
        # First, get the repository node ID
        try:
            repo_info = self._client.repo_info()
            repo_node_id = repo_info.get("node_id")
            if not repo_node_id:
                return "Error: Could not get repository node ID"
        except Exception as e:
            raise _wrap_api_error(e, "get repo info for discussion")

        # Get the category ID for the slug
        query = """
        query($owner: String!, $name: String!) {
            repository(owner: $owner, name: $name) {
                discussionCategories(first: 20) {
                    nodes {
                        id
                        slug
                    }
                }
            }
        }
        """
        try:
            result = self._client.graphql(query, {
                "owner": self._client.owner,
                "name": self._client.repo,
            })
            categories = result.get("data", {}).get("repository", {}).get("discussionCategories", {}).get("nodes", [])
            category_id = None
            for cat in categories:
                if cat.get("slug") == category_slug:
                    category_id = cat.get("id")
                    break
            if not category_id:
                return f"Error: Discussion category '{category_slug}' not found"
        except Exception as e:
            raise _wrap_api_error(e, "get discussion categories")

        # Create the discussion
        mutation = """
        mutation($input: CreateDiscussionInput!) {
            createDiscussion(input: $input) {
                discussion {
                    url
                }
            }
        }
        """
        try:
            result = self._client.graphql(mutation, {
                "input": {
                    "repositoryId": repo_node_id,
                    "title": title,
                    "body": body,
                    "categoryCategoryId": category_id,
                }
            })
            url = result.get("data", {}).get("createDiscussion", {}).get("discussion", {}).get("url")
            if url:
                return f"✓ Created discussion: {url}"
            return f"Error: {result.get('errors', 'Unknown error')}"
        except Exception as e:
            raise _wrap_api_error(e, "create discussion")

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

    def commit_multiple(self, files: list[dict[str, str]], message: str) -> str:
        """Commit multiple files atomically.

        Args:
            files: List of {"path": str, "content": str} dicts
            message: Commit message
        """
        try:
            result = self._client.commit_multiple(files, message)
            paths = ", ".join(f["path"] for f in files)
            sha = result.get("sha", "")[:7]
            return f"✓ Committed {len(files)} file(s) ({sha}): {paths}"
        except Exception as e:
            raise _wrap_api_error(e, "commit multiple files")

    def sync_all(self, *, message: str = "", dry_run: bool = False) -> str:
        """Diff local data files against GitHub and commit changes atomically.

        Syncs: jukebox songs, TV channels (JSON + generated JS), themes, scores.

        Args:
            message: Commit message (defaults to "Update via magmascript")
            dry_run: If True, show what would change without committing
        """
        # Find the project root (look for .git directory)
        project_root = Path.cwd()
        while project_root != project_root.parent:
            if (project_root / ".git").is_dir():
                break
            project_root = project_root.parent
        else:
            raise APIError("Not in a git repository")

        admin_dir = project_root / "arcade" / "admin"
        scores_dir = admin_dir / "scores"

        # Define files to sync: (local_path, github_path, label)
        files_to_check = []

        # Jukebox
        jukebox_local = admin_dir / "jukebox-songs.json"
        if jukebox_local.is_file():
            files_to_check.append((jukebox_local, "arcade/admin/jukebox-songs.json", "jukebox"))

        # TV channels JSON
        tv_json_local = admin_dir / "tv-channels.json"
        if tv_json_local.is_file():
            files_to_check.append((tv_json_local, "arcade/admin/tv-channels.json", "tv-json"))

        # Themes
        themes_local = admin_dir / "themes.json"
        if themes_local.is_file():
            files_to_check.append((themes_local, "arcade/admin/themes.json", "themes"))

        # Score files
        if scores_dir.is_dir():
            for f in sorted(scores_dir.glob("*.json")):
                github_path = f"arcade/admin/scores/{f.name}"
                files_to_check.append((f, github_path, f"score:{f.stem}"))

        # Compare each file against GitHub
        files_to_commit = []
        files_changed = []

        for local_path, github_path, label in files_to_check:
            try:
                local_content = local_path.read_text()
            except Exception:
                continue

            try:
                remote_content, _ = self.get_file(github_path)
            except Exception:
                remote_content = None

            if remote_content is None or local_content.strip() != remote_content.strip():
                files_to_commit.append({"path": github_path, "content": local_content})
                files_changed.append(label)

        # If TV JSON changed, also generate and include channels.js
        if "tv-json" in files_changed:
            tv_json_path = admin_dir / "tv-channels.json"
            try:
                channels = json.loads(tv_json_path.read_text())
                channels_js = _generate_channels_js(channels)
                files_to_commit.append({"path": "visual/tv/channels.js", "content": channels_js})
                files_changed.append("tv-js")
            except Exception:
                pass

        # Report
        if not files_changed:
            return "Everything already in sync"

        if dry_run:
            lines = [f"Would commit {len(files_to_commit)} file(s):"]
            for f in files_to_commit:
                lines.append(f"  {f['path']}")
            return "\n".join(lines)

        # Commit atomically
        commit_msg = message or "Update via magmascript"
        result = self.commit_multiple(files_to_commit, commit_msg)
        return result + f"\nFiles changed: {', '.join(files_changed)}"

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
