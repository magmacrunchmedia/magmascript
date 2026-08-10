"""Tests for the core commands module (magma, crunch, texas, toast)."""

from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from magmascript.core.commands import (
    magma, crunch, texas, toast,
    MagmaStatus, CrunchResult, ToastResult,
)


# --- Mock result types ---


@dataclass
class MockBackupResult:
    completed: int = 10
    skipped: int = 2
    elapsed_seconds: int = 5
    errors: list[str] = field(default_factory=list)


@dataclass
class MockFetchResult:
    completed: int = 5
    skipped: int = 1
    resolved: int = 3
    errors: list[str] = field(default_factory=list)


@dataclass
class MockBuildResult:
    total_entries: int = 100
    deduplicated: int = 80
    output_file: str = "search-index.json"


@dataclass
class MockBakeResult:
    baked: int = 20
    skipped: int = 5
    errors: list[str] = field(default_factory=list)


@dataclass
class MockPlayerStats:
    name: str = "Test"
    total_entries: int = 10
    games_played: int = 5


@dataclass
class MockScoresReport:
    generated_at: str = "2026-01-01"
    total_games: int = 5
    total_scores: int = 50
    scoreboards: list = field(default_factory=list)
    player_stats: list = field(default_factory=lambda: [MockPlayerStats()])


# --- Tests: magma ---


class TestMagma:
    @patch("magmascript.core.commands.list_domains", return_value=["mb", "pi"])
    @patch("magmascript.core.commands.get_config")
    @patch("magmascript.core.cache.get_cache")
    def test_magma_returns_status(self, mock_cache, mock_config, mock_domains):
        mock_cache.return_value.file_stats.return_value = {
            "total_files": 10,
            "total_size_bytes": 5000,
            "domains": {"mb": {"files": 5}},
        }
        result = magma()
        assert isinstance(result, MagmaStatus)
        assert result.version
        assert "mb" in result.domains
        assert result.cache["total_files"] == 10


# --- Tests: crunch ---


class TestCrunch:
    @patch("magmascript.domains.mb.MusicBrainzClient")
    @patch("magmascript.core.commands._get_project_root")
    def test_crunch_mb(self, mock_root, mock_cls):
        mock_client = MagicMock()
        mock_client.backup.return_value = MockBackupResult()
        mock_cls.return_value = mock_client

        result = crunch("mb")
        assert isinstance(result, CrunchResult)
        assert result.target == "mb"
        assert result.completed == 10
        mock_client.backup.assert_called_once_with(
            dry_run=False, skip_existing=True, stale_only=True
        )
        mock_client.close.assert_called_once()

    @patch("magmascript.domains.lastfm.LastFmClient")
    @patch("magmascript.core.commands._get_project_root")
    def test_crunch_lastfm(self, mock_root, mock_cls):
        mock_client = MagicMock()
        mock_client.fetch.return_value = MockFetchResult()
        mock_cls.return_value = mock_client

        result = crunch("lastfm")
        assert result.target == "lastfm"
        assert result.completed == 5
        mock_client.fetch.assert_called_once_with(
            dry_run=False, skip_existing=True
        )

    @patch("magmascript.domains.search.SearchClient")
    @patch("magmascript.core.commands._get_project_root")
    def test_crunch_search(self, mock_root, mock_cls):
        mock_client = MagicMock()
        mock_client.build.return_value = MockBuildResult()
        mock_cls.return_value = mock_client

        result = crunch("search")
        assert result.target == "search"
        assert result.completed == 100
        assert result.details["deduplicated"] == 80

    @patch("magmascript.domains.archive.ArchiveClient")
    @patch("magmascript.core.commands._get_project_root")
    def test_crunch_archive(self, mock_root, mock_cls):
        mock_client = MagicMock()
        mock_client.bake_cache.return_value = MockBakeResult()
        mock_cls.return_value = mock_client

        result = crunch("archive")
        assert result.target == "archive"
        assert result.completed == 20
        assert result.skipped == 5

    def test_crunch_unknown_target(self):
        with pytest.raises(ValueError, match="Unknown crunch target"):
            crunch("unknown")

    @patch("magmascript.domains.mb.MusicBrainzClient")
    @patch("magmascript.core.commands._get_project_root")
    def test_crunch_dry_run(self, mock_root, mock_cls):
        mock_client = MagicMock()
        mock_client.backup.return_value = MockBackupResult()
        mock_cls.return_value = mock_client

        crunch("mb", dry_run=True)
        mock_client.backup.assert_called_once_with(
            dry_run=True, skip_existing=True, stale_only=True
        )


# --- Tests: texas ---


