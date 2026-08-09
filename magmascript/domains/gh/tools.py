"""Typed result dataclasses for the GitHub domain."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Workflow:
    """A GitHub Actions workflow with latest run status."""

    name: str
    file: str
    status: str  # success, failure, in_progress, etc.
    conclusion: str
    last_run: str
    event: str
    run_id: int | None = None
    html_url: str = ""


@dataclass
class WorkflowRun:
    """A single workflow run entry."""

    id: int
    status: str
    conclusion: str
    event: str
    created_at: str
    html_url: str
    name: str = ""


@dataclass
class Issue:
    """A GitHub issue."""

    number: int
    title: str
    state: str
    created_at: str
    labels: list[str] = None  # type: ignore[assignment]
    html_url: str = ""

    def __post_init__(self):
        if self.labels is None:
            self.labels = []


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def parse_workflow_runs(runs: list[dict], workflow_map: dict[str, str]) -> list[Workflow]:
    """Parse raw API workflow runs into typed Workflow objects.

    Maps runs to known workflows using the workflow_map (name -> file).
    """
    # Reverse map: file -> name
    file_to_name = {v: k for k, v in workflow_map.items()}

    results = []
    seen_files = set()

    for run in runs:
        path = run.get("path", "")
        # Extract filename from path (e.g. ".github/workflows/ci.yml" -> "ci.yml")
        filename = path.rsplit("/", 1)[-1] if "/" in path else path

        if filename in file_to_name and filename not in seen_files:
            seen_files.add(filename)
            results.append(Workflow(
                name=file_to_name[filename],
                file=filename,
                status=run.get("status", "unknown"),
                conclusion=run.get("conclusion", ""),
                last_run=run.get("created_at", ""),
                event=run.get("event", ""),
                run_id=run.get("id"),
                html_url=run.get("html_url", ""),
            ))

    # Add workflows that had no runs
    for name, filename in workflow_map.items():
        if filename not in seen_files:
            results.append(Workflow(
                name=name,
                file=filename,
                status="never",
                conclusion="",
                last_run="",
                event="",
            ))

    return results


def parse_issues(raw_issues: list[dict]) -> list[Issue]:
    """Parse raw API issue objects into typed Issue objects."""
    results = []
    for issue in raw_issues:
        # Skip pull requests (they show up in /issues endpoint too)
        if "pull_request" in issue:
            continue
        labels = [label.get("name", "") for label in issue.get("labels", [])]
        results.append(Issue(
            number=issue["number"],
            title=issue["title"],
            state=issue.get("state", "unknown"),
            created_at=issue.get("created_at", ""),
            labels=labels,
            html_url=issue.get("html_url", ""),
        ))
    return results
