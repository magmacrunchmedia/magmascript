"""Tests for the Asthenosphere - MagmaScript's explicit-memory tier."""

from __future__ import annotations

import pytest

from magmascript.lang.astheno import SPECS, AsthenoTypeError, Fixed, coerce
from magmascript.lang.astheno.numeric import binary_op, set_warn_hook
from magmascript.lang.interpreter import Interpreter, RuntimeError as MgsRuntimeError
from magmascript.lang.lexer import Lexer
from magmascript.lang.parser import Parser


def run_src(src: str) -> Interpreter:
    env = Interpreter(source=src)
    env.run(Parser(Lexer(src).tokenize()).parse())
    return env


@pytest.fixture
def warnings():
    """Capture Asthenosphere warnings instead of printing them."""
    captured: list[str] = []
    previous = set_warn_hook(captured.append)
    yield captured
    set_warn_hook(previous)


class TestWidths:
    def test_all_specs_present(self):
        assert set(SPECS) == {
            "i8", "i16", "i32", "i64",
            "u8", "u16", "u32", "u64",
            "f32", "f64",
        }

    @pytest.mark.parametrize(
        "name,low,high",
        [
            ("i8", -128, 127),
            ("u8", 0, 255),
            ("i16", -32768, 32767),
            ("u16", 0, 65535),
            ("i32", -2147483648, 2147483647),
            ("u32", 0, 4294967295),
            ("i64", -(2**63), 2**63 - 1),
            ("u64", 0, 2**64 - 1),
        ],
    )
    def test_integer_bounds(self, name, low, high):
        spec = SPECS[name]
        assert (spec.low, spec.high) == (low, high)

    def test_type_reports_width(self):
        env = run_src("x = i32(5)\nt = type(x)\n")
        assert env.globals.get("t") == "i32"

    def test_widthof(self):
        env = run_src("a = widthof(i64)\nb = widthof(u8)\nc = widthof(i32(0))\n")
        assert env.globals.get("a") == 8
        assert env.globals.get("b") == 1
        assert env.globals.get("c") == 4


class TestWrapping:
    @pytest.mark.parametrize(
        "name,start,expected",
        [
            ("u8", 255, 0),
            ("i8", 127, -128),
            ("u16", 65535, 0),
            ("i16", 32767, -32768),
            ("u32", 4294967295, 0),
            ("i32", 2147483647, -2147483648),
            ("u64", 2**64 - 1, 0),
            ("i64", 2**63 - 1, -(2**63)),
        ],
    )
    def test_wraps_at_top_of_range(self, name, start, expected, warnings):
        spec = SPECS[name]
        result = binary_op("+", coerce(start, spec, context="t", quiet=True), 1)
        assert result == Fixed(expected, spec)

    def test_wrap_below_zero_on_unsigned(self, warnings):
        u8 = SPECS["u8"]
        assert binary_op("-", coerce(0, u8, context="t", quiet=True), 1) == Fixed(255, u8)

    def test_wrapping_is_reported(self, warnings):
        binary_op("+", coerce(255, SPECS["u8"], context="t", quiet=True), 1)
        assert len(warnings) == 1
        assert "u8 overflow" in warnings[0]
        assert "wrapped to 0" in warnings[0]

    def test_in_range_arithmetic_is_silent(self, warnings):
        binary_op("+", coerce(1, SPECS["u8"], context="t", quiet=True), 1)
        assert warnings == []

    def test_construction_out_of_range_wraps_and_warns(self, warnings):
        assert coerce(300, SPECS["u8"], context="u8()") == Fixed(44, SPECS["u8"])
        assert "does not fit u8" in warnings[0]

    def test_negation_can_overflow(self, warnings):
        i8 = SPECS["i8"]
        from magmascript.lang.astheno import negate
        assert negate(coerce(-128, i8, context="t", quiet=True)) == Fixed(-128, i8)
        assert "overflow" in warnings[0]


