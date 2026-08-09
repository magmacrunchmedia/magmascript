from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from magmascript.lang import ast_nodes as ast
from magmascript.lang.environment import Environment, EnvironmentError
from magmascript.lang.builtins import BUILTINS
from magmascript.lang.domain_bridge import create_domain_proxies, wrap_result


class RuntimeError(Exception):
    def __init__(self, message: str, line: int = 0, column: int = 0) -> None:
        if line:
            super().__init__(f"Line {line}, Column {column}: {message}")
        else:
            super().__init__(message)
        self.line = line
        self.column = column


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class ReturnSignal(Exception):
    def __init__(self, value: Any = None) -> None:
        self.value = value


@dataclass
class MgsFunction:
    params: list[str]
    body: ast.ASTNode
    closure: Environment
    name: str = ""

    def __call__(self, *args: Any) -> Any:
        if len(args) != len(self.params):
            raise RuntimeError(f"Expected {len(self.params)} arguments, got {len(args)}")

        child_env = self.closure.child()
        for param, arg in zip(self.params, args):
            child_env.define(param, arg)

        interp = _get_thread_interpreter()
        try:
            result = interp.execute(self.body, child_env)
            return result
        except ReturnSignal as e:
            return e.value

    def __repr__(self) -> str:
        if self.name:
            return f"<function:{self.name}>"
        return "<function:anonymous>"


_thread_interpreter: Interpreter | None = None


def _get_thread_interpreter() -> Interpreter:
    global _thread_interpreter
    if _thread_interpreter is None:
        _thread_interpreter = Interpreter()
    return _thread_interpreter


