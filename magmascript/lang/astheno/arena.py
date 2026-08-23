"""The arena - real bytes, real pointers, and a running commentary.

A ``Pine`` is a pointer: an offset into one ``Arena``'s ``bytearray``, carrying
the extent of the block it came from. Every read and write is checked against
that extent, and every allocation remembers the line that made it.

Two deliberate departures from a real allocator, both in service of the
diagnostics:

* **Blocks are never reused.** A bump allocator hands out fresh ground every
  time. In C, whether a use-after-free explodes depends on what has since been
  written over the block - which is exactly why the bug is so hard to pin down.
  Here a scorched block stays scorched, so the error fires every time, at the
  line that caused it, naming the line that scorched it.
* **Freed blocks keep their contents.** Nothing is zeroed on scorch, so a hex
  dump of a scorched block still shows what was there. Reading it is an error;
  looking at it from outside the program is not.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from magmascript.lang.astheno.numeric import Fixed, NumSpec, _wrap_int, coerce

ALIGNMENT = 8

# The first bytes of every arena are reserved and never handed out, so offset 0
# can mean "points at nothing" - the same trick as an unmapped zero page.
NULL_ZONE = 8


class AsthenoError(Exception):
    """An Asthenosphere fault, carrying the vocabulary it reports under."""

    prefix = "fire toad"


class Quicksand(AsthenoError):
    """Ground that looks solid and isn't - a scorched block, touched again."""

    prefix = "quicksand"


class AreaDoesNotExist(AsthenoError):
    """An access outside the block it claims to be inside."""

    prefix = "area does not exist"


# The interpreter installs this so allocations can record the line that made
# them. Without a hook, sites are reported as unknown.
_site_hook: Callable[[], int] | None = None


def set_site_hook(fn: Callable[[], int] | None) -> Callable[[], int] | None:
    global _site_hook
    previous = _site_hook
    _site_hook = fn
    return previous


def current_site() -> int:
    return _site_hook() if _site_hook is not None else 0


def _at(line: int) -> str:
    return f"line {line}" if line else "an unknown line"


@dataclass
class Block:
    offset: int
    size: int
    alive: bool = True
    garrisoned_at: int = 0
    scorched_at: int = 0
    label: str = ""


@dataclass
class Arena:
    """One contiguous region of bytes plus the bookkeeping to explain it."""

    data: bytearray = field(default_factory=lambda: bytearray(NULL_ZONE))
    blocks: dict[int, Block] = field(default_factory=dict)

    def block_containing(self, offset: int) -> Block | None:
        for block in self.blocks.values():
            if block.offset <= offset < block.offset + block.size:
                return block
        return None

    def garrison(self, size: int, label: str = "") -> "Pine":
        if size <= 0:
            raise AsthenoError(f"garrison() needs a positive size, got {size}")
        offset = len(self.data)
        padding = (-offset) % ALIGNMENT
        if padding:
            self.data.extend(b"\x00" * padding)
            offset += padding
        self.data.extend(b"\x00" * size)
        block = Block(offset=offset, size=size, garrisoned_at=current_site(), label=label)
        self.blocks[offset] = block
        return Pine(offset, self, block)

    def scorch(self, pine: "Pine") -> None:
        block = pine.block
        if pine.offset != block.offset:
            raise AsthenoError(
                f"scorch() needs the pine that garrison() returned - this one "
                f"points {pine.offset - block.offset} bytes into its block"
            )
        if not block.alive:
            raise Quicksand(
                f"this ground was already scorched at {_at(block.scorched_at)}"
            )
        block.alive = False
        block.scorched_at = current_site()

    def live_blocks(self) -> list[Block]:
        return [b for b in self.blocks.values() if b.alive]

    def total_garrisoned(self) -> int:
        return sum(b.size for b in self.blocks.values())