class TestNoPromotion:
    def test_mixing_widths_is_rejected(self):
        with pytest.raises(AsthenoTypeError, match="i32 and u8"):
            binary_op("+", coerce(1, SPECS["i32"], context="t"), coerce(1, SPECS["u8"], context="t"))

    def test_rejection_names_the_fix(self):
        with pytest.raises(AsthenoTypeError, match="osmosis"):
            binary_op("+", coerce(1, SPECS["i32"], context="t"), coerce(1, SPECS["u8"], context="t"))

    def test_bare_int_adopts_the_fixed_spec(self):
        result = binary_op("+", coerce(1, SPECS["i32"], context="t"), 41)
        assert result == Fixed(42, SPECS["i32"])

    def test_bare_int_must_fit(self):
        with pytest.raises(AsthenoTypeError, match="does not fit u8"):
            binary_op("+", coerce(1, SPECS["u8"], context="t"), 9999)

    def test_bare_float_rejected_for_integer_spec(self):
        with pytest.raises(AsthenoTypeError, match="convert first"):
            binary_op("+", coerce(1, SPECS["i32"], context="t"), 1.5)

    def test_mixing_surfaces_as_contemplate(self):
        with pytest.raises(MgsRuntimeError) as exc:
            run_src("x = i32(1) + u8(1)\n")
        assert exc.value.prefix == "contemplate"


class TestCDivision:
    """`/` truncates toward zero on integer specs, as C does."""

    @pytest.mark.parametrize(
        "a,b,quotient,remainder",
        [(-7, 2, -3, -1), (7, -2, -3, 1), (7, 2, 3, 1), (-7, -2, 3, -1)],
    )
    def test_truncates_toward_zero(self, a, b, quotient, remainder):
        i32 = SPECS["i32"]
        lhs = coerce(a, i32, context="t", quiet=True)
        rhs = coerce(b, i32, context="t", quiet=True)
        assert binary_op("/", lhs, rhs) == Fixed(quotient, i32)
        assert binary_op("%", lhs, rhs) == Fixed(remainder, i32)

    def test_differs_from_python_floor_division(self):
        i32 = SPECS["i32"]
        result = binary_op("/", coerce(-7, i32, context="t", quiet=True), 2)
        assert result.value == -3
        assert -7 // 2 == -4  # what the dynamic tier would give

    def test_division_by_zero(self):
        with pytest.raises(MgsRuntimeError, match="Division by zero"):
            run_src("x = i32(1) / i32(0)\n")


class TestFloats:
    def test_f32_loses_precision_visibly(self, warnings):
        result = coerce(0.1, SPECS["f32"], context="f32()")
        assert result.value != 0.1
        assert "loses precision" in warnings[0]

    def test_f64_keeps_python_float_precision(self, warnings):
        assert coerce(0.1, SPECS["f64"], context="f64()").value == 0.1
        assert warnings == []

    def test_float_truncation_to_int_spec_is_reported(self, warnings):
        assert coerce(3.9, SPECS["i32"], context="i32()") == Fixed(3, SPECS["i32"])
        assert "truncated" in warnings[0]


class TestOsmosis:
    def test_narrowing_wraps_and_reports(self, warnings):
        env = run_src("x = osmosis(i32(70000), i16)\n")
        assert env.globals.get("x") == Fixed(4464, SPECS["i16"])

    def test_widening_is_exact(self, warnings):
        env = run_src("x = osmosis(u8(200), i32)\n")
        assert env.globals.get("x") == Fixed(200, SPECS["i32"])
        assert warnings == []

    def test_rejects_a_non_width(self):
        with pytest.raises(MgsRuntimeError):
            run_src('x = osmosis(i32(1), "banana")\n')


