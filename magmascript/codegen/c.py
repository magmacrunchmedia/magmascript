"""C code generator for magmascript asthenosphere features.

Converts .mgs AST with asthenosphere features to equivalent C code.
Only handles asthenosphere features (floorplan, garrison, scorch, pine,
fixed-width integers, osmosis). Core language features are not supported.
"""

from __future__ import annotations

from magmascript.lang import ast_nodes as ast
from magmascript.lang.visitor import Visitor


# Type mappings from magmascript to C
TYPE_MAP = {
    "i8": "int8_t",
    "i16": "int16_t",
    "i32": "int32_t",
    "i64": "int64_t",
    "u8": "uint8_t",
    "u16": "uint16_t",
    "u32": "uint32_t",
    "u64": "uint64_t",
    "f32": "float",
    "f64": "double",
}

INCLUDES = """#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
"""


class CGenerator(Visitor):
    """Generate C code from a magmascript AST.

    Only handles asthenosphere features. Core language features
    (functions, classes, control flow) are not supported.
    """

    def __init__(self) -> None:
        super().__init__()
        self._lines: list[str] = []
        self._structs: dict[str, ast.FloorplanDef] = {}
        self._indent = 0

    def generate(self, program: ast.Program) -> str:
        """Generate C code from a Program node."""
        # First pass: collect floorplan definitions
        for stmt in program.body:
            if isinstance(stmt, ast.FloorplanDef):
                self._structs[stmt.name] = stmt

        # Generate struct definitions
        for name, plan in self._structs.items():
            self._gen_struct(plan)
            self._lines.append("")

        # Generate main function
        self._lines.append("int main(void) {")
        self._indent += 1
        for stmt in program.body:
            if not isinstance(stmt, ast.FloorplanDef):
                self._gen_statement(stmt)
        self._indent -= 1
        self._lines.append("}")
        self._lines.append("")

        return INCLUDES + "\n".join(self._lines)

    def _gen_struct(self, node: ast.FloorplanDef) -> None:
        """Generate a C struct from a floorplan definition."""
        self._lines.append(f"typedef struct {node.name} {{")
        self._indent += 1
        for field in node.fields:
            c_type = self._map_type(field.type_name)
            if field.count > 1:
                self._lines.append(f"{c_type} {field.name}[{field.count}];")
            elif field.points_to:
                self._lines.append(f"struct {field.points_to} *{field.name};")
            else:
                self._lines.append(f"{c_type} {field.name};")
        self._indent -= 1
        self._lines.append(f"}} {node.name};")

    def _map_type(self, type_name: str) -> str:
        """Map a magmascript type name to C."""
        return TYPE_MAP.get(type_name, type_name)

    def _gen_statement(self, node: ast.ASTNode) -> None:
        """Generate a C statement."""
        method = getattr(self, f"_gen_{type(node).__name__}", None)
        if method:
            method(node)
        else:
            self._lines.append(f"/* unsupported: {type(node).__name__} */")

    def _gen_Assignment(self, node: ast.Assignment) -> None:
        value = self._gen_expr(node.value)
        # Try to infer type from value
        type_name = "void *"
        if isinstance(node.value, ast.FunctionCall) and isinstance(node.value.callee, ast.Identifier):
            if node.value.callee.name == "garrison":
                type_name = "void *"
        self._lines.append(f"{type_name} {node.name} = {value};")

    def _gen_ExprStatement(self, node: ast.ExprStatement) -> None:
        # Handle assignments specially
        if isinstance(node.expr, ast.Assignment):
            self._gen_Assignment(node.expr)
        else:
            expr = self._gen_expr(node.expr)
            self._lines.append(f"{expr};")

    def _gen_PrintStatement(self, node: ast.PrintStatement) -> None:
        if len(node.arguments) == 1:
            arg = node.arguments[0]
            if isinstance(arg, ast.InterpolatedString):
                self._gen_printf(arg)
            else:
                expr = self._gen_expr(arg)
                self._lines.append(f'printf("%d\\n", {expr});')
        else:
            self._lines.append("/* printf with multiple args not supported */")

    def _gen_printf(self, node: ast.InterpolatedString) -> None:
        """Generate printf for an interpolated string."""
        parts = []
        args = []
        for part in node.parts:
            if isinstance(part, ast.StringLiteral):
                parts.append(part.value)
            else:
                parts.append("%d")
                args.append(self._gen_expr(part))
        fmt = "".join(parts)
        args_str = ", ".join(args)
        self._lines.append(f'printf("{fmt}"{", " + args_str if args_str else ""});')

    def _gen_FloorplanDef(self, node: ast.FloorplanDef) -> None:
        """Store floorplan for struct generation."""
        self._structs[node.name] = node

    def _gen_expr(self, node: ast.ASTNode) -> str:
        """Generate a C expression."""
        method = getattr(self, f"_expr_{type(node).__name__}", None)
        if method:
            return method(node)
        return f"/* unsupported: {type(node).__name__} */"

    def _expr_NumberLiteral(self, node: ast.NumberLiteral) -> str:
        return str(node.value)

    def _expr_StringLiteral(self, node: ast.StringLiteral) -> str:
        return f'"{node.value}"'

    def _expr_BoolLiteral(self, node: ast.BoolLiteral) -> str:
        return "1" if node.value else "0"

    def _expr_NoneLiteral(self, node: ast.NoneLiteral) -> str:
        return "NULL"

    def _expr_Identifier(self, node: ast.Identifier) -> str:
        return node.name

    def _expr_BinaryOp(self, node: ast.BinaryOp) -> str:
        left = self._gen_expr(node.left)
        right = self._gen_expr(node.right)
        return f"({left} {node.op} {right})"

    def _expr_UnaryOp(self, node: ast.UnaryOp) -> str:
        return f"{node.op}{self._gen_expr(node.operand)}"

    def _expr_FunctionCall(self, node: ast.FunctionCall) -> str:
        if isinstance(node.callee, ast.Identifier):
            name = node.callee.name
            args = [self._gen_expr(a) for a in node.arguments]

            # Map garrison to malloc
            if name == "garrison" and len(args) == 1:
                return f"malloc({args[0]})"

            # Map scorch to free
            if name == "scorch" and len(args) == 1:
                return f"free({args[0]})"

            # Map osmosis to cast
            if name == "osmosis" and len(args) == 2:
                type_name = args[0] if isinstance(node.arguments[0], ast.Identifier) else args[0]
                return f"({type_name}){args[1]}"

            # Map sizeof
            if name == "sizeof" and len(args) == 1:
                return f"sizeof({args[0]})"

            # Map alignof
            if name == "alignof" and len(args) == 1:
                return f"_Alignof({args[0]})"

            args_str = ", ".join(args)
            return f"{name}({args_str})"

        return "/* unsupported callee */"

    def _expr_MethodCall(self, node: ast.MethodCall) -> str:
        obj = self._gen_expr(node.object)
        args = [self._gen_expr(a) for a in node.arguments]

        # Map peek to cast dereference
        if node.method == "peek" and len(args) == 1:
            # Get the type name
            if isinstance(node.arguments[0], ast.Identifier):
                type_name = node.arguments[0].name
            elif isinstance(node.arguments[0], ast.PropertyAccess):
                # Look up field type from struct
                if isinstance(node.arguments[0].object, ast.Identifier):
                    struct_name = node.arguments[0].object.name
                    field_name = node.arguments[0].property
                    if struct_name in self._structs:
                        for f in self._structs[struct_name].fields:
                            if f.name == field_name:
                                type_name = self._map_type(f.type_name)
                                break
                        else:
                            type_name = "void *"
                    else:
                        type_name = "void *"
                else:
                    type_name = "void *"
            else:
                type_name = "void *"
            return f"*({type_name} *){obj}"

        # Map poke to cast dereference assignment
        if node.method == "poke" and len(args) == 2:
            # Get the type name
            if isinstance(node.arguments[0], ast.Identifier):
                type_name = node.arguments[0].name
            elif isinstance(node.arguments[0], ast.PropertyAccess):
                # Look up field type from struct
                if isinstance(node.arguments[0].object, ast.Identifier):
                    struct_name = node.arguments[0].object.name
                    field_name = node.arguments[0].property
                    if struct_name in self._structs:
                        for f in self._structs[struct_name].fields:
                            if f.name == field_name:
                                type_name = self._map_type(f.type_name)
                                break
                        else:
                            type_name = "void *"
                    else:
                        type_name = "void *"
                else:
                    type_name = "void *"
            else:
                type_name = "void *"

            # If the first arg is a property access like Point.x, use field offset
            if isinstance(node.arguments[0], ast.PropertyAccess):
                struct_name = node.arguments[0].object.name if isinstance(node.arguments[0].object, ast.Identifier) else ""
                field_name = node.arguments[0].property
                if struct_name:
                    return f"(({struct_name} *){obj})->{field_name} = {args[1]}"
            return f"*({type_name} *){obj} = {args[1]}"

        # Map bathysphere to printf hex dump
        if node.method == "bathysphere" and len(args) == 1:
            return f"/* bathysphere({args[0]}) - hex dump not available in C */"

        args_str = ", ".join(args)
        return f"{obj}.{node.method}({args_str})"

    def _expr_PropertyAccess(self, node: ast.PropertyAccess) -> str:
        obj = self._gen_expr(node.object)
        # If accessing a floorplan field (like Point.x), return the field name
        if isinstance(node.object, ast.Identifier) and node.object.name in self._structs:
            return node.property
        return f"{obj}.{node.property}"

    def _expr_IndexAccess(self, node: ast.IndexAccess) -> str:
        obj = self._gen_expr(node.object)
        idx = self._gen_expr(node.index)
        return f"{obj}[{idx}]"
