"""Module registry — domains register themselves here for CLI and DSL discovery."""

from __future__ import annotations

from typing import Any

# Global registry: domain_name -> module/client_class
REGISTRY: dict[str, Any] = {}


def register_domain(name: str, module: Any) -> None:
    """Register a domain (e.g., 'mcp') with its client module.

    Args:
        name: Domain name used in CLI subcommands (e.g., 'mcp')
        module: Module or class that provides the domain's methods
    """
    REGISTRY[name] = module


def get_domain(name: str) -> Any:
    """Get a registered domain by name."""
    if name not in REGISTRY:
        available = ", ".join(REGISTRY.keys()) or "(none)"
        raise KeyError(f"Unknown domain: {name!r}. Available: {available}")
    return REGISTRY[name]


def list_domains() -> list[str]:
    """List all registered domain names."""
    return list(REGISTRY.keys())
