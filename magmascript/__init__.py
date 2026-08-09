"""magmascript — a scripting toolkit with domain-first subcommands."""

__version__ = "1.0.0"

from magmascript.core.config import Config, get_config, load_config, set_config
from magmascript.core.registry import get_domain, list_domains, register_domain
from magmascript.core.rpc import RPCClient, RPCError, RPCResponse
from magmascript.core.output import format_output, format_table, format_json

# Import domains to trigger registration
from magmascript import domains  # noqa: F401

# Convenience: expose MCPClient at top level
from magmascript.domains.mcp import MCPClient

__all__ = [
    "__version__",
    "Config",
    "MCPClient",
    "RPCClient",
    "RPCError",
    "RPCResponse",
    "format_output",
    "format_json",
    "format_table",
    "get_config",
    "get_domain",
    "list_domains",
    "load_config",
    "register_domain",
    "set_config",
]
