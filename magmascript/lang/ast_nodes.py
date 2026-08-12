from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ASTNode:
    line: int = 0
    column: int = 0


@dataclass
class Program(ASTNode):
    body: list[ASTNode] = field(default_factory=list)


@dataclass
class Block(ASTNode):
    body: list[ASTNode] = field(default_factory=list)


@dataclass
class NumberLiteral(ASTNode):
    value: int | float = 0


@dataclass
class StringLiteral(ASTNode):
    value: str = ""
    interpolated: bool = False
    parts: list[Any] = field(default_factory=list)


@dataclass
class BoolLiteral(ASTNode):
    value: bool = False


@dataclass
class NoneLiteral(ASTNode):
    pass


@dataclass
class Identifier(ASTNode):
    name: str = ""


@dataclass
class BinaryOp(ASTNode):
    op: str = ""
    left: ASTNode = field(default_factory=ASTNode)
    right: ASTNode = field(default_factory=ASTNode)


@dataclass
class UnaryOp(ASTNode):
    op: str = ""
    operand: ASTNode = field(default_factory=ASTNode)


@dataclass
class Assignment(ASTNode):
    name: str = ""
    value: ASTNode = field(default_factory=ASTNode)
    op: str = "="


@dataclass
class PropertyAccess(ASTNode):
    object: ASTNode = field(default_factory=ASTNode)
    property: str = ""


@dataclass
class IndexAccess(ASTNode):
    object: ASTNode = field(default_factory=ASTNode)
    index: ASTNode = field(default_factory=ASTNode)


@dataclass
class Slice(ASTNode):
    start: ASTNode | None = None
    stop: ASTNode | None = None
    step: ASTNode | None = None


@dataclass
class FunctionCall(ASTNode):
    callee: ASTNode = field(default_factory=ASTNode)
    arguments: list[ASTNode] = field(default_factory=list)


@dataclass
class MethodCall(ASTNode):
    object: ASTNode = field(default_factory=ASTNode)
    method: str = ""
    arguments: list[ASTNode] = field(default_factory=list)


@dataclass
class IfExpression(ASTNode):
    condition: ASTNode = field(default_factory=ASTNode)
    then_block: ASTNode = field(default_factory=ASTNode)
    else_block: ASTNode | None = None


@dataclass
class ForLoop(ASTNode):
    variable: str = ""
    iterable: ASTNode = field(default_factory=ASTNode)
    body: ASTNode = field(default_factory=ASTNode)


@dataclass
class WhileLoop(ASTNode):
    condition: ASTNode = field(default_factory=ASTNode)
    body: ASTNode = field(default_factory=ASTNode)


@dataclass
class FunctionDef(ASTNode):
    name: str = ""
    params: list[str] = field(default_factory=list)
    body: ASTNode = field(default_factory=ASTNode)


@dataclass
class ArrowFunction(ASTNode):
    params: list[str] = field(default_factory=list)
    body: ASTNode = field(default_factory=ASTNode)


@dataclass
class ReturnStatement(ASTNode):
    value: ASTNode | None = None


@dataclass
class BreakStatement(ASTNode):
    pass


@dataclass
class ContinueStatement(ASTNode):
    pass


@dataclass
class ListLiteral(ASTNode):
    elements: list[ASTNode] = field(default_factory=list)


@dataclass
class DictLiteral(ASTNode):
    keys: list[ASTNode] = field(default_factory=list)
    values: list[ASTNode] = field(default_factory=list)


@dataclass
class ListComprehension(ASTNode):
    element: ASTNode = field(default_factory=ASTNode)
    variable: str = ""
    iterable: ASTNode = field(default_factory=ASTNode)
    condition: ASTNode | None = None


@dataclass
class InterpolatedString(ASTNode):
    parts: list[ASTNode] = field(default_factory=list)


@dataclass
class ExprStatement(ASTNode):
    expr: ASTNode = field(default_factory=ASTNode)


@dataclass
class PrintStatement(ASTNode):
    arguments: list[ASTNode] = field(default_factory=list)


@dataclass
class SpookedStatement(ASTNode):
    message: ASTNode = field(default_factory=StringLiteral)


@dataclass
class ImportStatement(ASTNode):
    module: str = ""
    names: list[str] = field(default_factory=list)
    alias: str = ""
    from_import: bool = False


@dataclass
class TryCatch(ASTNode):
    try_block: ASTNode = field(default_factory=Block)
    catch_param: str = ""
    catch_block: ASTNode = field(default_factory=Block)


@dataclass
class ThrowStatement(ASTNode):
    error_type: str = "fire toad"
    message: ASTNode = field(default_factory=StringLiteral)
