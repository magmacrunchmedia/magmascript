"""Fixed-width numbers for the Asthenosphere.

C's arithmetic, narrated. Values wrap exactly as C would, but every wrap and
every lossy conversion announces itself rather than happening in silence.

Design notes that differ from the dynamic tier on purpose:

* No integer promotion. ``i32 + i32`` is ``i32``; ``i32 + u8`` is an error
  directing you to ``osmosis()``. C's promotion rules are its worst-understood
  corner and there is nothing to gain by reproducing them.
* ``/`` on integer specs is C integer division, truncating toward zero, not the
  float division the dynamic tier gives you. ``i32(-7) / i32(2)`` is ``-3``,
  where Python's floor division would say ``-4``.
* A bare int literal may combine with any integer spec, provided it fits.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class NumSpec:
    name: str
    bits: int
    signed: bool
    is_float: bool = False

    @property
    def low(self) -> int:
        if self.is_float:
            raise AttributeError("float specs have no integer bounds")
        return -(1 << (self.bits - 1)) if self.signed else 0

    @property
    def high(self) -> int:
        if self.is_float:
            raise AttributeError("float specs have no integer bounds")
        return (1 << (self.bits - 1)) - 1 if self.signed else (1 << self.bits) - 1

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return self.name


SPECS: dict[str, NumSpec] = {
    "i8": NumSpec("i8", 8, True),
    "i16": NumSpec("i16", 16, True),
    "i32": NumSpec("i32", 32, True),
    "i64": NumSpec("i64", 64, True),
    "u8": NumSpec("u8", 8, False),
    "u16": NumSpec("u16", 16, False),
    "u32": NumSpec("u32", 32, False),
    "u64": NumSpec("u64", 64, False),
    "f32": NumSpec("f32", 32, True, is_float=True),
    "f64": NumSpec("f64", 64, True, is_float=True),
}


class AsthenoTypeError(TypeError):
    """Mixing widths, or using a value the Asthenosphere cannot accept."""


# The interpreter installs a hook so warnings carry a source location. Without
# one (library use, tests) warnings go to stderr unadorned.
_warn_hook: Callable[[str], None] | None = None


def set_warn_hook(fn: Callable[[str], None] | None) -> Callable[[str], None] | None:
    global _warn_hook
    previous = _warn_hook
    _warn_hook = fn
    return previous


def warn(message: str) -> None:
    if _warn_hook is not None:
        _warn_hook(message)
        return
    import sys
    print(f"spooked: {message}", file=sys.stderr)


def _truncate_float(value: float, spec: NumSpec) -> float:
    if spec.bits == 32:
        return struct.unpack("<f", struct.pack("<f", value))[0]
    return float(value)


def _wrap_int(value: int, spec: NumSpec) -> int:
    mask = (1 << spec.bits) - 1
    v = value & mask
    if spec.signed and v > spec.high:
        v -= 1 << spec.bits
    return v


def coerce(value: Any, spec: NumSpec, *, context: str, quiet: bool = False) -> "Fixed":
    """Build a Fixed of `spec`, wrapping or rounding and saying so."""
    if isinstance(value, Fixed):
        value = value.value
    if isinstance(value, bool):
        value = int(value)

    if spec.is_float:
        if not isinstance(value, (int, float)):
            raise AsthenoTypeError(
                f"{spec.name}() expected a number, got {type(value).__name__}"
            )
        result = _truncate_float(float(value), spec)
        if not quiet and result != float(value):
            warn(f"{context}: {value} loses precision as {spec.name} (became {result})")
        return Fixed(result, spec)

    if isinstance(value, float):
        truncated = int(value)
        if not quiet and truncated != value:
            warn(f"{context}: {value} truncated to {truncated} for {spec.name}")
        value = truncated
    elif not isinstance(value, int):
        raise AsthenoTypeError(
            f"{spec.name}() expected a number, got {type(value).__name__}"
        )

    wrapped = _wrap_int(value, spec)
    if not quiet and wrapped != value:
        warn(
            f"{context}: {value} does not fit {spec.name} "
            f"[{spec.low}, {spec.high}] - wrapped to {wrapped}"
        )
    return Fixed(wrapped, spec)


@dataclass(frozen=True)
class Fixed:
    """A number of a declared width. `value` is already in range for `spec`."""

    value: int | float
    spec: NumSpec

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"{self.spec.name}({self.value})"

    def __hash__(self) -> int:
        return hash((self.value, self.spec.name))

    def __bool__(self) -> bool:
        return self.value != 0


def _unify(left: Any, right: Any, op: str) -> tuple[Any, Any, NumSpec]:
    """Resolve operand specs, or explain why they cannot combine."""
    lf, rf = isinstance(left, Fixed), isinstance(right, Fixed)

    if lf and rf:
        if left.spec is not right.spec:
            raise AsthenoTypeError(
                f"cannot use '{op}' on {left.spec.name} and {right.spec.name} - "
                f"convert one first, e.g. osmosis(x, {left.spec.name})"
            )
        return left.value, right.value, left.spec

    fixed = left if lf else right
    bare = right if lf else left
    if isinstance(bare, bool) or not isinstance(bare, (int, float)):
        raise AsthenoTypeError(
            f"cannot use '{op}' on {fixed.spec.name} and {type(bare).__name__}"
        )
    if isinstance(bare, float) and not fixed.spec.is_float:
        raise AsthenoTypeError(
            f"cannot use '{op}' on {fixed.spec.name} and a float - "
            f"convert first, e.g. osmosis({bare}, {fixed.spec.name})"
        )
    if not fixed.spec.is_float and not (fixed.spec.low <= bare <= fixed.spec.high):
        raise AsthenoTypeError(
            f"{bare} does not fit {fixed.spec.name} "
            f"[{fixed.spec.low}, {fixed.spec.high}]"
        )
    lv = left.value if lf else left
    rv = right.value if rf else right
    return lv, rv, fixed.spec


def _c_divide(a: int, b: int) -> int:
    """Integer division truncating toward zero, as C does."""
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


def _c_remainder(a: int, b: int) -> int:
    return a - _c_divide(a, b) * b


ARITHMETIC = {"+", "-", "*", "/", "%"}
COMPARISON = {"==", "!=", "<", ">", "<=", ">="}


def binary_op(op: str, left: Any, right: Any) -> Any:
    """Apply `op` where at least one operand is a Fixed."""
    if op in COMPARISON:
        lv = left.value if isinstance(left, Fixed) else left
        rv = right.value if isinstance(right, Fixed) else right
        numeric = (int, float)
        if (
            isinstance(lv, bool)
            or isinstance(rv, bool)
            or not isinstance(lv, numeric)
            or not isinstance(rv, numeric)
        ):
            return op == "!="
        return {
            "==": lv == rv,
            "!=": lv != rv,
            "<": lv < rv,
            ">": lv > rv,
            "<=": lv <= rv,
            ">=": lv >= rv,
        }[op]

    if op not in ARITHMETIC:
        raise AsthenoTypeError(f"'{op}' is not defined for fixed-width numbers")

    lv, rv, spec = _unify(left, right, op)

    if op in ("/", "%") and rv == 0:
        raise ZeroDivisionError("Division by zero")

    if spec.is_float:
        if op == "+":
            result = lv + rv
        elif op == "-":
            result = lv - rv
        elif op == "*":
            result = lv * rv
        elif op == "/":
            result = lv / rv
        else:
            result = lv - int(lv / rv) * rv
        return Fixed(_truncate_float(float(result), spec), spec)

    if op == "+":
        exact = lv + rv
    elif op == "-":
        exact = lv - rv
    elif op == "*":
        exact = lv * rv
    elif op == "/":
        exact = _c_divide(lv, rv)
    else:
        exact = _c_remainder(lv, rv)

    wrapped = _wrap_int(exact, spec)
    if wrapped != exact:
        warn(
            f"{spec.name} overflow: {lv} {op} {rv} = {exact}, "
            f"wrapped to {wrapped} (range [{spec.low}, {spec.high}])"
        )
    return Fixed(wrapped, spec)


def negate(value: Fixed) -> Fixed:
    if value.spec.is_float:
        return Fixed(-value.value, value.spec)
    exact = -value.value
    wrapped = _wrap_int(exact, value.spec)
    if wrapped != exact:
        warn(f"{value.spec.name} overflow: -{value.value} wrapped to {wrapped}")
    return Fixed(wrapped, value.spec)
