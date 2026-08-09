"""Core framework for magmascript."""

from magmascript.core.config import Config, get_config, load_config, set_config
from magmascript.core.registry import get_domain, list_domains, register_domain
from magmascript.core.rpc import RPCClient, RPCError, RPCResponse

__all__ = [
    "Config",
    "RPCClient",
    "RPCError",
    "RPCResponse",
    "get_config",
    "get_domain",
    "list_domains",
    "load_config",
    "register_domain",
    "set_config",
]
