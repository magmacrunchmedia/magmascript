"""bathysphere() - descend and look at the bytes.

A sealed vessel you take down to observe the deep safely. The dump shows the
raw bytes, their ASCII reading, and - when the pine carries a floorplan - which
field each run of bytes belongs to and what it currently decodes to.

Padding is drawn too. A struct that wastes eight bytes to alignment shows those
eight bytes, which turns "reorder your fields" from folklore into something you
can point at.
"""

from __future__ import annotations

from typing import Any

from magmascript.lang.astheno.arena import Arena, Pine
from magmascript.lang.astheno.numeric import Fixed

BYTES_PER_ROW = 16
GROUP = 4


def _column_of(index: int) -> int:
    """Character column where byte `index` starts within a hex row."""
    return index * 3 + index // GROUP


def _hex_row(data: bytes) -> str:
    out = []
    for i, byte in enumerate(data):
        if i and i % GROUP == 0:
            out.append(" ")
        out.append(f"{byte:02x} ")
    return "".join(out).rstrip()


def _ascii_row(data: bytes) -> str:
    return "".join(chr(b) if 32 <= b < 127 else "." for b in data)


def _at(line: int) -> str:
    return f"line {line}" if line else "an unknown line"


def _field_runs(pine: Pine) -> list[tuple[int, int, str]]:
    """(start, length, label) for each field and padding gap in a floorplan."""
    plan = getattr(pine.spec, "fields", None)
    if plan is None:
        return []
    runs: list[tuple[int, int, str]] = []
    cursor = 0
    for field in plan:
        if field.offset > cursor:
            runs.append((cursor, field.offset - cursor, "(padding)"))
        label = f"{field.name}: {field.type_name}"
        try:
            value = field.read(pine)
        except Exception:
            value = None
        if value is not None:
            label += f" = {value}"
        runs.append((field.offset, field.size, label))
        cursor = field.offset + field.size
    size = getattr(pine.spec, "size", cursor)
    if size > cursor:
        runs.append((cursor, size - cursor, "(tail padding)"))
    return runs


def bathysphere(pine: Pine) -> str:
    """Render `pine`'s block as annotated hex."""
    if not isinstance(pine, Pine):
        raise TypeError(f"bathysphere() expected a pine, got {type(pine).__name__}")

    block = pine.block
    state = "alive" if block.alive else f"scorched at {_at(block.scorched_at)}"
    name = getattr(pine.spec, "name", None)
    heading = f"pine 0x{pine.offset:04x}"
    if name:
        heading += f" -> {name}"
    heading += (
        f" ({block.size} bytes, {state}, garrisoned at {_at(block.garrisoned_at)})"
    )

    data = bytes(pine.arena.data[block.offset:block.offset + block.size])
    runs = _field_runs(pine)
    lines = [heading]

    for row_start in range(0, len(data), BYTES_PER_ROW):
        row = data[row_start:row_start + BYTES_PER_ROW]
        hex_part = _hex_row(row)
        width = _column_of(BYTES_PER_ROW - 1) + 2
        lines.append(
            f"  {block.offset + row_start:04x}  {hex_part:<{width}}  |{_ascii_row(row)}|"
        )
        for start, length, label in runs:
            overlap_start = max(start, row_start)
            overlap_end = min(start + length, row_start + len(row))
            if overlap_start >= overlap_end:
                continue
            lead = _column_of(overlap_start - row_start)
            span = (
                _column_of(overlap_end - 1 - row_start)
                + 2
                - _column_of(overlap_start - row_start)
            )
            lines.append(
                f"  {' ' * 4}  {' ' * lead}{'^' * span}"
                f"{' ' * max(1, width - lead - span + 2)}{label}"
            )

    return "\n".join(lines)


def arena_summary(arena: Arena) -> str:
    """One line per block - the REPL's `.arena` view."""
    if not arena.blocks:
        return "arena is empty - nothing garrisoned yet"
    lines = [
        f"arena: {len(arena.data)} bytes, "
        f"{len(arena.live_blocks())} of {len(arena.blocks)} blocks alive"
    ]
    for block in sorted(arena.blocks.values(), key=lambda b: b.offset):
        state = "alive   " if block.alive else "scorched"
        label = f" {block.label}" if block.label else ""
        lines.append(
            f"  0x{block.offset:04x}  {block.size:>6} bytes  {state}"
            f"  garrisoned at {_at(block.garrisoned_at)}{label}"
        )
    return "\n".join(lines)


def leak_report(arena: Arena) -> str | None:
    """`ancient weeds` - what was never scorched. None if the ground is clean."""
    live = arena.live_blocks()
    if not live:
        return None
    total = sum(b.size for b in live)
    where = ", ".join(_at(b.garrisoned_at) for b in sorted(live, key=lambda b: b.garrisoned_at))
    plural = "pine" if len(live) == 1 else "pines"
    return (
        f"ancient weeds - {len(live)} {plural} never scorched "
        f"({total} bytes), garrisoned at {where}"
    )
