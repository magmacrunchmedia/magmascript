"""hypnagogia - the pass that runs at the threshold, just before execution.

The state between waking and sleep. Nothing has run yet; the program is walked
once and asked what it is about to do wrong.

MagmaScript is dynamic, so this pass is deliberately timid. It reports only
what cannot be explained away by control flow:

* A name that is never bound *anywhere* in an enclosing scope. Order is
  ignored on purpose - ``if c { x = 1 }`` followed by ``print(x)`` is legal
  when ``c`` holds, and flagging it would be a false alarm. A name bound
  nowhere at all, though, is a typo.
* Statements sitting after a ``return``, ``break``, or ``continue`` in the same
  block, which can never run.

Findings are warnings, not errors: a program that has always worked keeps
working. Floorplan and width faults stay where they are, raised for real when
the declaration is executed.

Custom rules can be registered via ``register_rule()``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from magmascript.lang import ast_nodes as ast
from magmascript.lang.util import suggest
from magmascript.lang.visitor import Visitor, children


@dataclass
class Finding:
    line: int
    column: int
    message: str

    def render(self, filename: str | None = None) -> str:
        where = f"{filename}:{self.line}" if filename else f"line {self.line}"
        return f"hypnagogia at {where}: {self.message}"


TERMINATORS = (ast.ReturnStatement, ast.BreakStatement, ast.ContinueStatement)


# -- custom rule registry ------------------------------------------------

_rules: list[tuple[str, callable]] = []


def register_rule(name: str, checker: callable) -> None:
    """Register a custom hypnagogia rule.

    The checker receives (program, findings) and appends to findings.
    """
    _rules.append((name, checker))


def list_rules() -> list[str]:
    """Return names of all registered rules."""
    return [name for name, _ in _rules]


# -- the main pass -------------------------------------------------------

class Hypnagogia(Visitor):
    def __init__(self, global_names: set[str] | None = None) -> None:
        super().__init__()
        self.findings: list[Finding] = []
        self.globals: set[str] = set(global_names or ())
        self._scopes: list[set[str]] = []

    # -- entry ----------------------------------------------------------

    def inspect(self, program: ast.Program) -> list[Finding]:
        bound = set(self.globals) | self._bindings(program.body)
        self._scopes = [bound]
        self._check_unreachable(program.body)
        for stmt in program.body:
            self.visit(stmt)

        # Run custom rules
        for name, checker in _rules:
            checker(program, self.findings)

        self.findings.sort(key=lambda f: (f.line, f.column))
        return self.findings

    # -- binding collection ---------------------------------------------

    def _bindings(self, nodes: list[ast.ASTNode]) -> set[str]:
        """Every name bound anywhere beneath `nodes`, at this function level.

        Nested function bodies are not descended into: their inner names are
        not visible out here.
        """
        found: set[str] = set()
        for node in nodes:
            self._collect(node, found)
        return found

    def _collect(self, node: ast.ASTNode, found: set[str]) -> None:
        if node is None:
            return

        if isinstance(node, ast.Assignment):
            found.add(node.name)
        elif isinstance(node, ast.MultiAssignment):
            found.update(node.targets)
        elif isinstance(node, ast.FunctionDef):
            found.add(node.name)
            return  # body belongs to its own scope
        elif isinstance(node, ast.ArrowFunction):
            return
        elif isinstance(node, ast.ClassDef):
            found.add(node.name)
            return
        elif isinstance(node, ast.FloorplanDef):
            found.add(node.name)
            return
        elif isinstance(node, ast.ForLoop):
            found.add(node.variable)
        elif isinstance(node, ast.ListComprehension):
            found.add(node.variable)
        elif isinstance(node, ast.TryCatch):
            if node.catch_param:
                found.add(node.catch_param)
        elif isinstance(node, ast.ImportStatement):
            if node.alias:
                found.add(node.alias)
            for name in node.names:
                found.add(name)
            if not node.alias and not node.names:
                found.add(node.module.replace("/", ".").split(".")[-1])

        for child in children(node):
            self._collect(child, found)

    # -- visitor methods ------------------------------------------------

    def visit_Identifier(self, node: ast.Identifier) -> None:
        if not any(node.name in scope for scope in self._scopes):
            known = set().union(*self._scopes) if self._scopes else set()
            hint = suggest(node.name, sorted(known)) if known else None
            message = f"'{node.name}' is never given a value"
            if hint:
                message += f" - did you mean '{hint}'?"
            self.findings.append(Finding(node.line, node.column, message))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        inner = set(node.params)
        body = node.body
        inner |= self._bindings(getattr(body, "body", [body]))
        for default in node.defaults.values():
            self.visit(default)
        self._scopes.append(inner)
        self.visit(body)
        self._scopes.pop()

    def visit_ArrowFunction(self, node: ast.ArrowFunction) -> None:
        inner = set(node.params)
        body = node.body
        inner |= self._bindings(getattr(body, "body", [body]))
        for default in node.defaults.values():
            self.visit(default)
        self._scopes.append(inner)
        self.visit(body)
        self._scopes.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for method in node.methods:
            inner = set(method.params) | {"self"}
            body = method.body
            inner |= self._bindings(getattr(body, "body", [body]))
            self._scopes.append(inner)
            self.visit(body)
            self._scopes.pop()

    def visit_FloorplanDef(self, node: ast.FloorplanDef) -> None:
        pass  # field types are checked when the declaration runs

    def visit_PropertyAccess(self, node: ast.PropertyAccess) -> None:
        self.visit(node.object)
        # the property name is not a variable

    def visit_PropertyAssignment(self, node: ast.PropertyAssignment) -> None:
        self.visit(node.object)
        self.visit(node.value)

    def visit_MethodCall(self, node: ast.MethodCall) -> None:
        self.visit(node.object)
        for arg in node.arguments:
            self.visit(arg)

    def visit_Block(self, node: ast.Block) -> None:
        self._check_unreachable(node.body)
        for child in children(node):
            self.visit(child)

    # -- unreachable code -----------------------------------------------

    def _check_unreachable(self, body: list[ast.ASTNode]) -> None:
        for index, stmt in enumerate(body):
            if isinstance(stmt, TERMINATORS) and index + 1 < len(body):
                nxt = body[index + 1]
                word = type(stmt).__name__.replace("Statement", "").lower()
                self.findings.append(
                    Finding(
                        getattr(nxt, "line", 0),
                        getattr(nxt, "column", 0),
                        f"this can never run - the {word} above always leaves first",
                    )
                )
                return


def inspect(program: ast.Program, global_names: set[str] | None = None) -> list[Finding]:
    return Hypnagogia(global_names).inspect(program)