class TestInterpreterIntegration:
    def test_zero_is_falsy(self):
        env = run_src('r = "no"\nif i32(0) { r = "yes" }\n')
        assert env.globals.get("r") == "no"

    def test_non_zero_is_truthy(self):
        env = run_src('r = "no"\nif i32(1) { r = "yes" }\n')
        assert env.globals.get("r") == "yes"

    def test_prints_as_a_bare_number(self):
        env = run_src('x = str(i32(42))\n')
        assert env.globals.get("x") == "42"

    def test_interpolates_as_a_bare_number(self):
        env = run_src('x = f"{i32(42)}"\n')
        assert env.globals.get("x") == "42"

    def test_comparison_across_widths_is_allowed(self):
        env = run_src("a = i32(5) == u8(5)\nb = i32(5) < u8(9)\n")
        assert env.globals.get("a") is True
        assert env.globals.get("b") is True

    def test_int_and_float_unwrap(self):
        env = run_src("a = int(i32(7))\nb = float(i32(7))\n")
        assert env.globals.get("a") == 7
        assert env.globals.get("b") == 7.0

    def test_abs_preserves_width(self):
        env = run_src("x = abs(i32(-5))\n")
        assert env.globals.get("x") == Fixed(5, SPECS["i32"])

    def test_widths_are_shadowable(self):
        """Widths are builtins, not keywords - existing code keeps working."""
        env = run_src("i32 = 5\nx = i32 + 1\n")
        assert env.globals.get("x") == 6

    def test_overflow_warning_names_the_line(self, capsys):
        src = "a = u8(255)\nb = a + 1\n"
        Interpreter(source=src, filename="t.mgs").run(
            Parser(Lexer(src).tokenize()).parse()
        )
        assert "t.mgs:2" in capsys.readouterr().err


# --------------------------------------------------------------------------
# Phase 2 - the arena and pines
# --------------------------------------------------------------------------


class TestGarrisonAndScorch:
    def test_garrison_returns_a_live_pine(self):
        env = run_src("p = garrison(16)\n")
        pine = env.globals.get("p")
        assert pine.alive
        assert pine.size == 16

    def test_offset_zero_is_never_handed_out(self):
        """Offset 0 is the null zone, so a stored pine of 0 means `none`."""
        env = run_src("p = garrison(8)\n")
        assert env.globals.get("p").offset > 0

    def test_scorch_kills_the_block(self):
        env = run_src("p = garrison(8)\nscorch(p)\n")
        assert not env.globals.get("p").alive

    def test_use_after_scorch_is_quicksand(self):
        with pytest.raises(MgsRuntimeError) as exc:
            run_src("p = garrison(8)\nscorch(p)\nx = p.peek(i32)\n")
        assert exc.value.prefix == "quicksand"

    def test_quicksand_names_the_scorch_line(self):
        with pytest.raises(MgsRuntimeError, match="scorched at line 2"):
            run_src("p = garrison(8)\nscorch(p)\nx = p.peek(i32)\n")

    def test_double_scorch_is_quicksand(self):
        with pytest.raises(MgsRuntimeError, match="already scorched at line 2"):
            run_src("p = garrison(8)\nscorch(p)\nscorch(p)\n")

    def test_write_after_scorch_is_quicksand(self):
        with pytest.raises(MgsRuntimeError) as exc:
            run_src("p = garrison(8)\nscorch(p)\np.poke(i32, 1)\n")
        assert exc.value.prefix == "quicksand"

    def test_scorch_requires_the_original_pine(self):
        with pytest.raises(MgsRuntimeError, match="bytes into its block"):
            run_src("p = garrison(16)\nscorch(p + 4)\n")

    def test_garrison_rejects_zero(self):
        with pytest.raises(MgsRuntimeError, match="positive size"):
            run_src("p = garrison(0)\n")

    def test_blocks_are_not_reused(self):
        """A scorched block stays scorched, so use-after-free is deterministic."""
        env = run_src("a = garrison(8)\nscorch(a)\nb = garrison(8)\n")
        assert env.globals.get("a").offset != env.globals.get("b").offset


