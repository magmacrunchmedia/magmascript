"""Floorplans - a layout diagram for a space, which is what a struct is for bytes.

Layout follows C: every field sits at its natural alignment, padding is inserted
to get there, and the whole plan is rounded up to its widest member's alignment
so an array of them stays aligned.

``layout()`` prints the padding rows as well as the fields. Reordering a struct
to save memory is usually folklore passed between programmers; here it is a
thing you can look at.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from magmascript.lang.astheno.arena import AsthenoError, Pine
from magmascript.lang.astheno.numeric import SPECS, Fixed, NumSpec

# A stored pine is an 8-byte absolute offset into the arena. Offset 0 is the
# reserved null zone, so it reads back as `none`.
PINE_SIZE = 8
PINE_ALIGN = 8


@dataclass
class Field:
    name: str
    type_name: str
    offset: int
    size: int
    align: int
    kind: str                      # "scalar" | "array" | "nested" | "pine"
    spec: NumSpec | None = None
    plan: "Floorplan | None" = None
    count: int = 1

    # --- language-level access ------------------------------------------

    def get(self, pine: Pine) -> Any:
        if self.kind == "scalar":
            return pine.peek(self.spec, self.offset)
        if self.kind == "array":
            pine._check(self.offset, self.size)
            return pine.shifted(self.offset).typed(self.spec)
        if self.kind == "nested":
            pine._check(self.offset, self.size)
            return pine.shifted(self.offset).typed(self.plan)
        # pine field
        stored = pine.peek(SPECS["u64"], self.offset).value
        if stored == 0:
            return None
        block = pine.arena.block_containing(stored)
        if block is None:
            raise AsthenoError(
                f"field '{self.name}' holds 0x{stored:x}, which is not inside "
                f"any block this arena handed out"
            )
        return Pine(stored, pine.arena, block, self.plan)

    def set(self, pine: Pine, value: Any) -> Any:
        if self.kind == "scalar":
            return pine.poke(self.spec, value, self.offset)
        if self.kind == "pine":
            if value is None:
                return pine.poke(SPECS["u64"], 0, self.offset)
            if not isinstance(value, Pine):
                raise AsthenoError(
                    f"field '{self.name}' holds a pine, got {type(value).__name__}"
                )
            return pine.poke(SPECS["u64"], value.offset, self.offset)
        raise AsthenoError(
            f"field '{self.name}' is {self.type_name} - assign through it "
            f"(poke, or an index) rather than replacing it wholesale"
        )

    def read(self, pine: Pine) -> Any:
        """A short display value for bathysphere, or None to show nothing."""
        if self.kind == "scalar":
            return pine.peek(self.spec, self.offset).value
        if self.kind == "pine":
            stored = pine.peek(SPECS["u64"], self.offset).value
            return "none" if stored == 0 else f"0x{stored:04x}"
        return None


@dataclass
class Floorplan:
    name: str
    fields: list[Field] = field(default_factory=list)
    size: int = 0
    align: int = 1

    def field_named(self, name: str) -> Field | None:
        for f in self.fields:
            if f.name == name:
                return f
        return None

    @property
    def padding_bytes(self) -> int:
        return self.size - sum(f.size for f in self.fields)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"floorplan {self.name} ({self.size} bytes)"


def _align_up(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


def build_floorplan(
    name: str,
    declared: list[tuple[str, str, int, str]],
    known: dict[str, Floorplan],
) -> Floorplan:
    """Compute offsets, padding, size and alignment for a declared plan.

    `declared` is (field_name, type_name, count, points_to). count > 1 means an
    array; points_to names a pine field's target, which may be this very plan -
    that is how a linked list gets written.
    """
    plan = Floorplan(name=name)
    seen: set[str] = set()
    cursor = 0
    max_align = 1
    self_referencing: list[Field] = []

    for field_name, type_name, count, points_to in declared:
        if field_name in seen:
            raise AsthenoError(f"floorplan {name} declares '{field_name}' twice")
        seen.add(field_name)

        spec: NumSpec | None = None
        nested: Floorplan | None = None

        if type_name in SPECS:
            spec = SPECS[type_name]
            unit, align, kind = spec.bits // 8, spec.bits // 8, "scalar"
        elif type_name == "pine":
            unit, align, kind = PINE_SIZE, PINE_ALIGN, "pine"
            if points_to:
                if points_to == name:
                    nested = None          # patched in below
                elif points_to in known:
                    nested = known[points_to]
                else:
                    raise AsthenoError(
                        f"floorplan {name}: field '{field_name}' points at "
                        f"'{points_to}', which is not a floorplan"
                    )
        elif type_name in known:
            nested = known[type_name]
            unit, align, kind = nested.size, nested.align, "nested"
        elif type_name == name:
            # A plan cannot contain itself; it would be infinitely large.
            raise AsthenoError(
                f"floorplan {name} cannot contain itself - use a `pine` field "
                f"to point at another {name}"
            )
        else:
            raise AsthenoError(
                f"floorplan {name}: unknown type '{type_name}' for field "
                f"'{field_name}'"
            )

        if count > 1:
            kind = "array"
            display = f"{type_name}[{count}]"
            size = unit * count
        elif kind == "pine" and points_to:
            display = f"pine[{points_to}]"
            size = unit
        else:
            display = type_name
            size = unit

        cursor = _align_up(cursor, align)
        built = Field(
                name=field_name,
                type_name=display,
                offset=cursor,
                size=size,
                align=align,
                kind=kind,
                spec=spec,
                plan=nested if kind in ("nested", "pine") else None,
                count=count,
        )
        plan.fields.append(built)
        if kind == "pine" and points_to == name:
            self_referencing.append(built)
        cursor += size
        max_align = max(max_align, align)

    plan.align = max_align
    plan.size = _align_up(cursor, max_align) or max_align
    # A plan can point at itself. Its fields were built before the plan was
    # finished, so close the loop now.
    for built in self_referencing:
        built.plan = plan
    return plan


def describe_layout(what: Any) -> str:
    """The field table, padding included."""
    if not isinstance(what, Floorplan):
        name = getattr(what, "name", type(what).__name__)
        raise AsthenoError(f"layout() expected a floorplan, got {name}")

    lines = [
        f"floorplan {what.name} - {what.size} bytes, align {what.align}",
        f"  {'off':>4}  {'size':>4}  {'field':<16} {'type'}",
    ]
    cursor = 0
    for f in what.fields:
        if f.offset > cursor:
            gap = f.offset - cursor
            lines.append(
                f"  {cursor:>4}  {gap:>4}  {'-- padding --':<16}"
            )
        lines.append(f"  {f.offset:>4}  {f.size:>4}  {f.name:<16} {f.type_name}")
        cursor = f.offset + f.size
    if what.size > cursor:
        lines.append(
            f"  {cursor:>4}  {what.size - cursor:>4}  {'-- tail padding --':<16}"
        )

    wasted = what.padding_bytes
    if wasted:
        lines.append(
            f"  {wasted} of {what.size} bytes are padding - "
            f"ordering fields widest-first would pack them tighter"
        )
    return "\n".join(lines)
