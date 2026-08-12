from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from magmascript.lang import ast_nodes as ast
from magmascript.lang.environment import Environment, EnvironmentError
from magmascript.lang.builtins import BUILTINS
from magmascript.lang.domain_bridge import create_domain_proxies, wrap_result
from magmascript.lang.util import suggest


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

    def __call__(self, *args: Any) -> Any:
        if len(args) != len(self.params):
            name = self.name or "anonymous"
            raise RuntimeError(f"{name}() takes {len(self.params)} argument{'s' if len(self.params) != 1 else ''} but {len(args)} {'were' if len(args) != 1 else 'was'} given")

        child_env = self.closure.child()
        for param, arg in zip(self.params, args):
            child_env.define(param, arg)

        interp = _get_thread_interpreter()
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
        self._script_args = script_args or []
        self._module_cache: dict[str, Environment] = {}
        self._loading_modules: set[str] = set()
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
            raise self.error("Cannot access property on None", node)

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
        index = self.execute(node.index, env)

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
            parts.append(str(value))
        return "".join(parts)

    def exec_ExprStatement(self, node: ast.ExprStatement, env: Environment) -> Any:
        return self.execute(node.expr, env)

    def exec_PrintStatement(self, node: ast.PrintStatement, env: Environment) -> Any:
        args = [self.execute(arg, env) for arg in node.arguments]
        print(*[str(a) for a in args])
        return None

    def exec_SpookedStatement(self, node: ast.SpookedStatement, env: Environment) -> Any:
        import sys
        message = self.execute(node.message, env)
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
            with open(module_path, "r") as f:
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


def run(source: str, script_args: list[str] | None = None) -> Any:
    from magmascript.lang.parser import parse
    program = parse(source)
    interpreter = Interpreter(source=source, script_args=script_args)
    global _thread_interpreter
    _thread_interpreter = interpreter
    return interpreter.run(program)