class TestBounds:
    def test_read_past_the_end(self):
        with pytest.raises(MgsRuntimeError) as exc:
            run_src("p = garrison(8)\nx = p.peek(i32, 6)\n")
        assert exc.value.prefix == "area does not exist"

    def test_byte_index_past_the_end(self):
        with pytest.raises(MgsRuntimeError, match="outside this pine"):
            run_src("p = garrison(4)\nx = p[99]\n")

    def test_negative_index(self):
        with pytest.raises(MgsRuntimeError) as exc:
            run_src("p = garrison(4)\nx = p[0 - 1]\n")
        assert exc.value.prefix == "area does not exist"

    def test_shifted_pine_cannot_escape_its_block(self):
        with pytest.raises(MgsRuntimeError) as exc:
            run_src("p = garrison(8)\nq = p + 6\nx = q.peek(i32)\n")
        assert exc.value.prefix == "area does not exist"

    def test_exact_fit_is_allowed(self):
        env = run_src("p = garrison(8)\np.poke(i32, 7, 4)\nx = p.peek(i32, 4)\n")
        assert env.globals.get("x").value == 7


class TestPeekPoke:
    @pytest.mark.parametrize("width,value", [
        ("i8", -5), ("u8", 200), ("i16", -300), ("u16", 60000),
        ("i32", -100000), ("u32", 4000000000),
        ("i64", -(2**40)), ("u64", 2**63 + 7),
    ])
    def test_round_trip(self, width, value):
        env = run_src(
            f"p = garrison(16)\np.poke({width}, {value})\nx = p.peek({width})\n"
        )
        assert env.globals.get("x").value == value

    def test_float_round_trip(self):
        env = run_src("p = garrison(16)\np.poke(f64, 0.5)\nx = p.peek(f64)\n")
        assert env.globals.get("x").value == 0.5

    def test_bytes_are_little_endian(self):
        env = run_src("p = garrison(8)\np.poke(u32, 1)\na = p[0]\nb = p[3]\n")
        assert env.globals.get("a").value == 1
        assert env.globals.get("b").value == 0

    def test_byte_write_and_read(self):
        env = run_src("p = garrison(4)\np[2] = 65\nx = p[2]\n")
        assert env.globals.get("x").value == 65

    def test_byte_reads_are_u8(self):
        env = run_src("p = garrison(4)\nt = type(p[0])\n")
        assert env.globals.get("t") == "u8"

    def test_memory_starts_zeroed(self):
        env = run_src("p = garrison(8)\nx = p.peek(i64)\n")
        assert env.globals.get("x").value == 0


class TestPointerArithmetic:
    def test_shift_forward(self):
        env = run_src("p = garrison(16)\nq = p + 4\nd = q - p\n")
        assert env.globals.get("d") == 4

    def test_shift_is_visible_through_reads(self):
        env = run_src("p = garrison(16)\np.poke(i32, 9, 8)\nx = (p + 8).peek(i32)\n")
        assert env.globals.get("x").value == 9

    def test_equality_compares_targets(self):
        env = run_src("p = garrison(16)\na = (p + 4) == (p + 4)\nb = (p + 4) == p\n")
        assert env.globals.get("a") is True
        assert env.globals.get("b") is False

    def test_a_live_pine_is_truthy(self):
        env = run_src('p = garrison(8)\nr = "no"\nif p { r = "yes" }\n')
        assert env.globals.get("r") == "yes"

    def test_a_scorched_pine_is_falsy(self):
        env = run_src('p = garrison(8)\nscorch(p)\nr = "no"\nif p { r = "yes" }\n')
        assert env.globals.get("r") == "no"


