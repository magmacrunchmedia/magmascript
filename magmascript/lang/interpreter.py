from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any, Callable

from magmascript.lang import ast_nodes as ast
from magmascript.lang.environment import Environment, EnvironmentError
from magmascript.lang.builtins import BUILTINS, to_display
from magmascript.lang.domain_bridge import create_domain_proxies, wrap_result
from magmascript.lang.util import suggest
from magmascript.lang import astheno


# Maximum nested .mgs function calls. Each one costs ~7 Python frames, so the
# interpreter raises Python's own limit to leave room for this many plus the
# expression nesting inside them.
MAX_CALL_DEPTH = 500
_PY_FRAMES_PER_CALL = 7
_PY_RECURSION_HEADROOM = 2000


class RuntimeError(Exception):
    def __init__(self, message: str, line: int = 0, column: int = 0, filename: str | None = None, source_line: str | None = None, call_stack: list[str] | None = None, prefix: str = "fire toad") -> None:
        self.line = line
        self.column = column
        self.filename = filename
        self.source_line = source_line
        self.call_stack = call_stack or []
        self.message = message
        self.prefix = prefix
        super().__init__(message)

    def format(self) -> str:
        parts = []
        if self.line:
            loc = f"line {self.line}, column {self.column}"
            if self.filename:
                loc = f"{self.filename}:{loc}"
            parts.append(f"{self.prefix} at {loc}")

            if self.source_line is not None:
                line_num = str(self.line)
                padding = " " * len(line_num)
                parts.append(f"  {padding} |")
                parts.append(f"  {line_num} | {self.source_line}")
                caret = " " * (self.column - 1) + "^"
                parts.append(f"  {padding} | {caret}")
        else:
            parts.append(self.prefix)

        parts.append(self.message)

        if self.call_stack:
            parts.append("")
            parts.append("Stack trace:")
            for frame in self.call_stack:
                parts.append(f"  {frame}")

        return "\n".join(parts)


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
    defaults: dict[str, Any] = field(default_factory=dict)

    def __call__(self, *args: Any) -> Any:
        min_args = len(self.params) - len(self.defaults)
        if len(args) < min_args or len(args) > len(self.params):
            name = self.name or "anonymous"
            if min_args == len(self.params):
                # No defaults - simple error message
                raise RuntimeError(f"{name}() takes {len(self.params)} argument{'s' if len(self.params) != 1 else ''} but {len(args)} {'were' if len(args) != 1 else 'was'} given")
            else:
                # Has defaults - range error message
                raise RuntimeError(f"{name}() takes {min_args}-{len(self.params)} argument(s) but {len(args)} {'were' if len(args) != 1 else 'was'} given")

        child_env = self.closure.child()
        for param, arg in zip(self.params, args):
            child_env.define(param, arg)
        # Bind defaults for unprovided params
        for param in self.params[len(args):]:
            if param in self.defaults:
                child_env.define(param, self.defaults[param])

        interp = _get_thread_interpreter()
        if len(interp._call_stack) >= MAX_CALL_DEPTH:
            raise interp._depth_error(self.body)
        interp._call_stack.append(self._stack_frame())
        try:
            result = interp.execute(self.body, child_env)
            return result
        except ReturnSignal as e:
            return e.value
        finally:
            interp._call_stack.pop()

    def _stack_frame(self) -> str:
        name = self.name or "anonymous"
        body = self.body
        if hasattr(body, "line") and body.line:
            return f"{name}() at line {body.line}"
        return f"{name}()"

    def __repr__(self) -> str:
        if self.name:
            return f"<function:{self.name}>"
        return "<function:anonymous>"


@dataclass
class MgsClass:
    name: str
    methods: dict[str, MgsFunction]
    closure: Environment

    def __call__(self, *args: Any) -> Any:
        instance = MgsInstance(
            class_def=self,
            attributes={},
        )
        init = self.methods.get("init")
        if init:
            # Only prepend self if not already in params
            if init.params and init.params[0] == "self":
                init_with_self = init
            else:
                init_with_self = MgsFunction(
                    params=["self"] + init.params,
                    body=init.body,
                    closure=self.closure,
                    name="init",
                )
            init_with_self(instance, *args)
        return instance

    def __repr__(self) -> str:
        return f"<class:{self.name}>"


