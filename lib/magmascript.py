"""magmascript Python library — import and use directly.

Usage:
    from lib.magmascript import mcp

    results = mcp.search("aphex twin")
    boards = mcp.scoreboards()
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import magmascript
_parent = str(Path(__file__).resolve().parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from magmascript import MCPClient, get_config  # noqa: E402

# Create a default client instance
config = get_config()
mcp = MCPClient(config)

__all__ = ["mcp", "MCPClient", "get_config"]