class TestLeakReport:
    def test_reports_unscorched_blocks(self):
        from magmascript.lang.astheno import leak_report
        env = run_src("a = garrison(16)\nb = garrison(32)\n")
        report = leak_report(env.arena)
        assert "ancient weeds" in report
        assert "2 pines" in report
        assert "48 bytes" in report

    def test_silent_when_everything_is_scorched(self):
        from magmascript.lang.astheno import leak_report
        env = run_src("a = garrison(16)\nscorch(a)\n")
        assert leak_report(env.arena) is None

    def test_names_the_garrison_lines(self):
        from magmascript.lang.astheno import leak_report
        env = run_src("a = garrison(16)\nb = garrison(8)\nscorch(a)\n")
        assert "line 2" in leak_report(env.arena)

    def test_arenas_are_isolated_between_programs(self):
        first = run_src("a = garrison(16)\n")
        second = run_src("b = garrison(8)\n")
        assert len(first.arena.blocks) == 1
        assert len(second.arena.blocks) == 1


class TestBathysphere:
    def test_renders_hex_and_ascii(self):
        from magmascript.lang.astheno import bathysphere
        env = run_src("p = garrison(8)\np[0] = 72\np[1] = 105\n")
        out = bathysphere(env.globals.get("p"))
        assert "48 69" in out
        assert "|Hi" in out

    def test_reports_scorched_state(self):
        from magmascript.lang.astheno import bathysphere
        env = run_src("p = garrison(8)\nscorch(p)\n")
        assert "scorched at line 2" in bathysphere(env.globals.get("p"))

    def test_scorched_memory_keeps_its_contents(self):
        """Reading it is an error; looking from outside is not."""
        from magmascript.lang.astheno import bathysphere
        env = run_src("p = garrison(8)\np[0] = 65\nscorch(p)\n")
        assert "41" in bathysphere(env.globals.get("p"))


# --------------------------------------------------------------------------
# Phase 3 - floorplans
# --------------------------------------------------------------------------


PLAN = """floorplan Point {
    tag: u8
    x: i32
    y: i32
    label: u8[8]
}
"""


class TestFloorplanLayout:
    def test_c_alignment_and_padding(self):
        env = run_src(PLAN)
        plan = env.globals.get("Point")
        assert [(f.name, f.offset, f.size) for f in plan.fields] == [
            ("tag", 0, 1), ("x", 4, 4), ("y", 8, 4), ("label", 12, 8),
        ]
        assert plan.size == 20
        assert plan.align == 4

    def test_padding_is_counted(self):
        env = run_src(PLAN)
        assert env.globals.get("Point").padding_bytes == 3

    def test_reordering_removes_padding(self):
        env = run_src("floorplan A {\n  x: i32\n  y: i32\n  tag: u8\n  pad: u8[3]\n}\n")
        plan = env.globals.get("A")
        assert plan.padding_bytes == 0
        assert plan.size == 12

    def test_tail_padding_rounds_to_alignment(self):
        env = run_src("floorplan T {\n  a: i32\n  b: u8\n}\n")
        plan = env.globals.get("T")
        assert plan.align == 4
        assert plan.size == 8

    def test_sizeof_and_alignof(self):
        env = run_src(PLAN + "s = sizeof(Point)\na = alignof(Point)\n")
        assert env.globals.get("s") == 20
        assert env.globals.get("a") == 4

    def test_layout_shows_padding_rows(self, capsys):
        run_src(PLAN + "layout(Point)\n")
        out = capsys.readouterr().out
        assert "padding" in out
        assert "tag" in out and "i32" in out

    def test_duplicate_field_rejected(self):
        with pytest.raises(MgsRuntimeError, match="twice"):
            run_src("floorplan D {\n  a: i32\n  a: i32\n}\n")

    def test_unknown_type_rejected(self):
        with pytest.raises(MgsRuntimeError, match="unknown type"):
            run_src("floorplan D {\n  a: banana\n}\n")

    def test_empty_floorplan_rejected(self):
        with pytest.raises(Exception):
            run_src("floorplan D {\n}\n")

    def test_direct_self_containment_rejected(self):
        with pytest.raises(MgsRuntimeError, match="cannot contain itself"):
            run_src("floorplan D {\n  a: i32\n  me: D\n}\n")


