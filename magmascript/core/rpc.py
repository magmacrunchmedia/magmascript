"""JSON-RPC 2.0 client for MCP streamable-http transport."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx


class RPCError(Exception):
    """JSON-RPC 2.0 error response."""

    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"RPC error {code}: {message}")


@dataclass
class RPCResponse:
    """Parsed JSON-RPC 2.0 response."""

    id: int | str | None
    result: Any = None
    error: RPCError | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class RPCClient:
    """Raw JSON-RPC 2.0 client for MCP streamable-http transport.

    Handles:
    - initialize handshake (legacy protocol)
    - tools/call, tools/list, and any other JSON-RPC methods
    - SSE stream parsing for long responses
    - Thread-safe request IDs
    """

    def __init__(self, url: str, api_key: str, *, client_name: str = "magmascript", client_version: str = "1.0.0"):
        self.url = url
        self.client_name = client_name
        self.client_version = client_version
        self._id = 0
        self._id_lock = threading.Lock()
        self._initialized = False
        self._http = httpx.Client(
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Authorization": f"Bearer {api_key}",
            },
            timeout=30.0,
        )

    def _next_id(self) -> int:
        with self._id_lock:
            self._id += 1
            return self._id

    def _send(self, method: str, params: dict | None = None, *, is_notification: bool = False) -> RPCResponse:
        """Send a JSON-RPC 2.0 request and return the parsed response."""
        msg: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if not is_notification:
            msg["id"] = self._next_id()
        if params is not None:
            msg["params"] = params

        resp = self._http.post(self.url, content=json.dumps(msg))
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")

        # application/json — single response
        if "application/json" in content_type:
            data = resp.json()
            return self._parse_response(data)

        # text/event-stream — SSE with multiple events
        if "text/event-stream" in content_type:
            return self._parse_sse(resp.text)

        # Fallback: try JSON
        try:
            return self._parse_response(resp.json())
        except Exception:
            raise RuntimeError(f"Unexpected content-type: {content_type}")

    def _parse_response(self, data: dict) -> RPCResponse:
        """Parse a single JSON-RPC 2.0 response object."""
        if "error" in data:
            err = data["error"]
            return RPCResponse(
                id=data.get("id"),
                error=RPCError(code=err["code"], message=err["message"], data=err.get("data")),
            )
        return RPCResponse(id=data.get("id"), result=data.get("result"))

    def _parse_sse(self, text: str) -> RPCResponse:
        """Parse SSE stream, collect all JSON-RPC messages, return last response."""
        last_response = RPCResponse(id=None)
        for line in text.splitlines():
            if not line.startswith("data: "):
                continue
            payload = line[6:].strip()
            if not payload:
                continue
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                continue
            parsed = self._parse_response(data)
            if parsed.error or parsed.result is not None:
                last_response = parsed
        return last_response

    def initialize(self) -> dict:
        """Run the MCP initialize handshake. Must be called before call_tool."""
        resp = self._send("initialize", {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": self.client_name, "version": self.client_version},
        })
        if resp.error:
            raise resp.error
        self._send("notifications/initialized", is_notification=True)
        self._initialized = True
        return resp.result

    def call_tool(self, name: str, arguments: dict | None = None) -> str:
        """Call an MCP tool and return the text content."""
        if not self._initialized:
            self.initialize()
        resp = self._send("tools/call", {"name": name, "arguments": arguments or {}})
        if resp.error:
            raise resp.error
        result = resp.result or {}
        if result.get("isError"):
            content = result.get("content", [])
            text = content[0]["text"] if content else "Unknown error"
            raise RuntimeError(text)
        content = result.get("content", [])
        if content and content[0].get("type") == "text":
            return content[0]["text"]
        return json.dumps(result)

    def list_tools(self) -> list[dict]:
        """List all available MCP tools."""
        if not self._initialized:
            self.initialize()
        resp = self._send("tools/list", {})
        if resp.error:
            raise resp.error
        return (resp.result or {}).get("tools", [])

    def raw(self, method: str, params: dict | None = None) -> Any:
        """Send a raw JSON-RPC 2.0 request (for future extensibility)."""
        if not self._initialized and method != "initialize":
            self.initialize()
        resp = self._send(method, params)
        if resp.error:
            raise resp.error
        return resp.result

    def close(self):
        """Close the HTTP client."""
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