@dataclass
class MgsInstance:
    class_def: MgsClass
    attributes: dict[str, Any]

    def __repr__(self) -> str:
        return f"<{self.class_def.name} instance>"

    def __str__(self) -> str:
        str_method = self.class_def.methods.get("__str__")
        if str_method:
            return str_method(self)
        return self.__repr__()


class MgsString:
    def __init__(self, value: str) -> None:
        self._value = value

    def split(self, sep: str | None = None) -> list[str]:
        if sep is None:
            return self._value.split()
        return self._value.split(sep)

    def join(self, iterable: list[str]) -> str:
        return self._value.join(iterable)

    def upper(self) -> str:
        return self._value.upper()

    def lower(self) -> str:
        return self._value.lower()

    def contains(self, sub: str) -> bool:
        return sub in self._value

    def replace(self, old: str, new: str) -> str:
        return self._value.replace(old, new)

    def length(self) -> int:
        return len(self._value)

    def startswith(self, prefix: str) -> bool:
        return self._value.startswith(prefix)

    def endswith(self, suffix: str) -> bool:
        return self._value.endswith(suffix)

    def strip(self) -> str:
        return self._value.strip()

    def match(self, pattern: str) -> list[str] | None:
        """Check if pattern matches at the start of the string. Returns groups or None."""
        import re
        m = re.match(pattern, self._value)
        if m:
            return list(m.groups()) if m.groups() else [m.group(0)]
        return None

    def findall(self, pattern: str) -> list[str]:
        """Find all non-overlapping matches of pattern in the string."""
        import re
        return re.findall(pattern, self._value)

    def __repr__(self) -> str:
        return self._value

    def __str__(self) -> str:
        return self._value


_thread_interpreter: Interpreter | None = None


def _get_thread_interpreter() -> Interpreter:
    global _thread_interpreter
    if _thread_interpreter is None:
        _thread_interpreter = Interpreter()
    return _thread_interpreter


