"""Domain modules — auto-imports all registered domains."""

# Importing this package triggers domain registration
from magmascript.domains import mcp  # noqa: F401
from magmascript.domains import pi  # noqa: F401
from magmascript.domains import gh  # noqa: F401
from magmascript.domains import media  # noqa: F401
from magmascript.domains import scores  # noqa: F401
from magmascript.domains import rights  # noqa: F401
from magmascript.domains import archive  # noqa: F401
from magmascript.domains import mb  # noqa: F401

__all__ = ["mcp", "pi", "gh", "media", "scores", "rights", "archive", "mb"]
