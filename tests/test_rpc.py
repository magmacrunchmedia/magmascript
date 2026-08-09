"""Tests for the JSON-RPC 2.0 client."""

import json
from unittest.mock import MagicMock, patch

import pytest

from magmascript.core.rpc import RPCClient, RPCError, RPCResponse


class TestRPCResponse:
    def test_ok_when_no_error(self):
        resp = RPCResponse(id=1, result={"tools": []})
        assert resp.ok is True

    def test_not_ok_when_error(self):
        resp = RPCResponse(id=1, error=RPCError(code=-32600, message="Invalid Request"))
        assert resp.ok is False


class TestRPCClient:
    def test_next_id_increments(self):
        client = RPCClient("http://example.com/mcp", "test-key")
        assert client._next_id() == 1
        assert client._next_id() == 2
        assert client._next_id() == 3
        client.close()

    def test_parse_response_success(self):
        client = RPCClient("http://example.com/mcp", "test-key")
        data = {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}
        resp = client._parse_response(data)
        assert resp.ok is True
        assert resp.result == {"tools": []}
        assert resp.id == 1
        client.close()

    def test_parse_response_error(self):
        client = RPCClient("http://example.com/mcp", "test-key")
        data = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32600, "message": "Invalid Request"}}
        resp = client._parse_response(data)
        assert resp.ok is False
        assert resp.error.code == -32600
        assert resp.error.message == "Invalid Request"
        client.close()

    def test_parse_sse(self):
        client = RPCClient("http://example.com/mcp", "test-key")
        sse = (
            "event: message\n"
            'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"hello"}]}}\n'
            "\n"
        )
        resp = client._parse_sse(sse)
        assert resp.ok is True
        assert resp.result["content"][0]["text"] == "hello"
        client.close()

    @patch("magmascript.core.rpc.httpx.Client")
    def test_initialize_handshake(self, mock_httpx):
        mock_client = MagicMock()
        mock_httpx.return_value = mock_client

        # Mock initialize response
        init_resp = MagicMock()
        init_resp.status_code = 200
        init_resp.headers = {"content-type": "application/json"}
        init_resp.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"protocolVersion": "2025-11-25", "serverInfo": {"name": "test"}},
        }

        # Mock initialized notification response
        notif_resp = MagicMock()
        notif_resp.status_code = 200
        notif_resp.headers = {"content-type": "application/json"}
        notif_resp.json.return_value = {"jsonrpc": "2.0"}

        mock_client.post.side_effect = [init_resp, notif_resp]

        client = RPCClient("http://example.com/mcp", "test-key")
        result = client.initialize()

        assert client._initialized is True
        assert result["serverInfo"]["name"] == "test"
        assert mock_client.post.call_count == 2
        client.close()

    @patch("magmascript.core.rpc.httpx.Client")
    def test_call_tool(self, mock_httpx):
        mock_client = MagicMock()
        mock_httpx.return_value = mock_client

        # Mock initialize
        init_resp = MagicMock()
        init_resp.status_code = 200
        init_resp.headers = {"content-type": "application/json"}
        init_resp.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": {}}

        # Mock initialized
        notif_resp = MagicMock()
        notif_resp.status_code = 200
        notif_resp.headers = {"content-type": "application/json"}
        notif_resp.json.return_value = {"jsonrpc": "2.0"}

        # Mock tool call
        tool_resp = MagicMock()
        tool_resp.status_code = 200
        tool_resp.headers = {"content-type": "application/json"}
        tool_resp.json.return_value = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {"content": [{"type": "text", "text": "Found 3 matches"}], "isError": False},
        }

        mock_client.post.side_effect = [init_resp, notif_resp, tool_resp]

        client = RPCClient("http://example.com/mcp", "test-key")
        result = client.call_tool("search_cache", {"query": "test"})

        assert result == "Found 3 matches"
        client.close()

    @patch("magmascript.core.rpc.httpx.Client")
    def test_call_tool_error(self, mock_httpx):
        mock_client = MagicMock()
        mock_httpx.return_value = mock_client

        # Mock initialize
        init_resp = MagicMock()
        init_resp.status_code = 200
        init_resp.headers = {"content-type": "application/json"}
        init_resp.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": {}}

        # Mock initialized
        notif_resp = MagicMock()
        notif_resp.status_code = 200
        notif_resp.headers = {"content-type": "application/json"}
        notif_resp.json.return_value = {"jsonrpc": "2.0"}

        # Mock tool error
        tool_resp = MagicMock()
        tool_resp.status_code = 200
        tool_resp.headers = {"content-type": "application/json"}
        tool_resp.json.return_value = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {"content": [{"type": "text", "text": "Game not found"}], "isError": True},
        }

        mock_client.post.side_effect = [init_resp, notif_resp, tool_resp]

        client = RPCClient("http://example.com/mcp", "test-key")
        with pytest.raises(RuntimeError, match="Game not found"):
            client.call_tool("get_scores", {"game": "nonexistent"})
        client.close()
