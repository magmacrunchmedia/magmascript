"""Core framework for magmascript."""

from magmascript.core.cache import CacheStats, CacheStore, get_cache
from magmascript.core.config import Config, get_config, load_config, set_config
from magmascript.core.exceptions import (
    APIError,
    AuthError,
    ConfigError,
    MagmascriptError,
    MCPError,
    ProviderError,
    RateLimitError,
    SSHError,
)
from magmascript.core.registry import get_domain, list_domains, register_domain
from magmascript.core.rpc import RPCClient, RPCError, RPCResponse
from magmascript.core.runner import CommandRunner

__all__ = [
    "APIError",
    "AuthError",
    "CacheStats",
    "CacheStore",
    "CommandRunner",
    "Config",
    "ConfigError",
    "MagmascriptError",
    "MCPError",
    "ProviderError",
    "RPCClient",
    "RPCError",
    "RPCResponse",
    "RateLimitError",
    "SSHError",
    "get_cache",
    "get_config",
    "get_domain",
    "list_domains",
    "load_config",
    "register_domain",
    "set_config",
]
