"""Exception hierarchy for magmascript.

All domain-specific exceptions inherit from MagmascriptError.
"""

from __future__ import annotations

from typing import Any


class MagmascriptError(Exception):
    """Base exception for all magmascript errors."""


class ConfigError(MagmascriptError):
    """Configuration is missing or invalid."""


class SSHError(MagmascriptError):
    """SSH connection or command failed."""

    def __init__(self, message: str, *, host: str = "", code: int = -1):
        super().__init__(message)
        self.host = host
        self.code = code


class APIError(MagmascriptError):
    """HTTP API request failed."""

    def __init__(self, message: str, *, status_code: int = 0, url: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.url = url


class AuthError(APIError):
    """Authentication failed (401/403)."""


class RateLimitError(APIError):
    """Rate limit exceeded (429)."""


class MCPError(MagmascriptError):
    """MCP server returned an error."""

    def __init__(self, message: str, *, code: int = 0, data: Any = None):
        super().__init__(message)
        self.code = code
        self.data = data


class ProviderError(MagmascriptError):
    """A media provider failed."""

    def __init__(self, message: str, *, provider: str = ""):
        super().__init__(message)
        self.provider = provider
