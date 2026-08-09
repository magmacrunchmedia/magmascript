"""Output formatting helpers for CLI and DSL."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any


def format_table(items: list[Any], columns: list[str] | None = None) -> str:
    """Format a list of dataclass instances or dicts as an aligned text table.

    Args:
        items: List of dataclass instances or dicts
        columns: Column names to display. If None, uses all fields.
    """
    if not items:
        return "(no results)"

    # Get columns from first item
    if columns is None:
        first = items[0]
        if is_dataclass(first) and not isinstance(first, type):
            columns = [f.name for f in first.__dataclass_fields__.values()]
        elif isinstance(first, dict):
            columns = list(first.keys())
        else:
            return str(first)

    # Extract values
    rows = []
    for item in items:
        if is_dataclass(item) and not isinstance(item, type):
            d = asdict(item)
        elif isinstance(item, dict):
            d = item
        else:
            d = {"value": item}
        rows.append([str(d.get(col, "")) for col in columns])

    # Calculate widths
    widths = [len(col) for col in columns]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    # Build table
    header = "  ".join(col.ljust(widths[i]) for i, col in enumerate(columns))
    sep = "  ".join("-" * widths[i] for i in range(len(columns)))
    lines = [header, sep]
    for row in rows:
        lines.append("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))

    return "\n".join(lines)


def format_json(data: Any, *, indent: int = 2) -> str:
    """Format data as JSON string."""
    if is_dataclass(data) and not isinstance(data, type):
        data = asdict(data)
    return json.dumps(data, indent=indent, default=str)


def format_plain(text: str) -> str:
    """Pass-through for plain text (already formatted by the MCP server)."""
    return text


def format_list(items: list[Any], *, key: str | None = None) -> str:
    """Format a list as a numbered text list."""
    if not items:
        return "(no results)"
    lines = []
    for i, item in enumerate(items, 1):
        if is_dataclass(item) and not isinstance(item, type):
            d = asdict(item)
            if key and key in d:
                lines.append(f"{i}. {d[key]}")
            else:
                # Use the first field or str representation
                first_val = next(iter(d.values()), str(item))
                lines.append(f"{i}. {first_val}")
        elif isinstance(item, dict):
            val = item.get(key, str(item)) if key else str(item)
            lines.append(f"{i}. {val}")
        else:
            lines.append(f"{i}. {item}")
    return "\n".join(lines)


FORMATTERS = {
    "table": format_table,
    "json": format_json,
    "plain": format_plain,
    "list": format_list,
}


def format_output(data: Any, fmt: str = "plain", **kwargs) -> str:
    """Format output using the specified formatter.

    Args:
        data: Data to format
        fmt: Formatter name ('table', 'json', 'plain', 'list')
        **kwargs: Additional arguments passed to the formatter
    """
    formatter = FORMATTERS.get(fmt, format_plain)
    return formatter(data, **kwargs)
