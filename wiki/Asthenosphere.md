# The Asthenosphere

The layer beneath the lithosphere. MagmaScript's dynamic tier hands you Python
objects and a garbage collector; the Asthenosphere hands you bytes and a shovel,
then narrates every mistake you make with them.

## What "low-level" means here

MagmaScript is a tree-walking interpreter written in Python. A C-style tier can
never be *fast* here — an `i32` add still costs a Python dispatch. So low-level
means **explicit memory and layout, not performance**: a real `bytearray` arena,
pointers as offsets, structs with visible padding, and integers that genuinely
wrap.

What you get in exchange is the thing C cannot give you. The interpreter sees
every memory operation, so it can catch the use-after-free, name the line that
leaked, and hex-dump a struct with its fields labelled. C gives you valgrind as
a separate tool. Here it is free and always on.

The guiding rule, applied everywhere: **C's behavior, but narrated.** Wrapping
still wraps — and says so. Padding still pads — and shows you where.

## Vocabulary

| Concept | Name | Release |
|---|---|---|
| the tier | *Asthenosphere* | Asthenosphere |
| allocate | `garrison(n)` | Martial Law in Garrison Oaks (2018) |
| free | `scorch(p)` | Scorched Earth |
| pointer | `pine` | Pine (2016) |
| inspect / hex dump | `bathysphere(p)` | Bathysphere |
| struct | `floorplan Name {}` | Sex Van Floor Plan (2026) |
| convert | `osmosis(v, i32)` | Reverse Osmosis Reversed |
| leak report | `ancient weeds` | Ancient Weeds (2023) |
| use-after-free | `quicksand` | Quicksand |
| out-of-bounds | `area does not exist` | Area Does Not Exist |
| overflow wrap | `spooked` | Spooked (2025) |
| the pre-run pass | `hypnagogia` | Hypnagogia |

`sizeof`, `alignof`, `peek`, `poke` and the width names keep their C spellings.
A C programmer should land softly; theming the load-bearing words would make the
tier harder to read for exactly the people it is for.

## Widths

`i8 i16 i32 i64  u8 u16 u32 u64  f32 f64`

```magmascript
x = i32(5)
b = u8(255)
print(type(x))        // i32
print(widthof(i64))   // 8
```

Arithmetic wraps like C, and reports it:

```magmascript
counter = u8(255)
counter = counter + 1     // spooked: u8 overflow: 255 + 1 = 256, wrapped to 0
```

**There is no integer promotion.** `i32 + i32` is `i32`. `i32 + u8` is an error
telling you to convert. A bare int literal may join any integer width if it
fits. C's promotion rules are its worst-understood corner and reproducing them
would buy nothing.

```magmascript
x = i32(1) + u8(1)          // contemplate: cannot use '+' on i32 and u8
y = i32(1) + osmosis(u8(1), i32)   // fine
```

**`/` truncates toward zero on integer widths**, as C does — not the float
division the dynamic tier gives you:

```magmascript
print(i32(-7) / i32(2))   // -3   (the dynamic tier's -7 / 2 would floor to -4)
```

## The arena

```magmascript
p = garrison(16)      // claim 16 bytes
p.poke(i32, 10)       // write at offset 0
p.poke(i32, 20, 4)    // write at offset 4
print(p.peek(i32))    // 10
p[8] = 72             // raw byte write
print(p[8])           // u8(72)
scorch(p)             // release it
```

`p + n` shifts a pine; `q - p` is the distance between two. Bounds travel with
the pine, so a shifted pine still cannot leave its block.

Two deliberate departures from a real allocator, both for the diagnostics:

- **Blocks are never reused.** In C, whether a use-after-free explodes depends
  on what has since overwritten the block — which is exactly why the bug is so
  hard to pin down. Here a scorched block stays scorched, so the fault fires
  every time, at the line that caused it.
- **Freed blocks keep their contents**, so `bathysphere()` can still show you
  what was there. Reading it from the program is an error; looking from outside
  is not.

## Floorplans

A floor plan is a layout diagram for a space — which is what a struct is for
bytes.

```magmascript
floorplan Point {
    tag: u8
    x: i32
    y: i32
    label: u8[8]
}

layout(Point)
p = garrison(Point)
p.x = i32(10)
print(p.x)
scorch(p)
```

`layout()` prints the padding rows, not just the fields:

```
floorplan Point - 20 bytes, align 4
   off  size  field            type
     0     1  tag              u8
     1     3  -- padding --
     4     4  x                i32
     8     4  y                i32
    12     8  label            u8[8]
  3 of 20 bytes are padding - ordering fields widest-first would pack them tighter
```

Field types may be a width, an array (`u8[16]`), another floorplan, or a pine.
A pine field names what it points at, which may be its own plan — that is how
you write a linked list:

```magmascript
floorplan Node {
    value: i32
    next: pine[Node]
}
```

A null pine reads back as `none`. See `scripts/examples/astheno-list.mgs`.

## bathysphere()

A sealed vessel you take down to observe the deep safely.

```
pine 0x0008 -> Point (20 bytes, alive, garrisoned at line 11)
  0008  07 00 00 00  0a 00 00 00  ec ff ff ff  00 00 00 00  |................|
        ^^                                                  tag: u8 = 7
           ^^^^^^^^                                         (padding)
                     ^^^^^^^^^^^                            x: i32 = 10
                                  ^^^^^^^^^^^               y: i32 = -20
                                               ^^^^^^^^^^^  label: u8[8]
```

In the REPL, `.arena` lists every block, alive or scorched.

## Faults

| Fault | Reported as |
|---|---|
| reading or writing scorched ground | `quicksand`, naming the line that scorched it |
| scorching twice | `quicksand`, naming the first scorch |
| reading outside a block | `area does not exist`, with the block's extent |
| never scorching | `spooked: ancient weeds` at exit, naming each garrison line |
| arithmetic that does not fit | `spooked`, with the exact value and the wrap |

All of them carry the usual caret diagram, and `try`/`haunter` catches them:

```magmascript
try {
    x = p.peek(i32)
} haunter (e) {
    print(f"{e.prefix} — {e.message}")
}
```

Run `scripts/examples/astheno-faults.mgs` to see every one of them fire.

## hypnagogia

The threshold state between waking and sleep — a single pass over the program
just before it runs.

MagmaScript is dynamic, so the pass is deliberately timid. It reports only what
control flow cannot explain away: a name bound *nowhere* in any enclosing scope,
and statements sitting after a `return`, `break`, or `continue`. Order is
ignored on purpose, because `if c { x = 1 }` followed by `print(x)` is legal
when `c` holds.

Findings are warnings, never errors. A program that has always worked keeps
working.

```
spooked: hypnagogia at t.mgs:5: 'nmae' is never given a value - did you mean 'name'?
spooked: hypnagogia at t.mgs:8: this can never run - the return above always leaves first
```

## Compatibility

`floorplan` is the only reserved word the Asthenosphere adds. Everything else —
`garrison`, `scorch`, `bathysphere`, `osmosis`, `sizeof`, the width names — is a
builtin, so a script that already uses one of those names as a variable keeps
working. A program that never mentions the Asthenosphere behaves exactly as it
did before.

## Examples

- `scripts/examples/astheno-list.mgs` — a linked list built by hand
- `scripts/examples/astheno-packing.mgs` — the same fields, two orderings, two sizes
- `scripts/examples/astheno-faults.mgs` — every memory fault, caught and named
