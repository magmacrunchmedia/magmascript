"""CLI command registry.

Provides a decorator-based system for registering CLI commands.
Replaces the if/elif chain in cli.py with a dictionary lookup.

Usage::

    from magmascript.core.registry import command, get_command, list_commands

    @command("run")
    def cmd_run(action, args, fmt):
        ...

    # In cli.py main():
    cmd = get_command(domain)
    if cmd:
        cmd(action, args, fmt)
"""

from __future__ import annotations

from typing import Callable

_commands: dict[str, Callable] = {}


def command(name: str, help_text: str = "") -> Callable:
    """Decorator to register a CLI command.

    The decorated function receives (action, args, fmt) where:
    - action: the subcommand string (e.g., "search")
    - args: remaining arguments list
    - fmt: output format ("table" or "json")
    """
    def decorator(fn: Callable) -> Callable:
        _commands[name] = fn
        fn._help_text = help_text
        return fn
    return decorator


def get_command(name: str) -> Callable | None:
    """Look up a registered command by name."""
    return _commands.get(name)


def list_commands() -> list[str]:
    """Return sorted list of registered command names."""
    return sorted(_commands.keys())


def command_help(name: str) -> str:
    """Return the help text for a command, or empty string."""
    cmd = _commands.get(name)
    return getattr(cmd, "_help_text", "") if cmd else ""
