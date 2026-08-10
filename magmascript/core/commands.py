"""Core commands — magma, crunch, texas, toast."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from magmascript.core.config import get_config
from magmascript.core.registry import list_domains


# --- Result types ---


@dataclass
class MagmaStatus:
    version: str
    domains: dict[str, str]
    cache: dict[str, Any]
    last_crunch: str | None = None


@dataclass
class CrunchResult:
    target: str
    completed: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    details: Any = None


@dataclass
class ToastResult:
    target: str
    files_cleared: int = 0
    message: str = ""


# --- Helpers ---


def _get_project_root() -> Path | None:
    config = get_config()
    return Path(config.project.root) if config.project.root else None


def _make_crunch_result(target: str, **kwargs: Any) -> CrunchResult:
    return CrunchResult(target=target, **kwargs)


# --- magma ---


def magma() -> MagmaStatus:
    from magmascript import __version__
    from magmascript.core.cache import get_cache

    config = get_config()

    # Check which domains are configured
    domains: dict[str, str] = {}
    for name in list_domains():
        domains[name] = "registered"

    cache = get_cache()
    stats = cache.file_stats()

    return MagmaStatus(
        version=__version__,
        domains=domains,
        cache={
            "total_files": stats.get("total_files", 0),
            "total_size_bytes": stats.get("total_size_bytes", 0),
            "domains": stats.get("domains", {}),
        },
    )


# --- crunch ---


def crunch(target: str, *, dry_run: bool = False) -> CrunchResult:
    if target == "mb":
        return _crunch_mb(dry_run=dry_run)
    elif target == "lastfm":
        return _crunch_lastfm(dry_run=dry_run)
    elif target == "search":
        return _crunch_search()
    elif target == "archive":
        return _crunch_archive(dry_run=dry_run)
    elif target == "scores":
        return _crunch_scores()
    elif target == "gh":
        return _crunch_gh(dry_run=dry_run)
    elif target == "all":
        return _crunch_all(dry_run=dry_run)
    else:
        raise ValueError(f"Unknown crunch target: {target!r}. Available: mb, lastfm, search, archive, scores, gh, all")


def _crunch_mb(*, dry_run: bool = False) -> CrunchResult:
    from magmascript.domains.mb import MusicBrainzClient

    root = _get_project_root()
    client = MusicBrainzClient(project_root=root)
    try:
        result = client.backup(dry_run=dry_run, skip_existing=True, stale_only=True)
        return CrunchResult(
            target="mb",
            completed=result.completed,
            skipped=result.skipped,
            errors=result.errors,
            elapsed_seconds=result.elapsed_seconds,
        )
    finally:
        client.close()


def _crunch_lastfm(*, dry_run: bool = False) -> CrunchResult:
    from magmascript.domains.lastfm import LastFmClient

    root = _get_project_root()
    client = LastFmClient(project_root=root)
    try:
        result = client.fetch(dry_run=dry_run, skip_existing=True)
        return CrunchResult(
            target="lastfm",
            completed=result.completed,
            skipped=result.skipped,
            errors=result.errors,
        )
    finally:
        client.close()


def _crunch_search() -> CrunchResult:
    from magmascript.domains.search import SearchClient

    root = _get_project_root()
    client = SearchClient(project_root=root)
    result = client.build()
    return CrunchResult(
        target="search",
        completed=result.total_entries,
        details={"deduplicated": result.deduplicated, "output_file": result.output_file},
    )


def _crunch_archive(*, dry_run: bool = False) -> CrunchResult:
    from magmascript.domains.archive import ArchiveClient

    root = _get_project_root()
    client = ArchiveClient(project_root=root)
    result = client.bake_cache(dry_run=dry_run)
    return CrunchResult(
        target="archive",
        completed=result.baked,
        skipped=result.skipped,
        errors=result.errors,
    )


def _crunch_scores() -> CrunchResult:
    from magmascript.domains.scores import ScoresClient

    config = get_config()
    client = ScoresClient(config)
    try:
        result = client.report()
        return CrunchResult(
            target="scores",
            completed=result.total_scores,
            details={"total_games": result.total_games, "player_count": len(result.player_stats)},
        )
    finally:
        client.close()


def _crunch_gh(*, dry_run: bool = False) -> CrunchResult:
    from magmascript.domains.gh import GHClient

    config = get_config()
    client = GHClient(config)
    try:
        msg = client.sync_all(dry_run=dry_run)
        return CrunchResult(target="gh", details={"message": msg})
    finally:
        client.close()


def _crunch_all(*, dry_run: bool = False) -> CrunchResult:
    targets = ["mb", "lastfm", "archive", "search", "gh"]
    total_completed = 0
    total_errors: list[str] = []

    for t in targets:
        result = crunch(t, dry_run=dry_run)
        total_completed += result.completed
        total_errors.extend(result.errors)

    return CrunchResult(
        target="all",
        completed=total_completed,
        errors=total_errors,
    )


# --- texas ---


def texas(target: str, *, dry_run: bool = False) -> CrunchResult:
    if target == "mb":
        return _texas_mb(dry_run=dry_run)
    elif target == "lastfm":
        return _texas_lastfm(dry_run=dry_run)
    elif target == "search":
        return _texas_search(dry_run=dry_run)
    elif target == "archive":
        return _texas_archive(dry_run=dry_run)
    elif target == "scores":
        return _texas_scores()
    elif target == "gh":
        return _texas_gh(dry_run=dry_run)
    elif target == "all":
        return _texas_all(dry_run=dry_run)
    else:
        raise ValueError(f"Unknown texas target: {target!r}. Available: mb, lastfm, search, archive, scores, gh, all")


def _texas_mb(*, dry_run: bool = False) -> CrunchResult:
    from magmascript.domains.mb import MusicBrainzClient

    root = _get_project_root()
    client = MusicBrainzClient(project_root=root)
    try:
        result = client.backup(dry_run=dry_run, skip_existing=False, stale_only=False)
        return CrunchResult(
            target="mb",
            completed=result.completed,
            skipped=result.skipped,
            errors=result.errors,
            elapsed_seconds=result.elapsed_seconds,
        )
    finally:
        client.close()


def _texas_lastfm(*, dry_run: bool = False) -> CrunchResult:
    from magmascript.domains.lastfm import LastFmClient

    root = _get_project_root()
    client = LastFmClient(project_root=root)
    try:
        result = client.fetch(dry_run=dry_run, skip_existing=False)
        return CrunchResult(
            target="lastfm",
            completed=result.completed,
            skipped=result.skipped,
            errors=result.errors,
        )
    finally:
        client.close()


def _texas_search(*, dry_run: bool = False) -> CrunchResult:
    from magmascript.domains.search import SearchClient
    from magmascript.domains.archive import ArchiveClient

    root = _get_project_root()

    search_client = SearchClient(project_root=root)
    search_result = search_client.build()

    archive_client = ArchiveClient(project_root=root)
    bake_result = archive_client.bake_cache(dry_run=dry_run)

    return CrunchResult(
        target="search",
        completed=search_result.total_entries + bake_result.baked,
        skipped=bake_result.skipped,
        errors=bake_result.errors,
        details={
            "search_entries": search_result.total_entries,
            "deduplicated": search_result.deduplicated,
            "baked": bake_result.baked,
        },
    )


def _texas_archive(*, dry_run: bool = False) -> CrunchResult:
    from magmascript.domains.archive import ArchiveClient

    root = _get_project_root()
    client = ArchiveClient(project_root=root)

    stubs = client.generate_stubs()
    bake = client.bake_cache(dry_run=dry_run)
    fmt = client.check_format()

    return CrunchResult(
        target="archive",
        completed=bake.baked,
        skipped=bake.skipped,
        errors=bake.errors + (fmt.get("warnings", []) if isinstance(fmt, dict) else []),
        details={"stubs": stubs, "format_warnings": fmt},
    )


def _texas_scores() -> CrunchResult:
    from magmascript.domains.scores import ScoresClient

    config = get_config()
    client = ScoresClient(config)
    try:
        report = client.report()
        return CrunchResult(
            target="scores",
            completed=report.total_scores,
            details={
                "total_games": report.total_games,
                "player_count": len(report.player_stats),
                "generated_at": report.generated_at,
            },
        )
    finally:
        client.close()


def _texas_gh(*, dry_run: bool = False) -> CrunchResult:
    from magmascript.domains.gh import GHClient

    config = get_config()
    client = GHClient(config)
    try:
        msg = client.sync_all(dry_run=dry_run, message="texas: full sync")
        return CrunchResult(target="gh", details={"message": msg})
    finally:
        client.close()


def _texas_all(*, dry_run: bool = False) -> CrunchResult:
    targets = ["mb", "lastfm", "archive", "search", "scores", "gh"]
    total_completed = 0
    total_errors: list[str] = []

    for t in targets:
        result = texas(t, dry_run=dry_run)
        total_completed += result.completed
        total_errors.extend(result.errors)

    return CrunchResult(
        target="all",
        completed=total_completed,
        errors=total_errors,
    )


# --- toast ---


def toast(target: str, *, domain: str | None = None) -> ToastResult:
    if target == "cache":
        return _toast_cache(domain=domain)
    elif target == "mb-cache":
        return _toast_mb_cache()
    elif target == "lastfm-cache":
        return _toast_lastfm_cache()
    elif target == "scores-cache":
        return _toast_cache(domain="scores")
    elif target == "gh-cache":
        return _toast_cache(domain="gh")
    elif target == "search-index":
        return _toast_search_index()
    elif target == "all":
        return _toast_all()
    else:
        raise ValueError(f"Unknown toast target: {target!r}. Available: cache, mb-cache, lastfm-cache, scores-cache, gh-cache, search-index, all")


def _toast_cache(*, domain: str | None = None) -> ToastResult:
    from magmascript.core.cache import get_cache

    cache = get_cache()
    count = cache.clear(domain=domain)
    label = f" ({domain})" if domain else ""
    return ToastResult(target="cache" + label, files_cleared=count, message=f"Cleared {count} cache entries{label}.")


def _toast_mb_cache() -> ToastResult:
    root = _get_project_root()
    if not root:
        return ToastResult(target="mb-cache", message="No project root configured")

    cache_dir = root / "archive" / "_cache"
    if not cache_dir.is_dir():
        return ToastResult(target="mb-cache", message="MB cache directory not found")

    count = 0
    for f in cache_dir.rglob("*.json"):
        f.unlink(missing_ok=True)
        count += 1

    return ToastResult(target="mb-cache", files_cleared=count, message=f"Cleared {count} MB cache files.")


def _toast_lastfm_cache() -> ToastResult:
    root = _get_project_root()
    if not root:
        return ToastResult(target="lastfm-cache", message="No project root configured")

    cache_dir = root / "arcade" / "admin" / "stats" / "lastfm"
    if not cache_dir.is_dir():
        return ToastResult(target="lastfm-cache", message="Last.fm cache directory not found")

    count = 0
    for f in cache_dir.rglob("*.json"):
        f.unlink(missing_ok=True)
        count += 1

    return ToastResult(target="lastfm-cache", files_cleared=count, message=f"Cleared {count} Last.fm cache files.")


def _toast_search_index() -> ToastResult:
    root = _get_project_root()
    if not root:
        return ToastResult(target="search-index", message="No project root configured")

    index_file = root / "search-index.json"
    if index_file.is_file():
        index_file.unlink()
        return ToastResult(target="search-index", files_cleared=1, message="Removed search-index.json.")
    return ToastResult(target="search-index", message="search-index.json not found.")


def _toast_all() -> ToastResult:
    total = 0
    messages: list[str] = []

    r = _toast_cache()
    total += r.files_cleared
    messages.append(r.message)

    r = _toast_mb_cache()
    total += r.files_cleared
    messages.append(r.message)

    r = _toast_lastfm_cache()
    total += r.files_cleared
    messages.append(r.message)

    r = _toast_search_index()
    total += r.files_cleared
    messages.append(r.message)

    return ToastResult(target="all", files_cleared=total, message=" | ".join(messages))