class TestFloorplanFields:
    def test_read_and_write_scalars(self):
        env = run_src(
            PLAN + "p = garrison(Point)\np.x = i32(10)\np.y = i32(-20)\n"
            "rx = p.x\nry = p.y\n"
        )
        assert env.globals.get("rx").value == 10
        assert env.globals.get("ry").value == -20

    def test_fields_land_at_their_offsets(self):
        env = run_src(PLAN + "p = garrison(Point)\np.x = i32(1)\nb = p[4]\n")
        assert env.globals.get("b").value == 1

    def test_unknown_field_rejected(self):
        with pytest.raises(MgsRuntimeError, match="no field"):
            run_src(PLAN + "p = garrison(Point)\nx = p.nope\n")

    def test_array_field_yields_a_pine(self):
        env = run_src(
            PLAN + "p = garrison(Point)\nl = p.label\nl[0] = 65\nb = p[12]\n"
        )
        assert env.globals.get("b").value == 65

    def test_garrison_of_a_plan_sizes_the_block(self):
        env = run_src(PLAN + "p = garrison(Point)\ns = sizeof(p)\n")
        assert env.globals.get("s") == 20

    def test_nested_floorplan_field(self):
        env = run_src(
            "floorplan Inner {\n  a: i32\n  b: i32\n}\n"
            "floorplan Outer {\n  head: Inner\n  n: u16\n}\n"
            "p = garrison(Outer)\np.head.a = i32(5)\nx = p.head.a\n"
        )
        assert env.globals.get("x").value == 5


LIST = (
    "floorplan Node {\n  value: i32\n  next: pine[Node]\n}\n"
    "a = garrison(Node)\nb = garrison(Node)\n"
    "a.value = i32(1)\nb.value = i32(2)\n"
    "a.next = b\nb.next = none\n"
)


class TestPineFields:
    def test_self_referential_plan(self):
        env = run_src(LIST + "x = a.next.value\n")
        assert env.globals.get("x").value == 2

    def test_null_pine_reads_as_none(self):
        env = run_src(LIST + "t = b.next\n")
        assert env.globals.get("t") is None

    def test_pine_field_is_eight_byte_aligned(self):
        env = run_src(LIST)
        plan = env.globals.get("Node")
        assert plan.field_named("next").offset == 8
        assert plan.size == 16

    def test_walking_a_list(self):
        env = run_src(
            LIST
            + "total = 0\ncursor = a\n"
            + "while cursor != none {\n"
            + "    total = total + int(cursor.value)\n"
            + "    cursor = cursor.next\n"
            + "}\n"
        )
        assert env.globals.get("total") == 3

    def test_pine_field_rejects_a_non_pine(self):
        with pytest.raises(MgsRuntimeError, match="holds a pine"):
            run_src(LIST + "a.next = 5\n")

    def test_pointee_must_be_a_floorplan(self):
        with pytest.raises(MgsRuntimeError, match="not a floorplan"):
            run_src("floorplan D {\n  n: pine[Nope]\n}\n")


class TestFloorplanIsTheOnlyNewKeyword:
    def test_everything_else_is_a_shadowable_builtin(self):
        from magmascript.lang.tokens import KEYWORDS
        new_names = {
            "garrison", "scorch", "bathysphere", "osmosis",
            "sizeof", "alignof", "layout", "i32", "u8", "pine",
        }
        assert new_names.isdisjoint(KEYWORDS)
        assert "floorplan" in KEYWORDS

    def test_garrison_can_be_shadowed(self):
        env = run_src("garrison = 5\nx = garrison + 1\n")
        assert env.globals.get("x") == 6


# --------------------------------------------------------------------------
# Phase 4 - the hypnagogia pass
# --------------------------------------------------------------------------


def look(src: str):
    """Run the threshold pass over `src` and return its findings."""
    from magmascript.lang.hypnagogia import inspect as hypnagogia
    from magmascript.lang.parser import parse

    interpreter = Interpreter()
    return hypnagogia(parse(src), set(interpreter.globals.variables))