class Interpreter:
    def __init__(self, source: str | None = None, filename: str | None = None, script_args: list[str] | None = None) -> None:
        self.globals = Environment()
        self.source = source
        self.filename = filename
        self._call_stack: list[str] = []
        self._current_node: ast.ASTNode | None = None
        self.arena = astheno.Arena()
        self._script_args = script_args or []
        self._module_cache: dict[str, Environment] = {}
        self._loading_modules: set[str] = set()
        needed = MAX_CALL_DEPTH * _PY_FRAMES_PER_CALL + _PY_RECURSION_HEADROOM
        if sys.getrecursionlimit() < needed:
            sys.setrecursionlimit(needed)
        self._setup_builtins()
        self._setup_domains()

    def _setup_builtins(self) -> None:
        for name, func in BUILTINS.items():
            self.globals.define(name, func)
        self.globals.define("args", lambda: self._script_args)

    def _setup_domains(self) -> None:
        proxies = create_domain_proxies()
        for name, proxy in proxies.items():
            self.globals.define(name, proxy)
        # Add HTTP proxy for .mgs scripts
        from magmascript.lang.builtins import HttpProxy
        self.globals.define("http", HttpProxy())

    def _get_source_line(self, line_num: int) -> str | None:
        if self.source is None:
            return None
        lines = self.source.split("\n")
        if 1 <= line_num <= len(lines):
            return lines[line_num - 1]
        return None

    def error(self, message: str, node: ast.ASTNode | None = None, prefix: str = "fire toad") -> RuntimeError:
        line = getattr(node, "line", 0) or 0
        column = getattr(node, "column", 0) or 0
        source_line = self._get_source_line(line) if line else None
        return RuntimeError(message, line, column, self.filename, source_line, list(self._call_stack), prefix)

    def _depth_error(self, node: ast.ASTNode | None = None) -> RuntimeError:
        """Build the recursion-limit error with an elided stack.

        format() prints every frame it is given, so handing it a 500-deep
        stack would bury the message. Show the bottom and top of the stack
        and count what is between.
        """
        frames = self._call_stack
        if len(frames) > 8:
            frames = frames[:3] + [f"... {len(frames) - 6} more frames ..."] + frames[-3:]
        else:
            frames = list(frames)
        line = getattr(node, "line", 0) or 0
        column = getattr(node, "column", 0) or 0
        # parse_block() builds Block without position info, so fall back to the
        # first statement inside the function body.
        if not line:
            inner = next(iter(getattr(node, "body", []) or []), None)
            line = getattr(inner, "line", 0) or 0
            column = getattr(inner, "column", 0) or 0
        source_line = self._get_source_line(line) if line else None
        return RuntimeError(
            f"Call depth exceeded {MAX_CALL_DEPTH} — is this recursion infinite?",
            line,
            column,
            self.filename,
            source_line,
            frames,
            "exploding brain syndrome",
        )

    def run(self, program: ast.Program) -> Any:
        # Register as the active interpreter so MgsFunction.__call__ executes
        # bodies against *this* instance. Without this, any entry point that
        # constructs an Interpreter directly (the CLI does) leaves the global
        # unset, and function bodies run on a blank interpreter with no source
        # — costing every in-function error its filename and caret diagram.
        # Save/restore rather than assign, so an imported module's interpreter
        # does not outlive its own run().
        global _thread_interpreter
        previous = _thread_interpreter
        _thread_interpreter = self
        previous_hook = astheno.set_warn_hook(self._astheno_warn)
        previous_site = astheno.set_site_hook(self._astheno_site)
        previous_arena = astheno.set_arena(self.arena)
        try:
            result = None
            for stmt in program.body:
                result = self.execute(stmt, self.globals)
            return result
        finally:
            _thread_interpreter = previous
            astheno.set_warn_hook(previous_hook)
            astheno.set_site_hook(previous_site)
            astheno.set_arena(previous_arena)

    def execute(self, node: ast.ASTNode, env: Environment) -> Any:
        method = getattr(self, f"exec_{type(node).__name__}", None)
        if method is None:
            raise RuntimeError(f"Unknown node type: {type(node).__name__}")
        # Asthenosphere warnings (overflow, precision loss, leaks) are raised
        # deep inside pure helpers that have no AST access. Recording the node
        # here is what lets those warnings name a line. Measured cost: none.
        self._current_node = node
        try:
            return method(node, env)
        except astheno.AsthenoError as e:
            # Raised deep inside arena helpers with no AST access. The
            # innermost execute() frame catches it, so the reported node is
            # the precise one; outer frames see a RuntimeError and pass it on.
            raise self.error(str(e), node, prefix=e.prefix) from None

    def _astheno_site(self) -> int:
        return getattr(self._current_node, "line", 0) or 0

    def report_leaks(self) -> None:
        """Announce anything never scorched. Call at program exit."""
        report = astheno.leak_report(self.arena)
        if report:
            print(f"spooked: {report}", file=sys.stderr)

    def _astheno_warn(self, message: str) -> None:
        node = self._current_node
        line = getattr(node, "line", 0) or 0
        prefix = "spooked"
        if line:
            prefix += f" at {self.filename}:{line}" if self.filename else f" at line {line}"
        print(f"{prefix}: {message}", file=sys.stderr)

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
            msg = f"Undefined variable '{node.name}'"
            if e.suggestion:
                msg += f" — did you mean '{e.suggestion}'?"
            raise self.error(msg, node, prefix="devastate")

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

        if isinstance(left, astheno.Pine) or isinstance(right, astheno.Pine):
            return self._pine_binary_op(node, left, right)

        if isinstance(left, astheno.Fixed) or isinstance(right, astheno.Fixed):
            try:
                return astheno.binary_op(node.op, left, right)
            except astheno.AsthenoTypeError as e:
                raise self.error(str(e), node, prefix="contemplate")
            except ZeroDivisionError:
                raise self.error("Division by zero", node)

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
                raise self.error("Division by zero", node)
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
        if node.op == "in":
            if isinstance(right, dict):
                return left in right
            if isinstance(right, (list, str)):
                return left in right
            raise self.error(f"Cannot use 'in' on {type(right).__name__}", node)
        if node.op == "not in":
            if isinstance(right, dict):
                return left not in right
            if isinstance(right, (list, str)):
                return left not in right
            raise self.error(f"Cannot use 'not in' on {type(right).__name__}", node)

        raise RuntimeError(f"Unknown operator: {node.op}", node.line, node.column)

    def _pine_binary_op(self, node: ast.BinaryOp, left: Any, right: Any) -> Any:
        op = node.op
        if op in ("==", "!="):
            same = (
                isinstance(left, astheno.Pine)
                and isinstance(right, astheno.Pine)
                and left.offset == right.offset
            )
            return same if op == "==" else not same

        if op in ("+", "-"):
            # pine - pine is the distance between them, in bytes.
            if isinstance(left, astheno.Pine) and isinstance(right, astheno.Pine):
                if op == "+":
                    raise self.error(
                        "two pines cannot be added - subtract them for the "
                        "distance between them",
                        node,
                        prefix="contemplate",
                    )
                return left.offset - right.offset

            if op == "-" and not isinstance(left, astheno.Pine):
                raise self.error(
                    "cannot subtract a pine from a number", node, prefix="contemplate"
                )

            pine, delta = (left, right) if isinstance(left, astheno.Pine) else (right, left)
            if isinstance(delta, astheno.Fixed):
                delta = delta.value
            if isinstance(delta, bool) or not isinstance(delta, int):
                raise self.error(
                    f"a pine can only shift by a whole number of bytes, "
                    f"got {type(delta).__name__}",
                    node,
                    prefix="contemplate",
                )
            return pine.shifted(delta if op == "+" else -delta)

        raise self.error(
            f"'{op}' is not defined for pines", node, prefix="contemplate"
        )

    def exec_UnaryOp(self, node: ast.UnaryOp, env: Environment) -> Any:
        operand = self.execute(node.operand, env)

        if node.op == "-":
            if isinstance(operand, astheno.Fixed):
                return astheno.negate(operand)
            return -operand
        if node.op == "not":
            return not operand

        raise RuntimeError(f"Unknown unary operator: {node.op}", node.line, node.column)

    def exec_Assignment(self, node: ast.Assignment, env: Environment) -> Any:
        value = self.execute(node.value, env)
        env.set(node.name, value)
        return value

    def exec_MultiAssignment(self, node: ast.MultiAssignment, env: Environment) -> Any:
        # Evaluate all RHS values
        values = [self.execute(v, env) for v in node.values]

        # If single RHS value that is iterable (list), unpack it
        if len(values) == 1 and len(node.targets) > 1:
            iterable = values[0]
            if isinstance(iterable, (list,)):
                if len(iterable) != len(node.targets):
                    raise self.error(
                        f"Cannot unpack {len(iterable)} values into {len(node.targets)} targets",
                        node,
                    )
                values = list(iterable)

        # Validate count match
        if len(node.targets) != len(values):
            raise self.error(
                f"Multi-assignment mismatch: {len(node.targets)} targets, {len(values)} values",
                node,
            )

        # Assign each value
        for name, value in zip(node.targets, values):
            env.set(name, value)

        return values[0] if len(values) == 1 else values

    def exec_PropertyAccess(self, node: ast.PropertyAccess, env: Environment) -> Any:
        obj = self.execute(node.object, env)
        if obj is None:
            raise self.error("Cannot access property on None", node)

        if isinstance(obj, astheno.Pine):
            field = self._pine_field(obj, node.property)
            if field is not None:
                return field.get(obj)

        # Handle instance attribute/method access
        if isinstance(obj, MgsInstance):
            # First check instance attributes
            if node.property in obj.attributes:
                return obj.attributes[node.property]
            # Then check class methods
            if node.property in obj.class_def.methods:
                method = obj.class_def.methods[node.property]
                def bound_method(*args: Any) -> Any:
                    return method(obj, *args)
                return bound_method
            raise self.error(
                f"'{obj.class_def.name}' has no attribute '{node.property}'",
                node,
            )

        if isinstance(obj, dict):
            if node.property in obj:
                return obj[node.property]
            available = ", ".join(sorted(obj.keys()))
            raise self.error(f"Property '{node.property}' not found on dict. Available: {available}", node)

        if hasattr(obj, "_obj"):
            return getattr(obj, node.property)

        if hasattr(obj, node.property):
            return getattr(obj, node.property)

        raise self.error(f"Cannot access property '{node.property}' on {type(obj).__name__}", node)

    def exec_IndexAccess(self, node: ast.IndexAccess, env: Environment) -> Any:
        obj = self.execute(node.object, env)

        # Handle slice syntax: list[start:stop:step]
        if isinstance(node.index, ast.Slice):
            start = self.execute(node.index.start, env) if node.index.start else None
            stop = self.execute(node.index.stop, env) if node.index.stop else None
            step = self.execute(node.index.step, env) if node.index.step else None
            if isinstance(obj, (list, str)):
                return obj[start:stop:step]
            raise self.error(f"Cannot slice {type(obj).__name__}", node)

        index = self.execute(node.index, env)

        if isinstance(obj, astheno.Pine):
            return astheno.Fixed(obj.read_byte(self._pine_index(index, node)), astheno.SPECS["u8"])

        if isinstance(obj, list):
            if not isinstance(index, int):
                raise self.error("List index must be an integer", node)
            if index < 0 or index >= len(obj):
                raise self.error(f"List index {index} out of range (list has {len(obj)} element{'s' if len(obj) != 1 else ''})", node)
            return obj[index]

        if isinstance(obj, dict):
            if index not in obj:
                available = ", ".join(repr(k) for k in sorted(obj.keys(), key=str))
                raise self.error(f"Key {index!r} not found in dict. Available keys: {available}", node)
            return obj[index]

        if hasattr(obj, "__getitem__"):
            try:
                return obj[index]
            except (KeyError, IndexError) as e:
                raise self.error(str(e), node)

        raise self.error(f"Cannot index into {type(obj).__name__}", node)

    def exec_FunctionCall(self, node: ast.FunctionCall, env: Environment) -> Any:
        callee = self.execute(node.callee, env)
        args = [self.execute(arg, env) for arg in node.arguments]

        if callable(callee):
            try:
                result = callee(*args)
                return wrap_result(result)
            except RuntimeError:
                raise
            except TypeError as e:
                raise self.error(str(e), node, prefix="contemplate")

        raise self.error(f"Cannot call non-function: {type(callee).__name__}", node)

    def exec_MethodCall(self, node: ast.MethodCall, env: Environment) -> Any:
        obj = self.execute(node.object, env)
        args = [self.execute(arg, env) for arg in node.arguments]

        if obj is None:
            raise self.error("Cannot call method on None", node)

        # Handle instance method calls
        if isinstance(obj, MgsInstance):
            method = obj.class_def.methods.get(node.method)
            if method is None:
                raise self.error(
                    f"'{obj.class_def.name}' has no method '{node.method}'",
                    node,
                )
            try:
                result = method(obj, *args)
                return wrap_result(result)
            except RuntimeError:
                raise
            except TypeError as e:
                raise self.error(str(e), node, prefix="contemplate")

        if isinstance(obj, str):
            mgs_str = MgsString(obj)
            method = getattr(mgs_str, node.method, None)
            if method and callable(method):
                try:
                    result = method(*args)
                    return result
                except RuntimeError:
                    raise
                except TypeError as e:
                    raise self.error(str(e), node, prefix="contemplate")

        # Support calling functions stored in dicts: module.func()
        if isinstance(obj, dict) and node.method in obj:
            func = obj[node.method]
            if callable(func):
                try:
                    return func(*args)
                except RuntimeError:
                    raise
                except TypeError as e:
                    raise self.error(str(e), node, prefix="contemplate")
            return func

        if hasattr(obj, "_obj"):
            method = getattr(obj, node.method, None)
            if method:
                try:
                    result = method(*args)
                    return wrap_result(result)
                except RuntimeError:
                    raise
                except TypeError as e:
                    raise self.error(str(e), node, prefix="contemplate")

        if hasattr(obj, node.method):
            method = getattr(obj, node.method)
            if callable(method):
                try:
                    result = method(*args)
                    return wrap_result(result)
                except RuntimeError:
                    raise
                except TypeError as e:
                    raise self.error(str(e), node, prefix="contemplate")

        type_name = type(obj).__name__
        if hasattr(obj, "_obj"):
            type_name = type(obj._obj).__name__
        raise self.error(f"{type_name} has no method '{node.method}'", node)

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
            raise self.error(f"Cannot iterate over {type(iterable).__name__}", node)

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
        # Evaluate defaults at definition time
        evaluated_defaults = {
            name: self.execute(expr, env) for name, expr in node.defaults.items()
        }
        func = MgsFunction(
            params=node.params,
            body=node.body,
            closure=env,
            name=node.name,
            defaults=evaluated_defaults,
        )
        if node.name:
            env.define(node.name, func)
        return func

    def exec_ArrowFunction(self, node: ast.ArrowFunction, env: Environment) -> Any:
        evaluated_defaults = {
            name: self.execute(expr, env) for name, expr in node.defaults.items()
        }
        return MgsFunction(
            params=node.params,
            body=node.body,
            closure=env,
            defaults=evaluated_defaults,
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

    def exec_DictLiteral(self, node: ast.DictLiteral, env: Environment) -> Any:
        result = {}
        for key_node, value_node in zip(node.keys, node.values):
            key = self.execute(key_node, env)
            value = self.execute(value_node, env)
            result[key] = value
        return result

    def exec_ListComprehension(self, node: ast.ListComprehension, env: Environment) -> Any:
        iterable = self.execute(node.iterable, env)
        result = []
        child_env = env.child()
        for item in iterable:
            child_env.define(node.variable, item)
            if node.condition is not None:
                if not self._is_truthy(self.execute(node.condition, child_env)):
                    continue
            result.append(self.execute(node.element, child_env))
        return result

    def exec_InterpolatedString(self, node: ast.InterpolatedString, env: Environment) -> Any:
        parts = []
        for part in node.parts:
            value = self.execute(part, env)
            parts.append(to_display(value))
        return "".join(parts)

    def exec_ExprStatement(self, node: ast.ExprStatement, env: Environment) -> Any:
        return self.execute(node.expr, env)

    def exec_PrintStatement(self, node: ast.PrintStatement, env: Environment) -> Any:
        args = [self.execute(arg, env) for arg in node.arguments]
        print(*[to_display(a) for a in args])
        return None

    def exec_SpookedStatement(self, node: ast.SpookedStatement, env: Environment) -> Any:
        import sys
        message = to_display(self.execute(node.message, env))
        prefix = "spooked"
        if node.line:
            loc = f" at line {node.line}"
            if self.filename:
                loc = f" at {self.filename}:{node.line}"
            prefix += loc
        print(f"{prefix}: {message}", file=sys.stderr)
        return None

    def _resolve_module_path(self, module: str) -> str:
        """Resolve module path relative to current file or search path."""
        from pathlib import Path
        
        # If it's an absolute path, use it directly
        if Path(module).is_absolute():
            if not Path(module).suffix:
                return module + ".mgs"
            return module
        
        # If it's a relative path (starts with ./ or ../), resolve relative to current file
        if module.startswith("./") or module.startswith("../"):
            if self.filename:
                current_dir = Path(self.filename).parent
                resolved = (current_dir / module).resolve()
            else:
                resolved = Path(module).resolve()
            if not resolved.suffix:
                resolved = resolved.with_suffix(".mgs")
            return str(resolved)
        
        # For non-relative paths, search in current file's directory
        candidates = []
        if self.filename:
            current_dir = Path(self.filename).parent
            candidates.append(current_dir / module)
            candidates.append(current_dir / "lib" / module)
        
        # Add ~/.magmascript/lib/
        home = Path.home()
        candidates.append(home / ".magmascript" / "lib" / module)
        
        # Try with .mgs extension
        for candidate in candidates:
            if candidate.with_suffix(".mgs").exists():
                return str(candidate.with_suffix(".mgs"))
            if candidate.exists():
                return str(candidate)
        
        # If not found, return the first candidate with .mgs extension
        if candidates:
            return str(candidates[0].with_suffix(".mgs"))
        else:
            return module + ".mgs"

    def _load_module(self, module_path: str, node: ast.ImportStatement) -> Environment:
        """Load and execute a module, returning its environment."""
        from pathlib import Path
        
        # Check cache
        if module_path in self._module_cache:
            return self._module_cache[module_path]
        
        # Check for circular imports
        if module_path in self._loading_modules:
            raise RuntimeError(
                f"Circular import detected: {module_path}",
                node.line,
                node.column,
                self.filename,
                prefix="fire toad",
            )
        
        # Check file exists
        if not Path(module_path).exists():
            raise RuntimeError(
                f"Module not found: {module_path}",
                node.line,
                node.column,
                self.filename,
                prefix="fire toad",
            )
        
        # Read and parse the module
        self._loading_modules.add(module_path)
        try:
            with open(module_path, "r", encoding="utf-8") as f:
                source = f.read()
            
            from magmascript.lang.lexer import Lexer
            from magmascript.lang.parser import Parser
            
            tokens = Lexer(source, filename=module_path).tokenize()
            program = Parser(tokens, source=source, filename=module_path).parse()
            
            # Create a new interpreter for the module
            interpreter = Interpreter(source=source, filename=module_path, script_args=self._script_args)
            interpreter._module_cache = self._module_cache
            interpreter._loading_modules = self._loading_modules
            interpreter.run(program)
            
            # Cache the module
            self._module_cache[module_path] = interpreter.globals
            
            return interpreter.globals
        finally:
            self._loading_modules.discard(module_path)

    def exec_ImportStatement(self, node: ast.ImportStatement, env: Environment) -> Any:
        module_path = self._resolve_module_path(node.module)
        module_env = self._load_module(module_path, node)
        
        # Determine the namespace name - use the original module name, not the resolved path
        namespace = node.alias or node.module
        if namespace.endswith(".mgs"):
            namespace = namespace[:-4]
        # If the namespace is a full path, extract just the filename
        if "/" in namespace or "\\" in namespace:
            from pathlib import Path
            namespace = Path(namespace).stem
        
        if node.from_import:
            # Import specific names: intent { name1, name2 } from "module"
            if node.alias:
                # intent { name1, name2 } from "module" as alias
                # Create a namespace object with the specified names
                namespace_obj = {}
                for name in node.names:
                    if name in module_env.variables:
                        namespace_obj[name] = module_env.variables[name]
                    else:
                        raise RuntimeError(
                            f"Name '{name}' not found in module '{node.module}'",
                            node.line,
                            node.column,
                            self.filename,
                            prefix="fire toad",
                        )
                env.define(namespace, namespace_obj)
            else:
                # intent { name1, name2 } from "module"
                # Import names directly into current scope
                for name in node.names:
                    if name in module_env.variables:
                        env.define(name, module_env.variables[name])
                    else:
                        raise RuntimeError(
                            f"Name '{name}' not found in module '{node.module}'",
                            node.line,
                            node.column,
                            self.filename,
                            prefix="fire toad",
                        )
        else:
            # Import entire module: intent "module" or intent "module" as alias
            # Convert module environment to a dict for property access
            module_dict = dict(module_env.variables)
            env.define(namespace, module_dict)
        
        return None

    def exec_TryCatch(self, node: ast.TryCatch, env: Environment) -> Any:
        try:
            return self.execute(node.try_block, env)
        except RuntimeError as e:
            # Bind the error to the catch parameter
            catch_env = env.child()
            catch_env.define(node.catch_param, {
                "message": e.message,
                "line": e.line,
                "file": e.filename,
                "prefix": e.prefix,
                "format": lambda: e.format(),
            })
            return self.execute(node.catch_block, catch_env)

    def exec_ThrowStatement(self, node: ast.ThrowStatement, env: Environment) -> Any:
        message = self.execute(node.message, env)
        raise RuntimeError(
            str(message),
            node.line,
            node.column,
            self.filename,
            prefix=node.error_type,
        )

    def exec_FloorplanDef(self, node: ast.FloorplanDef, env: Environment) -> Any:
        from magmascript.lang.astheno.floorplan import Floorplan, build_floorplan

        known: dict[str, Floorplan] = {}
        scope: Environment | None = env
        while scope is not None:
            for key, value in scope.variables.items():
                if isinstance(value, Floorplan) and key not in known:
                    known[key] = value
            scope = scope.parent

        declared = [(f.name, f.type_name, f.count, f.points_to) for f in node.fields]
        plan = build_floorplan(node.name, declared, known)
        env.define(node.name, plan)
        return plan

    def exec_ClassDef(self, node: ast.ClassDef, env: Environment) -> Any:
        methods = {}
        for method_node in node.methods:
            # Evaluate defaults at class definition time
            evaluated_defaults = {
                name: self.execute(expr, env) for name, expr in method_node.defaults.items()
            }
            func = MgsFunction(
                params=method_node.params,
                body=method_node.body,
                closure=env,
                name=method_node.name,
                defaults=evaluated_defaults,
            )
            methods[method_node.name] = func

        mgs_class = MgsClass(
            name=node.name,
            methods=methods,
            closure=env,
        )
        env.define(node.name, mgs_class)
        return mgs_class

    def _pine_field(self, pine: Any, name: str) -> Any:
        """The floorplan field `name` on this pine, or None if it has no plan."""
        plan = pine.spec
        if getattr(plan, "fields", None) is None:
            return None
        field = plan.field_named(name)
        if field is None:
            available = ", ".join(f.name for f in plan.fields)
            raise astheno.AsthenoError(
                f"floorplan {plan.name} has no field '{name}'. Available: {available}"
            )
        return field

    def exec_PropertyAssignment(self, node: ast.PropertyAssignment, env: Environment) -> Any:
        obj = self.execute(node.object, env)
        value = self.execute(node.value, env)

        if isinstance(obj, astheno.Pine):
            field = self._pine_field(obj, node.property)
            if field is not None:
                return field.set(obj, value)

        if isinstance(obj, MgsInstance):
            obj.attributes[node.property] = value
            return value

        if isinstance(obj, dict):
            obj[node.property] = value
            return value

        # A host object from a domain — a game entity, a config, anything the
        # bridge handed back. Reading its attributes already works
        # (exec_PropertyAccess falls through to getattr), so writing them has
        # to as well, or a script can inspect an object and never change it.
        if not node.property.startswith("_") and hasattr(obj, node.property):
            if isinstance(value, astheno.Fixed):
                # Widths are an Asthenosphere concept. Handing one to a host
                # object poisons its arithmetic downstream, so store the number.
                value = value.value
            try:
                setattr(obj, node.property, value)
            except AttributeError as e:
                raise self.error(
                    f"Cannot set '{node.property}' on {type(obj).__name__}: {e}",
                    node,
                ) from None
            return value

        raise self.error(
            f"Cannot set property on {type(obj).__name__}",
            node,
        )

    def _pine_index(self, index: Any, node: ast.ASTNode) -> int:
        if isinstance(index, astheno.Fixed):
            index = index.value
        if isinstance(index, bool) or not isinstance(index, int):
            raise self.error(
                f"a pine is indexed by whole bytes, got {type(index).__name__}",
                node,
                prefix="contemplate",
            )
        return index

    def exec_IndexAssignment(self, node: ast.IndexAssignment, env: Environment) -> Any:
        obj = self.execute(node.object, env)
        index = self.execute(node.index, env)
        value = self.execute(node.value, env)

        if isinstance(obj, astheno.Pine):
            at = self._pine_index(index, node)
            if node.op != "=":
                current = obj.read_byte(at)
                raw = value.value if isinstance(value, astheno.Fixed) else value
                value = current + raw if node.op == "+=" else current - raw
            return astheno.Fixed(obj.write_byte(at, value), astheno.SPECS["u8"])

        if isinstance(obj, str):
            raise self.error("Cannot assign into a string — strings are immutable", node)

        if isinstance(obj, list):
            if not isinstance(index, int) or isinstance(index, bool):
                raise self.error("List index must be an integer", node)
            if index < 0 or index >= len(obj):
                raise self.error(
                    f"List index {index} out of range (list has {len(obj)} element{'s' if len(obj) != 1 else ''})",
                    node,
                )
        elif isinstance(obj, dict):
            pass
        else:
            raise self.error(f"Cannot assign into {type(obj).__name__}", node)

        if node.op != "=":
            if isinstance(obj, dict) and index not in obj:
                raise self.error(f"Key '{index}' not found", node, prefix="devastate")
            current = obj[index]
            try:
                value = current + value if node.op == "+=" else current - value
            except TypeError as e:
                raise self.error(str(e), node, prefix="contemplate")

        obj[index] = value
        return value

    def _is_truthy(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, astheno.Fixed):
            return value.value != 0
        if isinstance(value, astheno.Pine):
            return value.alive
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
        if isinstance(value, dict):
            return len(value) > 0
        return True


def run(source: str, script_args: list[str] | None = None) -> Any:
    from magmascript.lang.parser import parse
    program = parse(source)
    interpreter = Interpreter(source=source, script_args=script_args)
    global _thread_interpreter
    _thread_interpreter = interpreter
    try:
        return interpreter.run(program)
    finally:
        interpreter.report_leaks()