class Interpreter:
    def __init__(self) -> None:
        self.globals = Environment()
        self._setup_builtins()
        self._setup_domains()

    def _setup_builtins(self) -> None:
        for name, func in BUILTINS.items():
            self.globals.define(name, func)

    def _setup_domains(self) -> None:
        proxies = create_domain_proxies()
        for name, proxy in proxies.items():
            self.globals.define(name, proxy)

    def run(self, program: ast.Program) -> Any:
        result = None
        for stmt in program.body:
            result = self.execute(stmt, self.globals)
        return result

    def execute(self, node: ast.ASTNode, env: Environment) -> Any:
        method = getattr(self, f"exec_{type(node).__name__}", None)
        if method is None:
            raise RuntimeError(f"Unknown node type: {type(node).__name__}")
        return method(node, env)

    def exec_Program(self, node: ast.Program, env: Environment) -> Any:
        result = None
        for stmt in node.body:
            result = self.execute(stmt, env)
        return result

    def exec_Block(self, node: ast.Block, env: Environment) -> Any:
        child_env = env.child()
        result = None
        for stmt in node.body:
            result = self.execute(stmt, child_env)
        return result

    def exec_NumberLiteral(self, node: ast.NumberLiteral, env: Environment) -> Any:
        return node.value

    def exec_StringLiteral(self, node: ast.StringLiteral, env: Environment) -> Any:
        return node.value

    def exec_BoolLiteral(self, node: ast.BoolLiteral, env: Environment) -> Any:
        return node.value

    def exec_NoneLiteral(self, node: ast.NoneLiteral, env: Environment) -> Any:
        return None

    def exec_Identifier(self, node: ast.Identifier, env: Environment) -> Any:
        try:
            return env.get(node.name)
        except EnvironmentError as e:
            raise RuntimeError(str(e), node.line, node.column)

    def exec_BinaryOp(self, node: ast.BinaryOp, env: Environment) -> Any:
        left = self.execute(node.left, env)

        if node.op == "and":
            if not left:
                return left
            return self.execute(node.right, env)

        if node.op == "or":
            if left:
                return left
            return self.execute(node.right, env)

        right = self.execute(node.right, env)

        if node.op == "+":
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            if isinstance(left, list) and isinstance(right, list):
                return left + right
            return left + right
        if node.op == "-":
            return left - right
        if node.op == "*":
            if isinstance(left, str) and isinstance(right, int):
                return left * right
            if isinstance(left, list) and isinstance(right, int):
                return left * right
            return left * right
        if node.op == "/":
            if right == 0:
                raise RuntimeError("Division by zero", node.line, node.column)
            return left / right
        if node.op == "%":
            return left % right
        if node.op == "==":
            return left == right
        if node.op == "!=":
            return left != right
        if node.op == "<":
            return left < right
        if node.op == ">":
            return left > right
        if node.op == "<=":
            return left <= right
        if node.op == ">=":
            return left >= right

        raise RuntimeError(f"Unknown operator: {node.op}", node.line, node.column)

    def exec_UnaryOp(self, node: ast.UnaryOp, env: Environment) -> Any:
        operand = self.execute(node.operand, env)

        if node.op == "-":
            return -operand
        if node.op == "not":
            return not operand

        raise RuntimeError(f"Unknown unary operator: {node.op}", node.line, node.column)

    def exec_Assignment(self, node: ast.Assignment, env: Environment) -> Any:
        value = self.execute(node.value, env)
        env.set(node.name, value)
        return value

    def exec_PropertyAccess(self, node: ast.PropertyAccess, env: Environment) -> Any:
        obj = self.execute(node.object, env)
        if obj is None:
            raise RuntimeError(f"Cannot access property on None", node.line, node.column)

        if isinstance(obj, dict):
            if node.property in obj:
                return obj[node.property]
            raise RuntimeError(f"Property '{node.property}' not found", node.line, node.column)

        if hasattr(obj, "_obj"):
            return getattr(obj, node.property)

        if hasattr(obj, node.property):
            return getattr(obj, node.property)

        raise RuntimeError(f"Cannot access property '{node.property}' on {type(obj).__name__}", node.line, node.column)

    def exec_IndexAccess(self, node: ast.IndexAccess, env: Environment) -> Any:
        obj = self.execute(node.object, env)
        index = self.execute(node.index, env)

        if isinstance(obj, list):
            if not isinstance(index, int):
                raise RuntimeError("List index must be an integer", node.line, node.column)
            if index < 0 or index >= len(obj):
                raise RuntimeError(f"List index out of bounds: {index}", node.line, node.column)
            return obj[index]

        if isinstance(obj, dict):
            if index not in obj:
                raise RuntimeError(f"Key not found: {index}", node.line, node.column)
            return obj[index]

        if hasattr(obj, "__getitem__"):
            try:
                return obj[index]
            except (KeyError, IndexError) as e:
                raise RuntimeError(str(e), node.line, node.column)

        raise RuntimeError(f"Cannot index into {type(obj).__name__}", node.line, node.column)

    def exec_FunctionCall(self, node: ast.FunctionCall, env: Environment) -> Any:
        callee = self.execute(node.callee, env)
        args = [self.execute(arg, env) for arg in node.arguments]

        if callable(callee):
            try:
                result = callee(*args)
                return wrap_result(result)
            except TypeError as e:
                raise RuntimeError(str(e), node.line, node.column)

        raise RuntimeError(f"Cannot call non-function: {type(callee).__name__}", node.line, node.column)

    def exec_MethodCall(self, node: ast.MethodCall, env: Environment) -> Any:
        obj = self.execute(node.object, env)
        args = [self.execute(arg, env) for arg in node.arguments]

        if obj is None:
            raise RuntimeError(f"Cannot call method on None", node.line, node.column)

        if hasattr(obj, "_obj"):
            method = getattr(obj, node.method, None)
            if method:
                try:
                    result = method(*args)
                    return wrap_result(result)
                except TypeError as e:
                    raise RuntimeError(str(e), node.line, node.column)

        if hasattr(obj, node.method):
            method = getattr(obj, node.method)
            if callable(method):
                try:
                    result = method(*args)
                    return wrap_result(result)
                except TypeError as e:
                    raise RuntimeError(str(e), node.line, node.column)

        raise RuntimeError(f"Object has no method '{node.method}'", node.line, node.column)

    def exec_IfExpression(self, node: ast.IfExpression, env: Environment) -> Any:
        condition = self.execute(node.condition, env)

        if self._is_truthy(condition):
            return self.execute(node.then_block, env)
        elif node.else_block:
            return self.execute(node.else_block, env)

        return None

    def exec_ForLoop(self, node: ast.ForLoop, env: Environment) -> Any:
        iterable = self.execute(node.iterable, env)

        if isinstance(iterable, list):
            items = iterable
        elif hasattr(iterable, "__iter__"):
            items = list(iterable)
        else:
            raise RuntimeError(f"Cannot iterate over {type(iterable).__name__}", node.line, node.column)

        result = None
        child_env = env.child()
        for item in items:
            child_env.define(node.variable, item)
            try:
                result = self.execute(node.body, child_env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

        return result

    def exec_WhileLoop(self, node: ast.WhileLoop, env: Environment) -> Any:
        result = None
        while self._is_truthy(self.execute(node.condition, env)):
            try:
                result = self.execute(node.body, env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue
        return result

    def exec_FunctionDef(self, node: ast.FunctionDef, env: Environment) -> Any:
        func = MgsFunction(
            params=node.params,
            body=node.body,
            closure=env,
            name=node.name,
        )
        if node.name:
            env.define(node.name, func)
        return func

    def exec_ArrowFunction(self, node: ast.ArrowFunction, env: Environment) -> Any:
        return MgsFunction(
            params=node.params,
            body=node.body,
            closure=env,
        )

    def exec_ReturnStatement(self, node: ast.ReturnStatement, env: Environment) -> Any:
        value = None
        if node.value:
            value = self.execute(node.value, env)
        raise ReturnSignal(value)

    def exec_BreakStatement(self, node: ast.BreakStatement, env: Environment) -> Any:
        raise BreakSignal()

    def exec_ContinueStatement(self, node: ast.ContinueStatement, env: Environment) -> Any:
        raise ContinueSignal()

    def exec_ListLiteral(self, node: ast.ListLiteral, env: Environment) -> Any:
        return [self.execute(elem, env) for elem in node.elements]

    def exec_InterpolatedString(self, node: ast.InterpolatedString, env: Environment) -> Any:
        parts = []
        for part in node.parts:
            value = self.execute(part, env)
            parts.append(str(value))
        return "".join(parts)

    def exec_ExprStatement(self, node: ast.ExprStatement, env: Environment) -> Any:
        return self.execute(node.expr, env)

    def exec_PrintStatement(self, node: ast.PrintStatement, env: Environment) -> Any:
        args = [self.execute(arg, env) for arg in node.arguments]
        print(*[str(a) for a in args])
        return None

    def _is_truthy(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, float):
            return value != 0.0
        if isinstance(value, str):
            return len(value) > 0
        if isinstance(value, list):
            return len(value) > 0
        return True


def run(source: str) -> Any:
    from magmascript.lang.parser import parse
    program = parse(source)
    interpreter = Interpreter()
    global _thread_interpreter
    _thread_interpreter = interpreter
    return interpreter.run(program)
