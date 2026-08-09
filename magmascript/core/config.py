"""Configuration loading for magmascript.

Priority: env vars > config file > defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_MCP_URL = "https://magmacrunch.duckdns.org/mcp"
CONFIG_DIR = Path.home() / ".config" / "magmascript"
CONFIG_FILE = CONFIG_DIR / "config.toml"


@dataclass
class MCPConfig:
    """MCP server configuration."""

    url: str = DEFAULT_MCP_URL
    api_key: str = ""


@dataclass
class Config:
    """Top-level magmascript configuration."""

    mcp: MCPConfig = field(default_factory=MCPConfig)


def _load_toml(path: Path) -> dict:
    """Load a TOML file. Returns empty dict if not found or tomli unavailable."""
    if not path.is_file():
        return {}
    try:
        import tomli

        return tomli.loads(path.read_text())
    except ImportError:
        # Python < 3.11 without tomli
        return {}
    except Exception:
        return {}


def load_config(*, config_path: Path | None = None, env_prefix: str = "MAGMA_") -> Config:
    """Load configuration from env vars and config file.

    Args:
        config_path: Override config file path. Defaults to ~/.config/magmascript/config.toml
        env_prefix: Override env var prefix. Defaults to MAGMA_
    """
    cfg_file = config_path or CONFIG_FILE
    toml = _load_toml(cfg_file)
    mcp_section = toml.get("mcp", {})

    return Config(
        mcp=MCPConfig(
            url=os.environ.get(f"{env_prefix}URL", mcp_section.get("url", DEFAULT_MCP_URL)),
            api_key=os.environ.get(f"{env_prefix}API_KEY")
            or os.environ.get("MCP_API_KEY", "")
            or mcp_section.get("api_key", ""),
        ),
    )


_config: Config | None = None


def get_config() -> Config:
    """Get the global config singleton (lazy-loaded)."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_config(config: Config) -> None:
    """Override the global config singleton."""
    global _config
    _config = config