class TestTexas:
    @patch("magmascript.domains.mb.MusicBrainzClient")
    @patch("magmascript.core.commands._get_project_root")
    def test_texas_mb_force_refresh(self, mock_root, mock_cls):
        mock_client = MagicMock()
        mock_client.backup.return_value = MockBackupResult()
        mock_cls.return_value = mock_client

        result = texas("mb")
        assert result.target == "mb"
        mock_client.backup.assert_called_once_with(
            dry_run=False, skip_existing=False, stale_only=False
        )

    @patch("magmascript.domains.lastfm.LastFmClient")
    @patch("magmascript.core.commands._get_project_root")
    def test_texas_lastfm_force_refresh(self, mock_root, mock_cls):
        mock_client = MagicMock()
        mock_client.fetch.return_value = MockFetchResult()
        mock_cls.return_value = mock_client

        result = texas("lastfm")
        mock_client.fetch.assert_called_once_with(
            dry_run=False, skip_existing=False
        )

    def test_texas_unknown_target(self):
        with pytest.raises(ValueError, match="Unknown texas target"):
            texas("unknown")


# --- Tests: toast ---


class TestToast:
    @patch("magmascript.core.cache.get_cache")
    def test_toast_cache(self, mock_cache_fn):
        mock_cache = MagicMock()
        mock_cache.clear.return_value = 42
        mock_cache_fn.return_value = mock_cache

        result = toast("cache")
        assert isinstance(result, ToastResult)
        assert result.files_cleared == 42
        mock_cache.clear.assert_called_once_with(domain=None)

    @patch("magmascript.core.cache.get_cache")
    def test_toast_cache_domain(self, mock_cache_fn):
        mock_cache = MagicMock()
        mock_cache.clear.return_value = 10
        mock_cache_fn.return_value = mock_cache

        result = toast("cache", domain="scores")
        assert result.files_cleared == 10
        mock_cache.clear.assert_called_once_with(domain="scores")

    @patch("magmascript.core.commands._get_project_root")
    def test_toast_search_index(self, mock_root, tmp_path):
        mock_root.return_value = tmp_path
        index_file = tmp_path / "search-index.json"
        index_file.write_text("{}")

        result = toast("search-index")
        assert result.files_cleared == 1
        assert not index_file.exists()

    @patch("magmascript.core.commands._get_project_root")
    def test_toast_search_index_not_found(self, mock_root, tmp_path):
        mock_root.return_value = tmp_path

        result = toast("search-index")
        assert result.files_cleared == 0
        assert "not found" in result.message

    @patch("magmascript.core.commands._get_project_root")
    def test_toast_mb_cache(self, mock_root, tmp_path):
        mock_root.return_value = tmp_path
        cache_dir = tmp_path / "archive" / "_cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "file1.json").write_text("{}")
        (cache_dir / "file2.json").write_text("{}")
        sub = cache_dir / "sub"
        sub.mkdir()
        (sub / "file3.json").write_text("{}")

        result = toast("mb-cache")
        assert result.files_cleared == 3

    @patch("magmascript.core.commands._get_project_root")
    def test_toast_mb_cache_no_project(self, mock_root):
        mock_root.return_value = None
        result = toast("mb-cache")
        assert "No project root" in result.message

    def test_toast_unknown_target(self):
        with pytest.raises(ValueError, match="Unknown toast target"):
            toast("unknown")

    @patch("magmascript.core.commands._get_project_root")
    @patch("magmascript.core.cache.get_cache")
    def test_toast_all(self, mock_cache_fn, mock_root, tmp_path):
        mock_root.return_value = tmp_path
        mock_cache = MagicMock()
        mock_cache.clear.return_value = 5
        mock_cache_fn.return_value = mock_cache

        result = toast("all")
        assert result.target == "all"
        assert result.files_cleared >= 5


# --- Tests: REPL completion sets ---


class TestReplCompletionSets:
    def test_crunch_targets(self):
        from magmascript.repl import _CRUNCH_TARGETS
        assert "mb" in _CRUNCH_TARGETS
        assert "all" in _CRUNCH_TARGETS
        assert len(_CRUNCH_TARGETS) == 7

    def test_toast_targets(self):
        from magmascript.repl import _TOAST_TARGETS
        assert "cache" in _TOAST_TARGETS
        assert "all" in _TOAST_TARGETS
        assert "mb-cache" in _TOAST_TARGETS

    def test_dot_commands_include_brand(self):
        from magmascript.repl import _DOT_COMMANDS
        assert ".magma" in _DOT_COMMANDS
        assert ".crunch" in _DOT_COMMANDS
        assert ".texas" in _DOT_COMMANDS
        assert ".toast" in _DOT_COMMANDS