@dataclass(frozen=True)
class Pine:
    """A pointer: where it points, and the block that bounds it."""

    offset: int
    arena: Arena = field(repr=False, compare=False)
    block: Block = field(repr=False, compare=False)
    spec: Any = None

    # --- checking -------------------------------------------------------

    def _check(self, at: int, nbytes: int) -> int:
        block = self.block
        if not block.alive:
            raise Quicksand(
                f"this ground was scorched at {_at(block.scorched_at)} "
                f"(garrisoned at {_at(block.garrisoned_at)})"
            )
        start = self.offset + at
        end = start + nbytes
        if start < block.offset or end > block.offset + block.size:
            rel = start - block.offset
            raise AreaDoesNotExist(
                f"byte {rel}..{rel + nbytes - 1} is outside this pine's block, "
                f"which covers 0..{block.size - 1} "
                f"({block.size} bytes garrisoned at {_at(block.garrisoned_at)})"
            )
        return start

    # --- typed access ---------------------------------------------------

    def peek(self, spec: Any = None, at: int = 0) -> Fixed:
        from magmascript.lang.astheno import resolve_spec

        resolved = resolve_spec(spec if spec is not None else self.spec, who="peek()")
        nbytes = resolved.bits // 8
        start = self._check(at, nbytes)
        raw = bytes(self.arena.data[start:start + nbytes])
        return _decode(raw, resolved)

    def poke(self, spec: Any, value: Any = None, at: int = 0) -> Any:
        from magmascript.lang.astheno import resolve_spec

        # poke(value) is allowed on a typed pine; poke(spec, value) otherwise.
        if value is None and self.spec is not None and not _looks_like_spec(spec):
            value, spec = spec, self.spec
        resolved = resolve_spec(spec, who="poke()")
        nbytes = resolved.bits // 8
        start = self._check(at, nbytes)
        fixed = coerce(value, resolved, context="poke()")
        self.arena.data[start:start + nbytes] = _encode(fixed, resolved)
        return fixed

    # --- raw byte access ------------------------------------------------

    def read_byte(self, index: int) -> int:
        start = self._check(index, 1)
        return self.arena.data[start]

    def write_byte(self, index: int, value: Any) -> int:
        start = self._check(index, 1)
        raw = value.value if isinstance(value, Fixed) else value
        if not isinstance(raw, int) or isinstance(raw, bool):
            raise AsthenoError(
                f"a byte must be an integer, got {type(value).__name__}"
            )
        self.arena.data[start] = raw & 0xFF
        return raw & 0xFF

    # --- arithmetic -----------------------------------------------------

    def shifted(self, delta: int) -> "Pine":
        return Pine(self.offset + delta, self.arena, self.block, self.spec)

    def typed(self, spec: Any) -> "Pine":
        return Pine(self.offset, self.arena, self.block, spec)

    @property
    def alive(self) -> bool:
        return self.block.alive

    @property
    def size(self) -> int:
        """Bytes remaining in the block from where this pine points."""
        return self.block.offset + self.block.size - self.offset

    def __len__(self) -> int:
        return self.size

    def __str__(self) -> str:
        state = "alive" if self.block.alive else "scorched"
        return f"pine 0x{self.offset:04x} ({self.size} bytes, {state})"

    def __repr__(self) -> str:
        return self.__str__()


def _looks_like_spec(value: Any) -> bool:
    from magmascript.lang.astheno import SpecHandle

    return isinstance(value, (SpecHandle, NumSpec)) or (
        isinstance(value, str) and value in __import__(
            "magmascript.lang.astheno.numeric", fromlist=["SPECS"]
        ).SPECS
    )


def _encode(fixed: Fixed, spec: NumSpec) -> bytes:
    import struct

    if spec.is_float:
        return struct.pack("<f" if spec.bits == 32 else "<d", float(fixed.value))
    return int(fixed.value).to_bytes(
        spec.bits // 8, "little", signed=spec.signed
    )


def _decode(raw: bytes, spec: NumSpec) -> Fixed:
    import struct

    if spec.is_float:
        return Fixed(struct.unpack("<f" if spec.bits == 32 else "<d", raw)[0], spec)
    return Fixed(int.from_bytes(raw, "little", signed=spec.signed), spec)
