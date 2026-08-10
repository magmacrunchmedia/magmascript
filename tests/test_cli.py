"""Tests for the CLI entry point."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from magmascript.cli import main


class TestCLI:
    def test_help_exits(self):
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["magmascript", "--help"]):
                main()
        assert exc_info.value.code == 0

    def test_unknown_domain(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["magmascript", "unknown"]):
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Unknown domain" in captured.err

    @patch("magmascript.domains.mcp.MCPClient")
    def test_search_action(self, mock_client_cls, capsys):
        mock_client = MagicMock()
        mock_client.search.return_value = []
        mock_client_cls.return_value = mock_client

        with patch("sys.argv", ["magmascript", "mcp", "search", "test"]):
            main()

        mock_client.search.assert_called_once_with("test")
        captured = capsys.readouterr()
        assert "(no results)" in captured.out

    @patch("magmascript.domains.mcp.MCPClient")
    def test_scoreboards_action(self, mock_client_cls, capsys):
        mock_client = MagicMock()
        mock_client.scoreboards.return_value = []
        mock_client_cls.return_value = mock_client

        with patch("sys.argv", ["magmascript", "mcp", "scoreboards"]):
            main()

        mock_client.scoreboards.assert_called_once()
        captured = capsys.readouterr()
        assert "(no results)" in captured.out

    @patch("magmascript.domains.mcp.MCPClient")
    def test_json_format(self, mock_client_cls, capsys):
        mock_client = MagicMock()
        mock_client.search.return_value = []
        mock_client_cls.return_value = mock_client

        with patch("sys.argv", ["magmascript", "mcp", "search", "test", "--json"]):
            main()

        captured = capsys.readouterr()
        assert "[]" in captured.out


class TestCLIBrandCommands:
    def test_magma_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["magmascript", "magma", "--help"]):
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "System status dashboard" in captured.out

    def test_crunch_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["magmascript", "crunch", "--help"]):
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "pipeline" in captured.out.lower()

    def test_texas_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["magmascript", "texas", "--help"]):
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "full/heavy" in captured.out.lower()

    def test_toast_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["magmascript", "toast", "--help"]):
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "burn/clear" in captured.out.lower()

    def test_crunch_unknown_target(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["magmascript", "crunch", "fake"]):
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Unknown crunch target" in captured.err

    def test_texas_unknown_target(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["magmascript", "texas", "fake"]):
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Unknown texas target" in captured.err

    def test_toast_unknown_target(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["magmascript", "toast", "fake"]):
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Unknown toast target" in captured.err
