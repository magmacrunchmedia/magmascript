"""AST pretty-printer. Unparses AST nodes back to .mgs source code.

Usage::

    from magmascript.lang.pretty import unparse
    source = unparse(program)
"""

from __future__ import annotations

from magmascript.lang import ast_nodes as ast


def unparse(node: ast.ASTNode, indent: int = 0) -> str:
    """Convert an AST node back to .mgs source code."""
    method = getattr(_Unparser, f"_unparse_{type(node).__name__}", None)
    if method:
        return method(node, indent)
    return f"/* unknown: {type(node).__name__} */"


class _Unparser:
    @staticmethod
    def _unparse_Program(node: ast.Program, indent: int) -> str:
        return "\n\n".join(unparse(stmt, indent) for stmt in node.body)

    @staticmethod
    def _unparse_Block(node: ast.Block, indent: int) -> str:
        if not node.body:
            return "{ }"
        inner = "\n".join(unparse(stmt, indent + 1) for stmt in node.body)
        return "{\n" + _indent(inner, indent + 1) + "\n" + _indent("}", indent)

    @staticmethod
    def _unparse_NumberLiteral(node: ast.NumberLiteral, indent: int) -> str:
        if isinstance(node.value, float):
            s = str(node.value)
            if "." not in s and "e" not in s.lower():
                s += ".0"
            return s
        return str(node.value)

    @staticmethod
    def _unparse_StringLiteral(node: ast.StringLiteral, indent: int) -> str:
        if node.interpolated:
            return f'f"{node.value}"'
        return f'"{node.value}"'

    @staticmethod
    def _unparse_BoolLiteral(node: ast.BoolLiteral, indent: int) -> str:
        return "true" if node.value else "false"

    @staticmethod
    def _unparse_NoneLiteral(node: ast.NoneLiteral, indent: int) -> str:
        return "none"

    @staticmethod
    def _unparse_Identifier(node: ast.Identifier, indent: int) -> str:
        return node.name

    @staticmethod
    def _unparse_BinaryOp(node: ast.BinaryOp, indent: int) -> str:
        return f"{unparse(node.left, indent)} {node.op} {unparse(node.right, indent)}"

    @staticmethod
    def _unparse_UnaryOp(node: ast.UnaryOp, indent: int) -> str:
        return f"{node.op}{unparse(node.operand, indent)}"

    @staticmethod
    def _unparse_FunctionCall(node: ast.FunctionCall, indent: int) -> str:
        args = ", ".join(unparse(a, indent) for a in node.arguments)
        return f"{unparse(node.callee, indent)}({args})"

    @staticmethod
    def _unparse_MethodCall(node: ast.MethodCall, indent: int) -> str:
        args = ", ".join(unparse(a, indent) for a in node.arguments)
        return f"{unparse(node.object, indent)}.{node.method}({args})"

    @staticmethod
    def _unparse_PropertyAccess(node: ast.PropertyAccess, indent: int) -> str:
        return f"{unparse(node.object, indent)}.{node.property}"

    @staticmethod
    def _unparse_IndexAccess(node: ast.IndexAccess, indent: int) -> str:
        if isinstance(node.index, ast.Slice):
            s = _unparse_slice(node.index)
            return f"{unparse(node.object, indent)}[{s}]"
        return f"{unparse(node.object, indent)}[{unparse(node.index, indent)}]"

    @staticmethod
    def _unparse_ListLiteral(node: ast.ListLiteral, indent: int) -> str:
        elems = ", ".join(unparse(e, indent) for e in node.elements)
        return f"[{elems}]"

    @staticmethod
    def _unparse_DictLiteral(node: ast.DictLiteral, indent: int) -> str:
        pairs = []
        for k, v in zip(node.keys, node.values):
            pairs.append(f"{unparse(k, indent)}: {unparse(v, indent)}")
        return "{" + ", ".join(pairs) + "}"

    @staticmethod
    def _unparse_ListComprehension(node: ast.ListComprehension, indent: int) -> str:
        parts = [f"{unparse(node.element, indent)} for {node.variable} in {unparse(node.iterable, indent)}"]
        if node.condition:
            parts.append(f" if {unparse(node.condition, indent)}")
        return "[" + "".join(parts) + "]"

    @staticmethod
    def _unparse_Assignment(node: ast.Assignment, indent: int) -> str:
        if node.op == "=":
            return f"{node.name} = {unparse(node.value, indent)}"
        return f"{node.name} {node.op} {unparse(node.value, indent)}"

    @staticmethod
    def _unparse_MultiAssignment(node: ast.MultiAssignment, indent: int) -> str:
        targets = ", ".join(node.targets)
        values = ", ".join(unparse(v, indent) for v in node.values)
        if node.op == "=":
            return f"{targets} = {values}"
        return f"{targets} {node.op} {values}"

    @staticmethod
    def _unparse_PropertyAssignment(node: ast.PropertyAssignment, indent: int) -> str:
        obj = unparse(node.object, indent)
        val = unparse(node.value, indent)
        if node.op == "=":
            return f"{obj}.{node.property} = {val}"
        return f"{obj}.{node.property} {node.op} {val}"

    @staticmethod
    def _unparse_IndexAssignment(node: ast.IndexAssignment, indent: int) -> str:
        obj = unparse(node.object, indent)
        idx = unparse(node.index, indent)
        val = unparse(node.value, indent)
        if node.op == "=":
            return f"{obj}[{idx}] = {val}"
        return f"{obj}[{idx}] {node.op} {val}"

    @staticmethod
    def _unparse_ExprStatement(node: ast.ExprStatement, indent: int) -> str:
        return unparse(node.expr, indent)

    @staticmethod
    def _unparse_PrintStatement(node: ast.PrintStatement, indent: int) -> str:
        args = ", ".join(unparse(a, indent) for a in node.arguments)
        return f"print({args})"

    @staticmethod
    def _unparse_SpookedStatement(node: ast.SpookedStatement, indent: int) -> str:
        return f"spooked({unparse(node.message, indent)})"

    @staticmethod
    def _unparse_ReturnStatement(node: ast.ReturnStatement, indent: int) -> str:
        if node.value:
            return f"return {unparse(node.value, indent)}"
        return "return"

    @staticmethod
    def _unparse_BreakStatement(node: ast.BreakStatement, indent: int) -> str:
        return "break"

    @staticmethod
    def _unparse_ContinueStatement(node: ast.ContinueStatement, indent: int) -> str:
        return "continue"

    @staticmethod
    def _unparse_IfExpression(node: ast.IfExpression, indent: int) -> str:
        parts = [f"if {unparse(node.condition, indent)} {unparse(node.then_block, indent)}"]
        if node.else_block:
            if isinstance(node.else_block, ast.IfExpression):
                parts.append(f"else {unparse(node.else_block, indent)}")
            else:
                parts.append(f"else {unparse(node.else_block, indent)}")
        return " ".join(parts)

    @staticmethod
    def _unparse_ForLoop(node: ast.ForLoop, indent: int) -> str:
        return f"for {node.variable} in {unparse(node.iterable, indent)} {unparse(node.body, indent)}"

    @staticmethod
    def _unparse_WhileLoop(node: ast.WhileLoop, indent: int) -> str:
        return f"while {unparse(node.condition, indent)} {unparse(node.body, indent)}"

    @staticmethod
    def _unparse_FunctionDef(node: ast.FunctionDef, indent: int) -> str:
        params = _format_params(node.params, node.defaults)
        return f"fn {node.name}({params}) {unparse(node.body, indent)}"

    @staticmethod
    def _unparse_ArrowFunction(node: ast.ArrowFunction, indent: int) -> str:
        params = _format_params(node.params, node.defaults)
        if isinstance(node.body, ast.Block):
            return f"fn({params}) {unparse(node.body, indent)}"
        return f"fn({params}) -> {unparse(node.body, indent)}"

    @staticmethod
    def _unparse_ClassDef(node: ast.ClassDef, indent: int) -> str:
        methods = "\n".join(unparse(m, indent + 1) for m in node.methods)
        return f"class {node.name} {{\n{_indent(methods, indent + 1)}\n{_indent('}', indent)}}"

    @staticmethod
    def _unparse_FloorplanDef(node: ast.FloorplanDef, indent: int) -> str:
        fields = []
        for f in node.fields:
            if f.count:
                fields.append(f"{f.name}: {f.type_name}[{f.count}]")
            elif f.points_to:
                fields.append(f"{f.name}: pine[{f.points_to}]")
            else:
                fields.append(f"{f.name}: {f.type_name}")
        body = "\n".join(_indent(f, indent + 1) for f in fields)
        return f"floorplan {node.name} {{\n{body}\n{_indent('}', indent)}}"

    @staticmethod
    def _unparse_TryCatch(node: ast.TryCatch, indent: int) -> str:
        body = unparse(node.try_block, indent)
        catch = unparse(node.catch_block, indent)
        param = f"({node.catch_param})" if node.catch_param else ""
        return f"try {body} haunter{param} {catch}"

    @staticmethod
    def _unparse_ThrowStatement(node: ast.ThrowStatement, indent: int) -> str:
        msg = unparse(node.message, indent)
        if node.error_type == "fire toad":
            return f"throw fire toad({msg})"
        return f"throw {node.error_type}({msg})"

    @staticmethod
    def _unparse_ImportStatement(node: ast.ImportStatement, indent: int) -> str:
        if node.from_import:
            names = ", ".join(node.names)
            if node.alias:
                return f"intent {{ {names} }} from \"{node.module}\" as {node.alias}"
            return f"intent {{ {names} }} from \"{node.module}\""
        if node.alias:
            return f"intent \"{node.module}\" as {node.alias}"
        return f"intent \"{node.module}\""


def _indent(text: str, level: int) -> str:
    prefix = "    " * level
    return "\n".join(prefix + line if line.strip() else "" for line in text.split("\n"))


def _format_params(params: list[str], defaults: dict[str, ast.ASTNode]) -> str:
    parts = []
    for p in params:
        if p in defaults:
            parts.append(f"{p} = {unparse(defaults[p])}")
        else:
            parts.append(p)
    return ", ".join(parts)


def _unparse_slice(node: ast.Slice) -> str:
    parts = []
    parts.append(unparse(node.start) if node.start else "")
    parts.append(unparse(node.stop) if node.stop else "")
    if node.step:
        parts.append(unparse(node.step))
    return ":".join(parts)