class TestHypnagogiaFindsRealProblems:
    def test_undefined_name(self):
        findings = look("print(nope)\n")
        assert len(findings) == 1
        assert "'nope' is never given a value" in findings[0].message

    def test_undefined_name_inside_a_function(self):
        findings = look("fn f() {\n    return missing\n}\n")
        assert len(findings) == 1
        assert findings[0].line == 2

    def test_suggests_a_near_name(self):
        findings = look("counter = 1\nprint(countr)\n")
        assert "did you mean" in findings[0].message

    def test_unreachable_after_return(self):
        findings = look('fn f() {\n    return 1\n    print("no")\n}\n')
        assert len(findings) == 1
        assert "can never run" in findings[0].message
        assert findings[0].line == 3

    def test_unreachable_after_break(self):
        findings = look('while true {\n    break\n    print("no")\n}\n')
        assert any("can never run" in f.message for f in findings)

    def test_unreachable_reported_once(self):
        findings = look('fn f() {\n    return 1\n    print("no")\n}\n')
        assert len([f for f in findings if "can never run" in f.message]) == 1

    def test_findings_are_sorted_by_position(self):
        findings = look("print(zeta)\nprint(alpha)\n")
        assert [f.line for f in findings] == [1, 2]

    def test_render_includes_the_filename(self):
        findings = look("print(nope)\n")
        assert "t.mgs:1" in findings[0].render("t.mgs")


class TestHypnagogiaStaysQuiet:
    """A dynamic language needs a timid pass. These must all report nothing."""

    def test_plain_program(self):
        assert look('x = 1\ny = x + 1\nprint(y)\n') == []

    def test_conditional_binding_is_not_flagged(self):
        """`if c { x = 1 }` then `print(x)` is legal when c holds."""
        assert look('if true { x = 1 }\nprint(x)\n') == []

    def test_use_before_assignment_is_not_flagged(self):
        assert look("fn f() {\n    return later\n}\nlater = 1\n") == []

    def test_function_parameters_are_bound(self):
        assert look("fn f(a, b) {\n    return a + b\n}\n") == []

    def test_loop_variables_are_bound(self):
        assert look("for i in range(3) {\n    print(i)\n}\n") == []

    def test_comprehension_variables_are_bound(self):
        assert look("xs = [n * 2 for n in range(3)]\n") == []

    def test_catch_parameter_is_bound(self):
        assert look('try {\n    x = 1\n} haunter (e) {\n    print(e)\n}\n') == []

    def test_builtins_are_known(self):
        assert look('print(len("hi"))\nprint(range(3))\n') == []

    def test_asthenosphere_names_are_known(self):
        assert look("p = garrison(8)\np.poke(i32, 1)\nscorch(p)\n") == []

    def test_domain_proxies_are_known(self):
        assert look("x = mcp\ny = mc1\n") == []

    def test_self_is_bound_in_methods(self):
        assert look("class C {\n    fn get(self) {\n        return self\n    }\n}\n") == []

    def test_floorplan_names_are_bound(self):
        assert look("floorplan P {\n  x: i32\n}\np = garrison(P)\n") == []

    def test_floorplan_field_types_are_not_variables(self):
        assert look("floorplan P {\n  x: i32\n  n: pine[P]\n}\n") == []

    def test_property_names_are_not_variables(self):
        assert look('d = {"a": 1}\nprint(d.a)\n') == []

    def test_arrow_function_params_are_bound(self):
        assert look("double = x -> x * 2\nprint(double(2))\n") == []

    def test_every_shipped_example_is_clean(self):
        """The pass must not cry wolf on code that already works."""
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        noisy = {}
        for path in sorted((root / "scripts" / "examples").glob("*.mgs")):
            findings = look(path.read_text(encoding="utf-8"))
            if findings:
                noisy[path.name] = [f.message for f in findings]
        assert noisy == {}
