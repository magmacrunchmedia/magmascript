"""The Asthenosphere - MagmaScript's explicit-memory tier.

The layer beneath the lithosphere. Where the dynamic tier hands you Python
objects and a garbage collector, this one hands you bytes and a shovel, then
narrates every mistake you make with them.
"""

from __future__ import annotations

from typing import Any

from magmascript.lang.astheno.numeric import (
    SPECS,
    AsthenoTypeError,
    Fixed,
    NumSpec,
    binary_op,
    coerce,
    negate,
    set_warn_hook,
    warn,
)
from magmascript.lang.astheno.arena import (
    Arena,
    AreaDoesNotExist,
    AsthenoError,
    Block,
    Pine,
    Quicksand,
    current_site,
    set_site_hook,
)
from magmascript.lang.astheno.dump import arena_summary, bathysphere, leak_report


class SpecHandle:
    """A width, usable as both a constructor and a type reference.

    ``i32(5)`` builds a value; ``osmosis(x, i32)`` and ``p.peek(i32)`` pass the
    same name as a type. One object serves both so there is only one spelling
    of a width in the language.
    """

    __slots__ = ("spec",)

    def __init__(self, spec: NumSpec) -> None:
        self.spec = spec

    def __call__(self, value: Any = 0) -> Fixed:
        return coerce(value, self.spec, context=f"{self.spec.name}()")

    def __repr__(self) -> str:
        return self.spec.name

    def __str__(self) -> str:
        return self.spec.name


SPEC_HANDLES: dict[str, SpecHandle] = {
    name: SpecHandle(spec) for name, spec in SPECS.items()
}


def resolve_spec(value: Any, *, who: str) -> NumSpec:
    """Accept a SpecHandle, a NumSpec, or a width's name."""
    if isinstance(value, SpecHandle):
        return value.spec
    if isinstance(value, NumSpec):
        return value
    if isinstance(value, str) and value in SPECS:
        return SPECS[value]
    known = ", ".join(SPECS)
    raise AsthenoTypeError(f"{who} expected a width ({known}), got {value!r}")


def builtin_osmosis(value: Any, spec: Any) -> Fixed:
    """Convert between widths explicitly, reporting anything lost."""
    target = resolve_spec(spec, who="osmosis()")
    origin = value.spec.name if isinstance(value, Fixed) else type(value).__name__
    return coerce(value, target, context=f"osmosis({origin} -> {target.name})")


def builtin_widthof(value: Any) -> int:
    """Bytes occupied by a fixed-width value or width."""
    if isinstance(value, Fixed):
        return value.spec.bits // 8
    return resolve_spec(value, who="widthof()").bits // 8


# One arena per running program. The interpreter swaps this in and out around
# run(), the same way it does the warning hook, so a script cannot see another
# script's memory and tests stay isolated.
_arena: Arena | None = None


def set_arena(arena: Arena | None) -> Arena | None:
    global _arena
    previous = _arena
    _arena = arena
    return previous


def current_arena() -> Arena:
    global _arena
    if _arena is None:
        _arena = Arena()
    return _arena


def builtin_garrison(what: Any = None) -> Pine:
    """Claim ground. Takes a byte count or a floorplan."""
    fields = getattr(what, "fields", None)
    if fields is not None:
        pine = current_arena().garrison(what.size, label=what.name)
        return pine.typed(what)
    if isinstance(what, Fixed):
        what = what.value
    if isinstance(what, bool) or not isinstance(what, int):
        raise AsthenoError(
            f"garrison() expected a byte count or a floorplan, "
            f"got {type(what).__name__}"
        )
    return current_arena().garrison(what)


def builtin_scorch(pine: Any) -> None:
    if not isinstance(pine, Pine):
        raise AsthenoError(f"scorch() expected a pine, got {type(pine).__name__}")
    current_arena().scorch(pine)


def builtin_bathysphere(pine: Any) -> None:
    print(bathysphere(pine))


def builtin_arena() -> None:
    print(arena_summary(current_arena()))


def builtin_sizeof(what: Any) -> int:
    size = getattr(what, "size", None)
    if size is not None and getattr(what, "fields", None) is not None:
        return size
    if isinstance(what, Pine):
        return what.size
    return builtin_widthof(what)


def builtin_alignof(what: Any) -> int:
    align = getattr(what, "align", None)
    if align is not None:
        return align
    return builtin_widthof(what)


def builtin_layout(what: Any) -> None:
    from magmascript.lang.astheno.floorplan import describe_layout

    print(describe_layout(what))


ASTHENO_BUILTINS: dict[str, Any] = {
    **SPEC_HANDLES,
    "osmosis": builtin_osmosis,
    "widthof": builtin_widthof,
    "garrison": builtin_garrison,
    "scorch": builtin_scorch,
    "bathysphere": builtin_bathysphere,
    "arena": builtin_arena,
    "sizeof": builtin_sizeof,
    "alignof": builtin_alignof,
    "layout": builtin_layout,
}

__all__ = [
    "ASTHENO_BUILTINS",
    "Arena",
    "AreaDoesNotExist",
    "AsthenoError",
    "Block",
    "Pine",
    "Quicksand",
    "arena_summary",
    "bathysphere",
    "current_arena",
    "current_site",
    "leak_report",
    "set_arena",
    "set_site_hook",
    "SPECS",
    "SPEC_HANDLES",
    "AsthenoTypeError",
    "Fixed",
    "NumSpec",
    "SpecHandle",
    "binary_op",
    "coerce",
    "negate",
    "resolve_spec",
    "set_warn_hook",
    "warn",
]
