"""MagmaScript code generators.

Usage::

    from magmascript.codegen import generate_c
    c_source = generate_c(program)
"""

from __future__ import annotations

from magmascript.lang import ast_nodes as ast
from magmascript.codegen.c import CGenerator


def generate_c(program: ast.Program) -> str:
    """Generate C code from a magmascript AST.

    Only handles asthenosphere features (floorplan, garrison, scorch,
    pine, fixed-width integers, osmosis). Core language features are
    not supported.
    """
    gen = CGenerator()
    return gen.generate(program)
