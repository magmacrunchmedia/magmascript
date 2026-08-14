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
class PIConfig:
    """Raspberry Pi SSH configuration."""

    host: str = "192.168.1.16"
    user: str = "jake"


@dataclass
class MC1Config:
    """MC1 Windows PC SSH configuration."""

    host: str = "100.75.220.87"
    user: str = "magma"


@dataclass
class GHConfig:
    """GitHub API configuration."""

    token: str = ""
    owner: str = "magmacrunchmedia"
    repo: str = "magmacrunch.com"


@dataclass
class MediaConfig:
    """Media search provider API keys."""

    pexels_key: str = ""
    pixabay_key: str = ""


@dataclass
class CacheConfig:
    """Cache configuration."""

    enabled: bool = True
    dir: str = ""
    ttl_media: int = 86400  # 24h
    ttl_scores: int = 3600  # 1h
    ttl_gh: int = 300  # 5min


@dataclass
class DiscordConfig:
    """Discord webhook configuration."""

    webhook_url: str = ""


@dataclass
class ProjectConfig:
    """Project root configuration."""

    root: str = ""


@dataclass
class Config:
    """Top-level magmascript configuration."""

    mcp: MCPConfig = field(default_factory=MCPConfig)
    pi: PIConfig = field(default_factory=PIConfig)
    mc1: MC1Config = field(default_factory=MC1Config)
    gh: GHConfig = field(default_factory=GHConfig)
    media: MediaConfig = field(default_factory=MediaConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    discord: DiscordConfig = field(default_factory=DiscordConfig)
    project: ProjectConfig = field(default_factory=ProjectConfig)


def _load_toml(path: Path) -> dict:
    """Load a TOML file. Returns empty dict if not found."""
    if not path.is_file():
        return {}
    try:
        import tomllib

        return tomllib.loads(path.read_text())
    except ImportError:
        # Python < 3.11
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
    pi_section = toml.get("pi", {})
    mc1_section = toml.get("mc1", {})
    gh_section = toml.get("gh", {})
    media_section = toml.get("media", {})
    cache_section = toml.get("cache", {})
    discord_section = toml.get("discord", {})
    project_section = toml.get("project", {})

    return Config(
        mcp=MCPConfig(
            url=os.environ.get(f"{env_prefix}URL", mcp_section.get("url", DEFAULT_MCP_URL)),
            api_key=os.environ.get(f"{env_prefix}API_KEY")
            or os.environ.get("MCP_API_KEY", "")
            or mcp_section.get("api_key", ""),
        ),
        pi=PIConfig(
            host=os.environ.get(f"{env_prefix}PI_HOST", pi_section.get("host", "192.168.1.16")),
            user=os.environ.get(f"{env_prefix}PI_USER", pi_section.get("user", "jake")),
        ),
        mc1=MC1Config(
            host=os.environ.get(f"{env_prefix}MC1_HOST", mc1_section.get("host", "100.75.220.87")),
            user=os.environ.get(f"{env_prefix}MC1_USER", mc1_section.get("user", "magma")),
        ),
        gh=GHConfig(
            token=os.environ.get(f"{env_prefix}GH_TOKEN")
            or os.environ.get("GITHUB_TOKEN", "")
            or gh_section.get("token", ""),
            owner=os.environ.get(f"{env_prefix}GH_OWNER", gh_section.get("owner", "magmacrunchmedia")),
            repo=os.environ.get(f"{env_prefix}GH_REPO", gh_section.get("repo", "magmacrunch.com")),
        ),
        media=MediaConfig(
            pexels_key=os.environ.get(f"{env_prefix}PEXELS_KEY", media_section.get("pexels_key", "")),
            pixabay_key=os.environ.get(f"{env_prefix}PIXABAY_KEY", media_section.get("pixabay_key", "")),
        ),
        cache=CacheConfig(
            enabled=os.environ.get(f"{env_prefix}CACHE_DISABLED", "") != "1"
            and cache_section.get("enabled", True),
            dir=cache_section.get("dir", ""),
            ttl_media=int(cache_section.get("ttl_media", 86400)),
            ttl_scores=int(cache_section.get("ttl_scores", 3600)),
            ttl_gh=int(cache_section.get("ttl_gh", 300)),
        ),
        discord=DiscordConfig(
            webhook_url=os.environ.get(f"{env_prefix}DISCORD_WEBHOOK_URL")
            or os.environ.get("DISCORD_WEBHOOK_URL", "")
            or discord_section.get("webhook_url", ""),
        ),
        project=ProjectConfig(
            root=os.environ.get(f"{env_prefix}PROJECT_ROOT")
            or os.environ.get("MAGMACRUNCH_ROOT", "")
            or project_section.get("root", ""),
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
