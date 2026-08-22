// ============================================================
// MagmaScript Playground — Browser-based code editor & runner
// ============================================================
// Uses Pyodide (Python WASM) to run .mgs code in the browser.
// Loads magmascript/lang/ source directly into Pyodide's FS,
// stubs out domain modules, and provides a CodeMirror 6 editor.

(async () => {
  // ----------------------------------------------------------
  // Constants
  // ----------------------------------------------------------

  const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v0.25.1/full/pyodide.js";
const LANG_FILE_CONTENTS = {
  "__init__.py": `from magmascript.lang.tokens import TokenType, Token, KEYWORDS
from magmascript.lang.lexer import Lexer
from magmascript.lang.ast_nodes import *
from magmascript.lang.parser import Parser
from magmascript.lang.interpreter import Interpreter
from magmascript.lang.environment import Environment
from magmascript.lang.builtins import BUILTINS
from magmascript.lang.domain_bridge import create_domain_proxies

__all__ = [
    "TokenType",
    "Token",
    "KEYWORDS",
    "Lexer",
    "Parser",
    "Interpreter",
    "Environment",
    "BUILTINS",
    "create_domain_proxies",
]
`,
  "tokens.py": `from __future__ import annotations

from enum import Enum, auto
from dataclasses import dataclass
from typing import Any


class TokenType(Enum):
    # Literals
    NUMBER = auto()
    STRING = auto()
    IDENTIFIER = auto()
    TRUE = auto()
    FALSE = auto()
    NONE = auto()

    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    EQ = auto()
    EQEQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LTE = auto()
    GTE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    DOT = auto()
    ARROW = auto()
    PLUS_EQ = auto()
    MINUS_EQ = auto()
    NOT_IN = auto()

    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    COLON = auto()
    SEMICOLON = auto()

    # Keywords
    IF = auto()
    ELSE = auto()
    FOR = auto()
    IN = auto()
    WHILE = auto()
    FN = auto()
    RETURN = auto()
    BREAK = auto()
    CONTINUE = auto()
    PRINT = auto()
    SPOOKED = auto()
    INTENT = auto()
    FROM = auto()
    AS = auto()
    TRY = auto()
    HAUNTER = auto()
    THROW = auto()
    CLASS = auto()
    SELF = auto()

    # Special
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    EOF = auto()


KEYWORDS: dict[str, TokenType] = {
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "none": TokenType.NONE,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "while": TokenType.WHILE,
    "fn": TokenType.FN,
    "return": TokenType.RETURN,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
    "print": TokenType.PRINT,
    "spooked": TokenType.SPOOKED,
    "intent": TokenType.INTENT,
    "from": TokenType.FROM,
    "as": TokenType.AS,
    "try": TokenType.TRY,
    "haunter": TokenType.HAUNTER,
    "throw": TokenType.THROW,
    "class": TokenType.CLASS,
    "self": TokenType.SELF,
}


@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, line={self.line})"
`,
  "ast_nodes.py": `from __future__ import annotations

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
    defaults: dict[str, ASTNode] = field(default_factory=dict)
    body: ASTNode = field(default_factory=ASTNode)


@dataclass
class ArrowFunction(ASTNode):
    params: list[str] = field(default_factory=list)
    defaults: dict[str, ASTNode] = field(default_factory=dict)
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


@dataclass
class ClassDef(ASTNode):
    name: str = ""
    methods: list[FunctionDef] = field(default_factory=list)


@dataclass
class PropertyAssignment(ASTNode):
    object: ASTNode = field(default_factory=ASTNode)
    property: str = ""
    value: ASTNode = field(default_factory=ASTNode)
    op: str = "="


@dataclass
class MultiAssignment(ASTNode):
    targets: list[str] = field(default_factory=list)
    values: list[ASTNode] = field(default_factory=list)
    op: str = "="
`,
  "lexer.py": `from __future__ import annotations

from magmascript.lang.tokens import Token, TokenType, KEYWORDS


class LexerError(Exception):
    def __init__(self, message: str, line: int, column: int, source_line: str | None = None, filename: str | None = None) -> None:
        self.line = line
        self.column = column
        self.source_line = source_line
        self.filename = filename
        self.message = message
        super().__init__(message)

    def format(self) -> str:
        parts = []
        loc = f"line {self.line}, column {self.column}"
        if self.filename:
            loc = f"{self.filename}:{loc}"
        parts.append(f"haunter at {loc}")

        if self.source_line is not None:
            line_num = str(self.line)
            padding = " " * len(line_num)
            parts.append(f"  {padding} |")
            parts.append(f"  {line_num} | {self.source_line}")
            caret = " " * (self.column - 1) + "^" * min(len(self.source_line) - self.column + 1, 20)
            parts.append(f"  {padding} | {caret}")

        parts.append(self.message)
        return "\\n".join(parts)


class Lexer:
    def __init__(self, source: str, filename: str | None = None) -> None:
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []
        self.indent_stack: list[int] = [0]
        self.paren_depth = 0

    def error(self, message: str) -> LexerError:
        source_line = self._get_source_line(self.line)
        return LexerError(message, self.line, self.column, source_line, self.filename)

    def _get_source_line(self, line_num: int) -> str | None:
        lines = self.source.split("\\n")
        if 1 <= line_num <= len(lines):
            return lines[line_num - 1]
        return None

    def peek(self) -> str | None:
        if self.pos < len(self.source):
            return self.source[self.pos]
        return None

    def advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def match(self, expected: str) -> bool:
        if self.pos < len(self.source) and self.source[self.pos] == expected:
            self.advance()
            return True
        return False

    def peek_next(self) -> str | None:
        if self.pos + 1 < len(self.source):
            return self.source[self.pos + 1]
        return None

    def skip_whitespace(self) -> None:
        while self.pos < len(self.source) and self.source[self.pos] in " \\t\\r":
            self.advance()

    def skip_comment(self) -> bool:
        if self.pos + 1 < len(self.source) and self.source[self.pos:self.pos + 2] == "//":
            while self.pos < len(self.source) and self.source[self.pos] != "\\n":
                self.advance()
            return True
        return False

    def read_string(self) -> Token:
        line, col = self.line, self.column
        quote = self.advance()
        parts: list[str] = []
        has_interpolation = False

        while self.pos < len(self.source) and self.source[self.pos] != quote:
            if self.source[self.pos] == "\\\\":
                self.advance()
                if self.pos < len(self.source):
                    esc = self.advance()
                    if esc == "n":
                        parts.append("\\n")
                    elif esc == "t":
                        parts.append("\\t")
                    elif esc == "\\\\":
                        parts.append("\\\\")
                    elif esc == quote:
                        parts.append(quote)
                    elif esc == "{":
                        parts.append("{")
                    else:
                        parts.append("\\\\" + esc)
            elif self.source[self.pos] == "{":
                has_interpolation = True
                parts.append(self.advance())
                depth = 1
                while self.pos < len(self.source) and depth > 0:
                    ch = self.source[self.pos]
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                    if depth > 0:
                        parts.append(self.advance())
                    else:
                        parts.append(self.advance())
            else:
                parts.append(self.advance())

        if self.pos >= len(self.source):
            preview = "".join(parts)[:30]
            raise self.error(f"Unterminated string starting with {quote}{preview}...")

        self.advance()
        value = "".join(parts)

        if has_interpolation:
            return Token(TokenType.STRING, ("interpolated", value), line, col)
        return Token(TokenType.STRING, ("plain", value), line, col)

    def read_number(self) -> Token:
        line, col = self.line, self.column
        start = self.pos
        has_dot = False

        while self.pos < len(self.source) and self.source[self.pos].isdigit():
            self.advance()

        if self.pos < len(self.source) and self.source[self.pos] == ".":
            if self.peek_next() and self.peek_next().isdigit():
                has_dot = True
                self.advance()
                while self.pos < len(self.source) and self.source[self.pos].isdigit():
                    self.advance()

        value_str = self.source[start:self.pos]
        value = float(value_str) if has_dot else int(value_str)
        return Token(TokenType.NUMBER, value, line, col)

    def read_identifier(self) -> Token:
        line, col = self.line, self.column
        start = self.pos

        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == "_"):
            self.advance()

        word = self.source[start:self.pos]
        token_type = KEYWORDS.get(word, TokenType.IDENTIFIER)

        # Special two-word operator: "not in"
        if word == "not":
            saved_pos, saved_line, saved_col = self.pos, self.line, self.column
            # skip whitespace
            while self.pos < len(self.source) and self.source[self.pos] in " \\t":
                self.advance()
            if self.pos < len(self.source) and self.source[self.pos:self.pos + 2] == "in":
                after_in = self.pos + 2
                if after_in >= len(self.source) or not (self.source[after_in].isalnum() or self.source[after_in] == "_"):
                    self.advance()  # consume 'i'
                    self.advance()  # consume 'n'
                    return Token(TokenType.NOT_IN, "not in", line, col)
            # restore position
            self.pos, self.line, self.column = saved_pos, saved_line, saved_col

        return Token(token_type, word, line, col)

    def handle_newline(self) -> None:
        line, col = self.line, self.column
        self.advance()

        if self.pos >= len(self.source) or self.source[self.pos] == "#" or self.source[self.pos:self.pos + 2] == "//":
            return

        if self.paren_depth > 0:
            return

        current_indent = 0
        while self.pos < len(self.source) and self.source[self.pos] in " \\t":
            current_indent += 1
            self.advance()

        if current_indent > self.indent_stack[-1]:
            self.indent_stack.append(current_indent)
            self.tokens.append(Token(TokenType.INDENT, current_indent, line, col))
        elif current_indent < self.indent_stack[-1]:
            while self.indent_stack[-1] > current_indent:
                self.indent_stack.pop()
                self.tokens.append(Token(TokenType.DEDENT, 0, self.line, self.column))
            if self.indent_stack[-1] != current_indent:
                raise self.error(f"Indentation error: expected {self.indent_stack[-1]} spaces, got {current_indent}")

    def tokenize(self) -> list[Token]:
        while self.pos < len(self.source):
            self.skip_whitespace()

            if self.pos >= len(self.source):
                break

            ch = self.source[self.pos]

            line, col = self.line, self.column

            if ch == "\\n":
                if self.paren_depth == 0:
                    self.tokens.append(Token(TokenType.NEWLINE, "\\\\n", line, col))
                    self.handle_newline()
                else:
                    self.advance()
                continue

            if ch == "#":
                while self.pos < len(self.source) and self.source[self.pos] != "\\n":
                    self.advance()
                continue

            if self.skip_comment():
                continue

            if ch == '"' or ch == "'":
                self.tokens.append(self.read_string())
            elif ch.isdigit():
                self.tokens.append(self.read_number())
            elif ch.isalpha() or ch == "_":
                token = self.read_identifier()
                if token.value == "f" and self.peek() in ('"', "'"):
                    string_token = self.read_string()
                    kind, value = string_token.value
                    self.tokens.append(Token(TokenType.STRING, ("interpolated", value), token.line, token.column))
                else:
                    self.tokens.append(token)
            elif ch == "(":
                self.paren_depth += 1
                self.tokens.append(Token(TokenType.LPAREN, "(", line, col))
                self.advance()
            elif ch == ")":
                self.paren_depth = max(0, self.paren_depth - 1)
                self.tokens.append(Token(TokenType.RPAREN, ")", line, col))
                self.advance()
            elif ch == "{":
                self.paren_depth += 1
                self.tokens.append(Token(TokenType.LBRACE, "{", line, col))
                self.advance()
            elif ch == "}":
                self.paren_depth = max(0, self.paren_depth - 1)
                self.tokens.append(Token(TokenType.RBRACE, "}", line, col))
                self.advance()
            elif ch == "[":
                self.paren_depth += 1
                self.tokens.append(Token(TokenType.LBRACKET, "[", line, col))
                self.advance()
            elif ch == "]":
                self.paren_depth = max(0, self.paren_depth - 1)
                self.tokens.append(Token(TokenType.RBRACKET, "]", line, col))
                self.advance()
            elif ch == "+":
                self.advance()
                if self.match("="):
                    self.tokens.append(Token(TokenType.PLUS_EQ, "+=", line, col))
                else:
                    self.tokens.append(Token(TokenType.PLUS, "+", line, col))
            elif ch == "-":
                self.advance()
                if self.match(">"):
                    self.tokens.append(Token(TokenType.ARROW, "->", line, col))
                elif self.match("="):
                    self.tokens.append(Token(TokenType.MINUS_EQ, "-=", line, col))
                else:
                    self.tokens.append(Token(TokenType.MINUS, "-", line, col))
            elif ch == "*":
                self.tokens.append(Token(TokenType.STAR, "*", line, col))
                self.advance()
            elif ch == "/":
                self.advance()
                if self.match("/"):
                    while self.pos < len(self.source) and self.source[self.pos] != "\\n":
                        self.advance()
                else:
                    self.tokens.append(Token(TokenType.SLASH, "/", line, col))
            elif ch == "%":
                self.tokens.append(Token(TokenType.PERCENT, "%", line, col))
                self.advance()
            elif ch == "=":
                self.advance()
                if self.match("="):
                    self.tokens.append(Token(TokenType.EQEQ, "==", line, col))
                else:
                    self.tokens.append(Token(TokenType.EQ, "=", line, col))
            elif ch == "!":
                self.advance()
                if self.match("="):
                    self.tokens.append(Token(TokenType.NEQ, "!=", line, col))
                else:
                    raise self.error(f"Unexpected character '!' — did you mean '!='?")
            elif ch == "<":
                self.advance()
                if self.match("="):
                    self.tokens.append(Token(TokenType.LTE, "<=", line, col))
                else:
                    self.tokens.append(Token(TokenType.LT, "<", line, col))
            elif ch == ">":
                self.advance()
                if self.match("="):
                    self.tokens.append(Token(TokenType.GTE, ">=", line, col))
                else:
                    self.tokens.append(Token(TokenType.GT, ">", line, col))
            elif ch == ".":
                self.tokens.append(Token(TokenType.DOT, ".", line, col))
                self.advance()
            elif ch == ",":
                self.tokens.append(Token(TokenType.COMMA, ",", line, col))
                self.advance()
            elif ch == ":":
                self.tokens.append(Token(TokenType.COLON, ":", line, col))
                self.advance()
            elif ch == ";":
                self.tokens.append(Token(TokenType.SEMICOLON, ";", line, col))
                self.advance()
            else:
                raise self.error(f"Unexpected character '{ch}'")

        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.tokens.append(Token(TokenType.DEDENT, 0, self.line, self.column))

        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return self.tokens


def tokenize(source: str) -> list[Token]:
    return Lexer(source).tokenize()
`,
  "parser.py": `from __future__ import annotations

from magmascript.lang.tokens import Token, TokenType, KEYWORDS
from magmascript.lang import ast_nodes as ast
from magmascript.lang.util import suggest


# Token type to human-readable name
TOKEN_NAMES: dict[TokenType, str] = {
    TokenType.LPAREN: "'('",
    TokenType.RPAREN: "')'",
    TokenType.LBRACE: "'{'",
    TokenType.RBRACE: "'}'",
    TokenType.LBRACKET: "'['",
    TokenType.RBRACKET: "']'",
    TokenType.COMMA: "','",
    TokenType.COLON: "':'",
    TokenType.SEMICOLON: "';'",
    TokenType.EQ: "'='",
    TokenType.EQEQ: "'=='",
    TokenType.NEQ: "'!='",
    TokenType.LT: "'<'",
    TokenType.GT: "'>'",
    TokenType.LTE: "'<='",
    TokenType.GTE: "'>='",
    TokenType.PLUS: "'+'",
    TokenType.MINUS: "'-'",
    TokenType.STAR: "'*'",
    TokenType.SLASH: "'/'",
    TokenType.PERCENT: "'%'",
    TokenType.AND: "'and'",
    TokenType.OR: "'or'",
    TokenType.NOT: "'not'",
    TokenType.DOT: "'.'",
    TokenType.ARROW: "'->'",
    TokenType.IF: "'if'",
    TokenType.ELSE: "'else'",
    TokenType.FOR: "'for'",
    TokenType.IN: "'in'",
    TokenType.WHILE: "'while'",
    TokenType.FN: "'fn'",
    TokenType.RETURN: "'return'",
    TokenType.BREAK: "'break'",
    TokenType.CONTINUE: "'continue'",
    TokenType.PRINT: "'print'",
    TokenType.SPOOKED: "'spooked'",
    TokenType.INTENT: "'intent'",
    TokenType.FROM: "'from'",
    TokenType.AS: "'as'",
    TokenType.TRY: "'try'",
    TokenType.HAUNTER: "'haunter'",
    TokenType.THROW: "'throw'",
    TokenType.CLASS: "'class'",
    TokenType.SELF: "'self'",
    TokenType.NOT_IN: "'not in'",
    TokenType.TRUE: "'true'",
    TokenType.FALSE: "'false'",
    TokenType.NONE: "'none'",
    TokenType.NEWLINE: "newline",
    TokenType.EOF: "end of file",
}


def token_display(token: Token) -> str:
    name = TOKEN_NAMES.get(token.type, token.type.name)
    if token.type == TokenType.IDENTIFIER:
        return f"identifier '{token.value}'"
    if token.type == TokenType.NUMBER:
        return f"number {token.value}"
    if token.type == TokenType.STRING:
        kind, value = token.value
        preview = value[:20] + "..." if len(value) > 20 else value
        return f"string \\"{preview}\\""
    return name


class ParseError(Exception):
    def __init__(self, message: str, token: Token, source_line: str | None = None, filename: str | None = None) -> None:
        self.token = token
        self.source_line = source_line
        self.filename = filename
        self.message = message
        super().__init__(message)

    def format(self) -> str:
        parts = []
        loc = f"line {self.token.line}, column {self.token.column}"
        if self.filename:
            loc = f"{self.filename}:{loc}"
        parts.append(f"haunter at {loc}")

        if self.source_line is not None:
            line_num = str(self.token.line)
            padding = " " * len(line_num)
            parts.append(f"  {padding} |")
            parts.append(f"  {line_num} | {self.source_line}")
            caret = " " * (self.token.column - 1) + "^"
            parts.append(f"  {padding} | {caret}")

        parts.append(self.message)
        return "\\n".join(parts)


class Parser:
    def __init__(self, tokens: list[Token], source: str | None = None, filename: str | None = None) -> None:
        self.tokens = tokens
        self.source = source
        self.filename = filename
        self.pos = 0

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def _get_source_line(self, line_num: int) -> str | None:
        if self.source is None:
            return None
        lines = self.source.split("\\n")
        if 1 <= line_num <= len(lines):
            return lines[line_num - 1]
        return None

    def error(self, message: str, token: Token | None = None) -> ParseError:
        if token is None:
            token = self.peek()
        source_line = self._get_source_line(token.line)
        return ParseError(message, token, source_line, self.filename)

    def expect(self, token_type: TokenType) -> Token:
        token = self.peek()
        if token.type != token_type:
            expected = TOKEN_NAMES.get(token_type, token_type.name)
            got = token_display(token)
            raise self.error(f"Expected {expected}, got {got}", token)
        return self.advance()

    def match(self, *types: TokenType) -> Token | None:
        if self.peek().type in types:
            return self.advance()
        return None

    def check(self, *types: TokenType) -> bool:
        return self.peek().type in types

    def skip_newlines(self) -> None:
        while self.match(TokenType.NEWLINE):
            pass

    def parse(self) -> ast.Program:
        body = self.parse_body()
        return ast.Program(body=body)

    def parse_body(self) -> list[ast.ASTNode]:
        statements = []
        self.skip_newlines()
        while not self.check(TokenType.EOF):
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
            self.skip_newlines()
        return statements

    def parse_block(self) -> ast.Block:
        if self.match(TokenType.LBRACE):
            self.skip_newlines()
            body = []
            while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
                stmt = self.parse_statement()
                if stmt:
                    body.append(stmt)
                self.skip_newlines()
            self.expect(TokenType.RBRACE)
            return ast.Block(body=body)

        self.expect(TokenType.COLON)
        self.skip_newlines()
        self.expect(TokenType.INDENT)
        body = []
        while not self.check(TokenType.DEDENT) and not self.check(TokenType.EOF):
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            self.skip_newlines()
        self.expect(TokenType.DEDENT)
        return ast.Block(body=body)

    def parse_statement(self) -> ast.ASTNode | None:
        self.skip_newlines()

        if self.check(TokenType.IF):
            return self.parse_if()
        if self.check(TokenType.FOR):
            return self.parse_for()
        if self.check(TokenType.WHILE):
            return self.parse_while()
        if self.check(TokenType.FN):
            return self.parse_function_def()
        if self.check(TokenType.RETURN):
            return self.parse_return()
        if self.check(TokenType.BREAK):
            self.advance()
            return ast.BreakStatement(line=self.tokens[self.pos - 1].line)
        if self.check(TokenType.CONTINUE):
            self.advance()
            return ast.ContinueStatement(line=self.tokens[self.pos - 1].line)
        if self.check(TokenType.PRINT) or self.check(TokenType.IDENTIFIER) and self.peek().value == "print":
            return self.parse_print()
        if self.check(TokenType.SPOOKED):
            return self.parse_spooked()
        if self.check(TokenType.INTENT):
            return self.parse_import()
        if self.check(TokenType.TRY):
            return self.parse_try_catch()
        if self.check(TokenType.THROW):
            return self.parse_throw()
        if self.check(TokenType.CLASS):
            return self.parse_class_def()

        return self.parse_expression_statement()

    def parse_if(self) -> ast.IfExpression:
        token = self.expect(TokenType.IF)
        condition = self.parse_expression()
        then_block = self.parse_block()
        else_block = None

        self.skip_newlines()
        if self.check(TokenType.ELSE):
            self.advance()
            else_block = self.parse_block()

        return ast.IfExpression(
            condition=condition,
            then_block=then_block,
            else_block=else_block,
            line=token.line,
            column=token.column,
        )

    def parse_for(self) -> ast.ForLoop:
        token = self.expect(TokenType.FOR)
        var_token = self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.IN)
        iterable = self.parse_expression()
        body = self.parse_block()

        return ast.ForLoop(
            variable=var_token.value,
            iterable=iterable,
            body=body,
            line=token.line,
            column=token.column,
        )

    def parse_while(self) -> ast.WhileLoop:
        token = self.expect(TokenType.WHILE)
        condition = self.parse_expression()
        body = self.parse_block()

        return ast.WhileLoop(
            condition=condition,
            body=body,
            line=token.line,
            column=token.column,
        )

    def parse_function_def(self) -> ast.FunctionDef | ast.ArrowFunction:
        token = self.expect(TokenType.FN)

        if self.check(TokenType.IDENTIFIER):
            name = self.advance().value
            self.expect(TokenType.LPAREN)
            params, defaults = self.parse_params()
            self.expect(TokenType.RPAREN)
            body = self.parse_block()
            return ast.FunctionDef(
                name=name,
                params=params,
                defaults=defaults,
                body=body,
                line=token.line,
                column=token.column,
            )
        else:
            self.expect(TokenType.LPAREN)
            params, defaults = self.parse_params()
            self.expect(TokenType.RPAREN)
            body = self.parse_block()
            return ast.FunctionDef(
                name="",
                params=params,
                defaults=defaults,
                body=body,
                line=token.line,
                column=token.column,
            )

    def parse_params(self) -> tuple[list[str], dict[str, ast.ASTNode]]:
        params = []
        defaults = {}
        if not self.check(TokenType.RPAREN):
            # Accept both IDENTIFIER and SELF as parameter names
            token = self.peek()
            if token.type in (TokenType.IDENTIFIER, TokenType.SELF):
                params.append(self.advance().value)
                # Check for default value
                if self.match(TokenType.EQ):
                    defaults[params[-1]] = self.parse_expression()
            else:
                raise self.error("Expected parameter name", token)
            while self.match(TokenType.COMMA):
                token = self.peek()
                if token.type in (TokenType.IDENTIFIER, TokenType.SELF):
                    params.append(self.advance().value)
                    # Check for default value
                    if self.match(TokenType.EQ):
                        defaults[params[-1]] = self.parse_expression()
                else:
                    raise self.error("Expected parameter name", token)
        return params, defaults

    def parse_return(self) -> ast.ReturnStatement:
        token = self.expect(TokenType.RETURN)
        value = None
        if not self.check(TokenType.NEWLINE) and not self.check(TokenType.EOF) and not self.check(TokenType.RBRACE):
            value = self.parse_expression()
        return ast.ReturnStatement(value=value, line=token.line, column=token.column)

    def parse_print(self) -> ast.PrintStatement:
        if self.check(TokenType.IDENTIFIER) and self.peek().value == "print":
            token = self.advance()
        else:
            token = self.advance()
        self.expect(TokenType.LPAREN)
        args = []
        if not self.check(TokenType.RPAREN):
            args.append(self.parse_expression())
            while self.match(TokenType.COMMA):
                args.append(self.parse_expression())
        self.expect(TokenType.RPAREN)
        return ast.PrintStatement(arguments=args, line=token.line, column=token.column)

    def parse_spooked(self) -> ast.SpookedStatement:
        token = self.expect(TokenType.SPOOKED)
        self.expect(TokenType.LPAREN)
        message = self.parse_expression()
        self.expect(TokenType.RPAREN)
        return ast.SpookedStatement(message=message, line=token.line, column=token.column)

    def parse_import(self) -> ast.ImportStatement:
        token = self.expect(TokenType.INTENT)
        
        # Check for "intent { name1, name2 } from "module""
        if self.check(TokenType.LBRACE):
            self.advance()
            names = []
            while not self.check(TokenType.RBRACE):
                name_token = self.expect(TokenType.IDENTIFIER)
                names.append(name_token.value)
                if not self.check(TokenType.RBRACE):
                    self.expect(TokenType.COMMA)
            self.expect(TokenType.RBRACE)
            self.expect(TokenType.FROM)
            module_token = self.expect(TokenType.STRING)
            # Handle string token value - could be tuple (quote_type, value) or just string
            module_value = module_token.value[1] if isinstance(module_token.value, tuple) else module_token.value
            
            # Check for "as alias"
            alias = ""
            if self.check(TokenType.AS):
                self.advance()
                alias_token = self.expect(TokenType.IDENTIFIER)
                alias = alias_token.value
            
            return ast.ImportStatement(
                module=module_value,
                names=names,
                alias=alias,
                from_import=True,
                line=token.line,
                column=token.column,
            )
        
        # Simple import: "intent "module"" or "intent "module" as alias"
        module_token = self.expect(TokenType.STRING)
        # Handle string token value - could be tuple (quote_type, value) or just string
        module_value = module_token.value[1] if isinstance(module_token.value, tuple) else module_token.value
        
        alias = ""
        if self.check(TokenType.AS):
            self.advance()
            alias_token = self.expect(TokenType.IDENTIFIER)
            alias = alias_token.value
        
        return ast.ImportStatement(
            module=module_value,
            alias=alias,
            from_import=False,
            line=token.line,
            column=token.column,
        )

    def parse_try_catch(self) -> ast.TryCatch:
        token = self.expect(TokenType.TRY)
        try_block = self.parse_block()
        
        self.skip_newlines()
        self.expect(TokenType.HAUNTER)
        self.expect(TokenType.LPAREN)
        catch_param = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.RPAREN)
        catch_block = self.parse_block()
        
        return ast.TryCatch(
            try_block=try_block,
            catch_param=catch_param,
            catch_block=catch_block,
            line=token.line,
            column=token.column,
        )

    def parse_throw(self) -> ast.ThrowStatement:
        token = self.expect(TokenType.THROW)
        # Parse error type: "fire toad" or just an identifier
        if self.check(TokenType.IDENTIFIER) and self.peek().value == "fire":
            self.advance()  # consume 'fire'
            self.expect(TokenType.IDENTIFIER)  # consume 'toad'
            error_type = "fire toad"
        elif self.check(TokenType.IDENTIFIER):
            error_type = self.advance().value
        else:
            error_type = "fire toad"
        
        message = self.parse_expression()
        return ast.ThrowStatement(
            error_type=error_type,
            message=message,
            line=token.line,
            column=token.column,
        )

    def parse_class_def(self) -> ast.ClassDef:
        token = self.expect(TokenType.CLASS)
        name_token = self.expect(TokenType.IDENTIFIER)
        
        # Support both brace block and indent block
        if self.match(TokenType.LBRACE):
            self.skip_newlines()
            methods = []
            while not self.check(TokenType.RBRACE) and not self.check(TokenType.EOF):
                if self.check(TokenType.FN):
                    methods.append(self.parse_function_def())
                else:
                    raise self.error("Expected method definition (fn) inside class", self.peek())
                self.skip_newlines()
            self.expect(TokenType.RBRACE)
        else:
            self.expect(TokenType.COLON)
            self.skip_newlines()
            self.expect(TokenType.INDENT)
            methods = []
            while not self.check(TokenType.DEDENT) and not self.check(TokenType.EOF):
                self.skip_newlines()
                if self.check(TokenType.FN):
                    methods.append(self.parse_function_def())
                else:
                    raise self.error("Expected method definition (fn) inside class", self.peek())
                self.skip_newlines()
            self.expect(TokenType.DEDENT)
        
        return ast.ClassDef(
            name=name_token.value,
            methods=methods,
            line=token.line,
            column=token.column,
        )

    def parse_expression_statement(self) -> ast.ASTNode:
        expr = self.parse_expression()

        if isinstance(expr, ast.Identifier):
            # Check for multi-assignment: a, b, c = 1, 2, 3
            if self.match(TokenType.COMMA):
                names = [expr.name]
                # Parse additional target names
                while True:
                    name_token = self.expect(TokenType.IDENTIFIER)
                    names.append(name_token.value)
                    if not self.match(TokenType.COMMA):
                        break
                self.expect(TokenType.EQ)
                # Parse RHS values
                values = [self.parse_expression()]
                while self.match(TokenType.COMMA):
                    if self.check(TokenType.NEWLINE) or self.check(TokenType.EOF):
                        break
                    values.append(self.parse_expression())
                return ast.MultiAssignment(
                    targets=names,
                    values=values,
                    op="=",
                    line=expr.line,
                    column=expr.column,
                )

            if self.match(TokenType.EQ):
                value = self.parse_expression()
                return ast.Assignment(
                    name=expr.name,
                    value=value,
                    op="=",
                    line=expr.line,
                    column=expr.column,
                )
            elif self.match(TokenType.PLUS_EQ):
                value = self.parse_expression()
                return ast.Assignment(
                    name=expr.name,
                    value=ast.BinaryOp(
                        op="+",
                        left=expr,
                        right=value,
                        line=expr.line,
                        column=expr.column,
                    ),
                    op="+=",
                    line=expr.line,
                    column=expr.column,
                )
            elif self.match(TokenType.MINUS_EQ):
                value = self.parse_expression()
                return ast.Assignment(
                    name=expr.name,
                    value=ast.BinaryOp(
                        op="-",
                        left=expr,
                        right=value,
                        line=expr.line,
                        column=expr.column,
                    ),
                    op="-=",
                    line=expr.line,
                    column=expr.column,
                )

        return ast.ExprStatement(expr=expr, line=expr.line, column=expr.column)

    def parse_expression(self) -> ast.ASTNode:
        return self.parse_assignment()

    def parse_assignment(self) -> ast.ASTNode:
        expr = self.parse_or()

        if isinstance(expr, ast.Identifier):
            if self.match(TokenType.EQ):
                value = self.parse_assignment()
                return ast.Assignment(
                    name=expr.name,
                    value=value,
                    op="=",
                    line=expr.line,
                    column=expr.column,
                )

        # Handle property assignment: obj.prop = value
        if isinstance(expr, ast.PropertyAccess):
            if self.match(TokenType.EQ):
                value = self.parse_assignment()
                return ast.PropertyAssignment(
                    object=expr.object,
                    property=expr.property,
                    value=value,
                    op="=",
                    line=expr.line,
                    column=expr.column,
                )

        return expr

    def parse_or(self) -> ast.ASTNode:
        left = self.parse_and()
        while self.check(TokenType.OR):
            op = self.advance()
            right = self.parse_and()
            left = ast.BinaryOp(
                op="or",
                left=left,
                right=right,
                line=op.line,
                column=op.column,
            )
        return left

    def parse_and(self) -> ast.ASTNode:
        left = self.parse_equality()
        while self.check(TokenType.AND):
            op = self.advance()
            right = self.parse_equality()
            left = ast.BinaryOp(
                op="and",
                left=left,
                right=right,
                line=op.line,
                column=op.column,
            )
        return left

    def parse_equality(self) -> ast.ASTNode:
        left = self.parse_comparison()
        while self.check(TokenType.EQEQ, TokenType.NEQ):
            op = self.advance()
            right = self.parse_comparison()
            left = ast.BinaryOp(
                op=op.value,
                left=left,
                right=right,
                line=op.line,
                column=op.column,
            )
        return left

    def parse_comparison(self) -> ast.ASTNode:
        left = self.parse_in()
        while self.check(TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            op = self.advance()
            right = self.parse_in()
            left = ast.BinaryOp(
                op=op.value,
                left=left,
                right=right,
                line=op.line,
                column=op.column,
            )
        return left

    def parse_in(self) -> ast.ASTNode:
        left = self.parse_addition()
        while self.check(TokenType.IN) or self.check(TokenType.NOT_IN):
            op = self.advance()
            right = self.parse_addition()
            op_str = "not in" if op.type == TokenType.NOT_IN else "in"
            left = ast.BinaryOp(
                op=op_str,
                left=left,
                right=right,
                line=op.line,
                column=op.column,
            )
        return left

    def parse_addition(self) -> ast.ASTNode:
        left = self.parse_multiplication()
        while self.check(TokenType.PLUS, TokenType.MINUS):
            op = self.advance()
            right = self.parse_multiplication()
            left = ast.BinaryOp(
                op=op.value,
                left=left,
                right=right,
                line=op.line,
                column=op.column,
            )
        return left

    def parse_multiplication(self) -> ast.ASTNode:
        left = self.parse_unary()
        while self.check(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self.advance()
            right = self.parse_unary()
            left = ast.BinaryOp(
                op=op.value,
                left=left,
                right=right,
                line=op.line,
                column=op.column,
            )
        return left

    def parse_unary(self) -> ast.ASTNode:
        if self.check(TokenType.MINUS):
            op = self.advance()
            operand = self.parse_unary()
            return ast.UnaryOp(op="-", operand=operand, line=op.line, column=op.column)
        if self.check(TokenType.NOT):
            op = self.advance()
            operand = self.parse_unary()
            return ast.UnaryOp(op="not", operand=operand, line=op.line, column=op.column)
        return self.parse_postfix()

    def parse_postfix(self) -> ast.ASTNode:
        expr = self.parse_primary()

        while True:
            if self.match(TokenType.DOT):
                prop = self.expect(TokenType.IDENTIFIER)
                if self.check(TokenType.LPAREN):
                    self.advance()
                    args = self.parse_arguments()
                    self.expect(TokenType.RPAREN)
                    expr = ast.MethodCall(
                        object=expr,
                        method=prop.value,
                        arguments=args,
                        line=prop.line,
                        column=prop.column,
                    )
                else:
                    expr = ast.PropertyAccess(
                        object=expr,
                        property=prop.value,
                        line=prop.line,
                        column=prop.column,
                    )
            elif self.match(TokenType.LBRACKET):
                # Check if this is a slice (starts with ':' or is '[]')
                if self.check(TokenType.COLON) or self.check(TokenType.RBRACKET):
                    # Slice with no start: [:stop] or [::step] or [:stop:step]
                    start = None
                    stop = None
                    step = None
                    if self.match(TokenType.COLON):
                        if not self.check(TokenType.RBRACKET) and not self.check(TokenType.COLON):
                            stop = self.parse_expression()
                    if self.match(TokenType.COLON):
                        if not self.check(TokenType.RBRACKET):
                            step = self.parse_expression()
                    self.expect(TokenType.RBRACKET)
                    expr = ast.IndexAccess(
                        object=expr,
                        index=ast.Slice(start=start, stop=stop, step=step, line=expr.line, column=expr.column),
                        line=expr.line,
                        column=expr.column,
                    )
                else:
                    first = self.parse_expression()
                    if self.match(TokenType.COLON):
                        # This is a slice: first:...
                        stop = None
                        step = None
                        if not self.check(TokenType.RBRACKET) and not self.check(TokenType.COLON):
                            stop = self.parse_expression()
                        if self.match(TokenType.COLON):
                            if not self.check(TokenType.RBRACKET):
                                step = self.parse_expression()
                        self.expect(TokenType.RBRACKET)
                        expr = ast.IndexAccess(
                            object=expr,
                            index=ast.Slice(start=first, stop=stop, step=step, line=first.line, column=first.column),
                            line=expr.line,
                            column=expr.column,
                        )
                    else:
                        self.expect(TokenType.RBRACKET)
                        expr = ast.IndexAccess(
                            object=expr,
                            index=first,
                            line=expr.line,
                            column=expr.column,
                        )
            elif self.check(TokenType.LPAREN):
                self.advance()
                args = self.parse_arguments()
                self.expect(TokenType.RPAREN)
                expr = ast.FunctionCall(
                    callee=expr,
                    arguments=args,
                    line=expr.line,
                    column=expr.column,
                )
            else:
                break

        return expr

    def parse_primary(self) -> ast.ASTNode:
        token = self.peek()

        if self.match(TokenType.NUMBER):
            return ast.NumberLiteral(value=token.value, line=token.line, column=token.column)

        if self.match(TokenType.STRING):
            kind, value = token.value
            if kind == "interpolated":
                parts = self.parse_interpolation(value)
                return ast.InterpolatedString(parts=parts, line=token.line, column=token.column)
            return ast.StringLiteral(value=value, line=token.line, column=token.column)

        if self.match(TokenType.TRUE):
            return ast.BoolLiteral(value=True, line=token.line, column=token.column)

        if self.match(TokenType.FALSE):
            return ast.BoolLiteral(value=False, line=token.line, column=token.column)

        if self.match(TokenType.NONE):
            return ast.NoneLiteral(line=token.line, column=token.column)

        if self.match(TokenType.IDENTIFIER):
            name_token = self.tokens[self.pos - 1]
            if self.check(TokenType.ARROW):
                self.advance()
                body_expr = self.parse_expression()
                return ast.ArrowFunction(
                    params=[name_token.value],
                    body=body_expr,
                    line=name_token.line,
                    column=name_token.column,
                )
            return ast.Identifier(name=name_token.value, line=name_token.line, column=name_token.column)

        # Treat 'self' as an identifier in expressions
        if self.match(TokenType.SELF):
            name_token = self.tokens[self.pos - 1]
            return ast.Identifier(name="self", line=name_token.line, column=name_token.column)

        if self.match(TokenType.LPAREN):
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr

        if self.match(TokenType.LBRACKET):
            elements = []
            if not self.check(TokenType.RBRACKET):
                first_expr = self.parse_expression()
                if self.check(TokenType.FOR):
                    self.advance()
                    var_token = self.expect(TokenType.IDENTIFIER)
                    self.expect(TokenType.IN)
                    iterable = self.parse_expression()
                    condition = None
                    if self.check(TokenType.IF):
                        self.advance()
                        condition = self.parse_expression()
                    self.expect(TokenType.RBRACKET)
                    return ast.ListComprehension(
                        element=first_expr,
                        variable=var_token.value,
                        iterable=iterable,
                        condition=condition,
                        line=token.line,
                        column=token.column,
                    )
                elements.append(first_expr)
                while self.match(TokenType.COMMA):
                    if self.check(TokenType.RBRACKET):
                        break
                    elements.append(self.parse_expression())
            self.expect(TokenType.RBRACKET)
            return ast.ListLiteral(elements=elements, line=token.line, column=token.column)

        if self.match(TokenType.LBRACE):
            keys = []
            values = []
            if not self.check(TokenType.RBRACE):
                key = self.parse_expression()
                self.expect(TokenType.COLON)
                value = self.parse_expression()
                keys.append(key)
                values.append(value)
                while self.match(TokenType.COMMA):
                    if self.check(TokenType.RBRACE):
                        break
                    key = self.parse_expression()
                    self.expect(TokenType.COLON)
                    value = self.parse_expression()
                    keys.append(key)
                    values.append(value)
            self.expect(TokenType.RBRACE)
            return ast.DictLiteral(keys=keys, values=values, line=token.line, column=token.column)

        if self.match(TokenType.FN):
            self.expect(TokenType.LPAREN)
            params, defaults = self.parse_params()
            self.expect(TokenType.RPAREN)
            if self.match(TokenType.ARROW):
                body_expr = self.parse_expression()
                return ast.ArrowFunction(
                    params=params,
                    defaults=defaults,
                    body=body_expr,
                    line=token.line,
                    column=token.column,
                )
            else:
                body = self.parse_block()
                return ast.FunctionDef(
                    name="",
                    params=params,
                    defaults=defaults,
                    body=body,
                    line=token.line,
                    column=token.column,
                )

        got = token_display(token)
        msg = f"Unexpected {got}"

        if token.type == TokenType.IDENTIFIER:
            kw = suggest(token.value, list(KEYWORDS.keys()))
            if kw:
                msg += f" — did you mean '{kw}'?"

        raise self.error(msg, token)

    def parse_interpolation(self, template: str) -> list[ast.ASTNode]:
        parts = []
        i = 0
        while i < len(template):
            if template[i] == "{":
                j = i + 1
                depth = 1
                while j < len(template) and depth > 0:
                    if template[j] == "{":
                        depth += 1
                    elif template[j] == "}":
                        depth -= 1
                    j += 1
                inner = template[i + 1:j - 1]
                inner_tokens = _tokenize_expression(inner)
                inner_parser = Parser(inner_tokens)
                parts.append(inner_parser.parse_expression())
                i = j
            else:
                start = i
                while i < len(template) and template[i] != "{":
                    i += 1
                text = template[start:i]
                if text:
                    parts.append(ast.StringLiteral(value=text))
        return parts

    def parse_arguments(self) -> list[ast.ASTNode]:
        args = []
        if not self.check(TokenType.RPAREN):
            args.append(self.parse_expression())
            while self.match(TokenType.COMMA):
                if self.check(TokenType.RPAREN):
                    break
                args.append(self.parse_expression())
        return args


def _tokenize_expression(source: str) -> list[Token]:
    from magmascript.lang.lexer import Lexer
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    filtered = [t for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT)]
    return filtered


def parse(source: str) -> ast.Program:
    from magmascript.lang.lexer import tokenize
    tokens = tokenize(source)
    parser = Parser(tokens)
    return parser.parse()
`,
  "interpreter.py": `from __future__ import annotations

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

        return "\\n".join(parts)


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
        # Add HTTP proxy for .mgs scripts
        from magmascript.lang.builtins import HttpProxy
        self.globals.define("http", HttpProxy())

    def _get_source_line(self, line_num: int) -> str | None:
        if self.source is None:
            return None
        lines = self.source.split("\\n")
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
        if "/" in namespace or "\\\\" in namespace:
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

    def exec_PropertyAssignment(self, node: ast.PropertyAssignment, env: Environment) -> Any:
        obj = self.execute(node.object, env)
        value = self.execute(node.value, env)

        if isinstance(obj, MgsInstance):
            obj.attributes[node.property] = value
            return value

        if isinstance(obj, dict):
            obj[node.property] = value
            return value

        raise self.error(
            f"Cannot set property on {type(obj).__name__}",
            node,
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
`,
  "environment.py": `from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from magmascript.lang.util import suggest


class EnvironmentError(Exception):
    def __init__(self, message: str, suggestion: str | None = None) -> None:
        self.suggestion = suggestion
        super().__init__(message)


@dataclass
class Environment:
    parent: Environment | None = None
    variables: dict[str, Any] = field(default_factory=dict)

    def get(self, name: str) -> Any:
        if name in self.variables:
            return self.variables[name]
        if self.parent is not None:
            return self.parent.get(name)
        candidates = self._collect_names()
        hint = suggest(name, candidates) if candidates else None
        raise EnvironmentError(f"Undefined variable '{name}'", hint)

    def set(self, name: str, value: Any) -> None:
        if name in self.variables:
            self.variables[name] = value
            return
        if self.parent is not None and self.parent.has(name):
            self.parent.set(name, value)
            return
        self.variables[name] = value

    def define(self, name: str, value: Any) -> None:
        self.variables[name] = value

    def has(self, name: str) -> bool:
        if name in self.variables:
            return True
        if self.parent is not None:
            return self.parent.has(name)
        return False

    def child(self) -> Environment:
        return Environment(parent=self)

    def _collect_names(self) -> list[str]:
        names = list(self.variables.keys())
        if self.parent is not None:
            names.extend(self.parent._collect_names())
        return names
`,
  "builtins.py": `from __future__ import annotations

from typing import Any, Callable


class HttpProxy:
    """HTTP client for making requests from .mgs scripts."""

    def get(self, url: str, **kwargs: Any) -> dict:
        """Make a GET request and return status, text, json, headers."""
        import httpx
        try:
            response = httpx.get(url, timeout=30, **kwargs)
            result: dict[str, Any] = {
                "status": response.status_code,
                "text": response.text,
                "headers": dict(response.headers),
            }
            try:
                result["json"] = response.json()
            except Exception:
                result["json"] = None
            return result
        except httpx.TimeoutException:
            raise TimeoutError(f"http.get: request timed out after 30 seconds: {url}")
        except httpx.RequestError as e:
            raise ConnectionError(f"http.get: request failed: {e}")

    def post(self, url: str, body: Any = None, **kwargs: Any) -> dict:
        """Make a POST request and return status, text, json, headers."""
        import httpx
        try:
            response = httpx.post(url, json=body, timeout=30, **kwargs)
            result = {
                "status": response.status_code,
                "text": response.text,
                "headers": dict(response.headers),
            }
            try:
                result["json"] = response.json()
            except Exception:
                result["json"] = None
            return result
        except httpx.TimeoutException:
            raise TimeoutError(f"http.post: request timed out after 30 seconds: {url}")
        except httpx.RequestError as e:
            raise ConnectionError(f"http.post: request failed: {e}")


def builtin_print(*args: Any) -> None:
    print(*[str(a) for a in args])


def builtin_echo(*args: Any) -> None:
    print(*[str(a) for a in args])


def builtin_len(value: Any) -> int:
    from magmascript.lang.domain_bridge import ListWrapper, DataclassWrapper
    if isinstance(value, (str, list, dict, ListWrapper)):
        return len(value)
    if isinstance(value, DataclassWrapper):
        obj = object.__getattribute__(value, "_obj")
        if hasattr(obj, "__len__"):
            return len(obj)
    raise TypeError(f"len() expected string, list, or dict, got {type(value).__name__}")


def builtin_type(value: Any) -> str:
    from magmascript.lang.interpreter import MgsClass, MgsInstance
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    if isinstance(value, MgsInstance):
        return value.class_def.name
    if isinstance(value, MgsClass):
        return "class"
    if callable(value):
        return "function"
    return "object"


def builtin_str(value: Any) -> str:
    if value is None:
        return "none"
    return str(value)


def builtin_int(value: Any) -> int:
    if isinstance(value, str):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    raise TypeError(f"int() expected string or number, got {type(value).__name__}")


def builtin_float(value: Any) -> float:
    if isinstance(value, str):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    raise TypeError(f"float() expected string or number, got {type(value).__name__}")


def builtin_range(*args: Any) -> list[int]:
    if len(args) == 1:
        return list(range(int(args[0])))
    if len(args) == 2:
        return list(range(int(args[0]), int(args[1])))
    if len(args) == 3:
        return list(range(int(args[0]), int(args[1]), int(args[2])))
    raise TypeError(f"range() takes 1-3 arguments, got {len(args)}")


def builtin_keys(value: Any) -> list[str]:
    if isinstance(value, dict):
        return list(value.keys())
    raise TypeError(f"keys() expected dict, got {type(value).__name__}")


def builtin_values(value: Any) -> list[Any]:
    if isinstance(value, dict):
        return list(value.values())
    raise TypeError(f"values() expected dict, got {type(value).__name__}")


def builtin_abs(value: Any) -> int | float:
    if isinstance(value, (int, float)):
        return abs(value)
    raise TypeError(f"abs() expected number, got {type(value).__name__}")


def builtin_min(*args: Any) -> Any:
    if len(args) == 1 and isinstance(args[0], list):
        return min(args[0])
    return min(args)


def builtin_max(*args: Any) -> Any:
    if len(args) == 1 and isinstance(args[0], list):
        return max(args[0])
    return max(args)


def builtin_sum(*args: Any) -> Any:
    if len(args) == 1 and isinstance(args[0], list):
        return sum(args[0])
    return sum(args)


def builtin_quarry(path: str) -> str:
    """Read file contents (quarry stone from the ground)."""
    from pathlib import Path
    try:
        return Path(path).read_text()
    except FileNotFoundError:
        raise FileNotFoundError(f"quarry: file not found: {path}")
    except IsADirectoryError:
        raise IsADirectoryError(f"quarry: is a directory: {path}")


def builtin_litho(path: str, content: str) -> None:
    """Write content to file (lithography - writing on stone)."""
    from pathlib import Path
    try:
        Path(path).write_text(content)
    except IsADirectoryError:
        raise IsADirectoryError(f"litho: is a directory: {path}")


def builtin_exec(command: str) -> dict:
    """Execute a shell command and return stdout, stderr, and exit code."""
    import subprocess
    try:
        result = subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"exec: command timed out after 30 seconds: {command}")


BUILTINS: dict[str, Callable] = {
    "print": builtin_print,
    "echo": builtin_echo,
    "len": builtin_len,
    "type": builtin_type,
    "str": builtin_str,
    "int": builtin_int,
    "float": builtin_float,
    "range": builtin_range,
    "keys": builtin_keys,
    "values": builtin_values,
    "abs": builtin_abs,
    "min": builtin_min,
    "max": builtin_max,
    "sum": builtin_sum,
    "quarry": builtin_quarry,
    "litho": builtin_litho,
    "exec": builtin_exec,
}
`,
  "domain_bridge.py": `from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any

from magmascript.core.registry import get_domain, list_domains


class DomainProxy:
    def __init__(self, name: str, client: Any) -> None:
        self._name = name
        self._client = client

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)

        method = getattr(self._client, name, None)
        if method is None:
            raise AttributeError(f"'{self._name}' has no method '{name}'")

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = method(*args, **kwargs)
            return wrap_result(result)

        return wrapper

    def close(self) -> None:
        if hasattr(self._client, "close"):
            try:
                self._client.close()
            except Exception:
                pass

    def __del__(self) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"<domain:{self._name}>"


class DataclassWrapper:
    def __init__(self, obj: Any) -> None:
        object.__setattr__(self, "_obj", obj)

    def __getattr__(self, name: str) -> Any:
        obj = object.__getattribute__(self, "_obj")
        if is_dataclass(obj) and not isinstance(obj, type):
            for f in fields(obj):
                if f.name == name:
                    return wrap_result(getattr(obj, name))
        raise AttributeError(f"'{type(obj).__name__}' has no attribute '{name}'")

    def __repr__(self) -> str:
        obj = object.__getattribute__(self, "_obj")
        return repr(obj)

    def __str__(self) -> str:
        obj = object.__getattribute__(self, "_obj")
        return str(obj)


class ListWrapper:
    def __init__(self, items: list[Any]) -> None:
        self._items = [wrap_result(item) for item in items]

    def __getitem__(self, index: int) -> Any:
        return self._items[index]

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Any:
        return iter(self._items)

    def __repr__(self) -> str:
        return repr(self._items)

    def __str__(self) -> str:
        return str(self._items)


def wrap_result(result: Any) -> Any:
    from magmascript.lang.interpreter import MgsInstance, MgsClass
    if result is None:
        return None
    if isinstance(result, (int, float, str, bool)):
        return result
    if callable(result):
        return result
    if isinstance(result, (MgsInstance, MgsClass)):
        return result
    if isinstance(result, list):
        return ListWrapper(result)
    if is_dataclass(result) and not isinstance(result, type):
        return DataclassWrapper(result)
    return result


def create_domain_proxies() -> dict[str, DomainProxy]:
    from magmascript.core.config import get_config

    proxies = {}
    config = get_config()

    for name in list_domains():
        try:
            client_class = get_domain(name)
            client = client_class(config)
            proxies[name] = DomainProxy(name, client)
        except Exception:
            pass

    return proxies
`,
  "util.py": `from __future__ import annotations


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    a_len, b_len = len(a), len(b)
    matrix = [[0] * (b_len + 1) for _ in range(a_len + 1)]

    for i in range(a_len + 1):
        matrix[i][0] = i
    for j in range(b_len + 1):
        matrix[0][j] = j

    for i in range(1, a_len + 1):
        for j in range(1, b_len + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,
                matrix[i][j - 1] + 1,
                matrix[i - 1][j - 1] + cost,
            )

    return matrix[a_len][b_len]


def suggest(name: str, candidates: list[str], max_distance: int = 2) -> str | None:
    best: str | None = None
    best_distance = max_distance + 1

    for candidate in candidates:
        d = levenshtein(name.lower(), candidate.lower())
        if d < best_distance:
            best_distance = d
            best = candidate

    if best_distance <= max_distance:
        return best
    return None
`,
};
  const EXAMPLES = [
    "hello",
    "fibonacci",
    "lists",
    "dictionaries",
    "strings",
    "classes",
    "control-flow",
    "slicing",
    "error-handling",
    "multi-assignment",
    "builtins",
    "advanced-functions",
    "brand-commands",
  ];

  const LANG_FILES = [
    "__init__.py",
    "tokens.py",
    "ast_nodes.py",
    "lexer.py",
    "parser.py",
    "interpreter.py",
    "environment.py",
    "builtins.py",
    "domain_bridge.py",
    "util.py",
  ];

  // ----------------------------------------------------------
  // DOM references
  // ----------------------------------------------------------

  const editorPanel = document.getElementById("editor-panel");
  const divider = document.getElementById("divider");
  const outputContent = document.getElementById("output-content");
  const consoleLog = document.getElementById("console-log");
  const loadingBar = document.getElementById("loading-bar");
  const statusInterp = document.getElementById("status-interp");
  const statusExample = document.getElementById("status-example");
  const statusReady = document.getElementById("status-ready");
  const exampleSelect = document.getElementById("example-select");
  const runBtn = document.getElementById("run");
  const resetBtn = document.getElementById("reset");
  const aboutBtn = document.getElementById("about-btn");
  const aboutModal = document.getElementById("about-modal");

  // ----------------------------------------------------------
  // State
  // ----------------------------------------------------------

  let pyodide = null;
  let editorView = null;
  let originalCode = "";

  // ----------------------------------------------------------
  // Logging helpers
  // ----------------------------------------------------------

  function logInit(msg) {
    const el = document.createElement("div");
    el.className = "console-line log";
    el.textContent = msg;
    consoleLog.appendChild(el);
    consoleLog.scrollTop = consoleLog.scrollHeight;
  }

  function logError(msg) {
    const el = document.createElement("div");
    el.className = "console-line error";
    el.textContent = msg;
    consoleLog.appendChild(el);
    consoleLog.scrollTop = consoleLog.scrollHeight;
  }

  function setStatus(html) {
    statusReady.innerHTML = html;
  }

  function setLoading(visible) {
    loadingBar.classList.toggle("hidden", !visible);
  }

  // ----------------------------------------------------------
  // CodeMirror 6 setup (independent of Pyodide)
  // ----------------------------------------------------------

  async function initEditor() {
    logInit("Loading CodeMirror...");

    // Import each module individually for better error reporting
    const stateMod = await import("https://esm.sh/@codemirror/state@6");
    const viewMod = await import("https://esm.sh/@codemirror/view@6");
    const jsMod = await import("https://esm.sh/@codemirror/lang-javascript@6");
    const themeMod = await import("https://esm.sh/@codemirror/theme-one-dark@6");

    const EditorState = stateMod.EditorState;
    const EditorView = viewMod.EditorView;
    const keymap = viewMod.keymap;
    const javascript = jsMod.javascript;
    const oneDark = themeMod.oneDark;

    if (!EditorState || !EditorView || !keymap || !javascript || !oneDark) {
      throw new Error(
        `CodeMirror import failed: EditorState=${!!EditorState}, EditorView=${!!EditorView}, keymap=${!!keymap}, javascript=${!!javascript}, oneDark=${!!oneDark}`
      );
    }

    const runKeymap = keymap.of([
      {
        key: "Ctrl-Enter",
        run: () => {
          runCode();
          return true;
        },
      },
      {
        key: "Cmd-Enter",
        run: () => {
          runCode();
          return true;
        },
      },
    ]);

    const state = EditorState.create({
      doc: "// Write MagmaScript code here\nprint('Hello, MagmaScript!')\n",
      extensions: [
        javascript(),
        oneDark,
        runKeymap,
        EditorView.lineWrapping,
        EditorView.theme({
          "&": { height: "100%" },
          ".cm-scroller": { overflow: "auto" },
        }),
      ],
    });

    editorView = new EditorView({
      state,
      parent: editorPanel,
    });

    logInit("CodeMirror ready");
  }

  // ----------------------------------------------------------
  // Pyodide bootstrap (sequential, step-by-step)
  // ----------------------------------------------------------

  async function initPyodide() {
    // Step 1: Load the Pyodide script from CDN
    logInit("Loading Pyodide runtime...");
    setStatus('<span class="dot loading"></span>loading');

    const script = document.createElement("script");
    script.src = PYODIDE_CDN;
    document.head.appendChild(script);
    await new Promise((resolve, reject) => {
      script.onload = resolve;
      script.onerror = () => reject(new Error("Failed to load Pyodide CDN script"));
    });
    logInit("Pyodide script loaded");

    // Step 2: Initialize Pyodide WASM runtime
    logInit("Initializing WASM runtime (this may take a moment)...");
    const loadFn = window.loadPyodide;
    if (typeof loadFn !== "function") {
      throw new Error(
        "loadPyodide not found on window. Pyodide script may not have loaded correctly."
      );
    }
    pyodide = await loadFn({
      indexURL: "https://cdn.jsdelivr.net/pyodide/v0.25.1/full/",
    });
    logInit("WASM runtime ready");

    // Step 3: Set up filesystem directories
    logInit("Creating filesystem...");
    const fs = pyodide.FS;

    // Create all directories explicitly
    const dirs = [
      "/home/pyodide/magmascript",
      "/home/pyodide/magmascript/lang",
      "/home/pyodide/magmascript/core",
    ];
    for (const dir of dirs) {
      if (!fs.analyzePath(dir).exists) {
        fs.mkdirTree(dir);
      }
    }
    logInit("Directories created");

    // Step 4: Write embedded lang source files
    for (const name of LANG_FILES) {
      const content = LANG_FILE_CONTENTS[name];
      fs.writeFile(`/home/pyodide/magmascript/lang/${name}`, content);
    }
    logInit(`All ${LANG_FILES.length} lang files installed`);

    // Step 5: Install stub modules (core/registry, core/config)
    logInit("Installing stub modules...");

    fs.writeFile("/home/pyodide/magmascript/core/__init__.py", "");

    fs.writeFile(
      "/home/pyodide/magmascript/core/registry.py",
      `REGISTRY = {}
def register_domain(name, module):
    REGISTRY[name] = module
def get_domain(name):
    return REGISTRY.get(name)
def list_domains():
    return list(REGISTRY.keys())
`
    );

    fs.writeFile(
      "/home/pyodide/magmascript/core/config.py",
      `from dataclasses import dataclass, field

@dataclass
class Config:
    pass

def get_config():
    return Config()
`
    );

    // Custom package init — only imports lang, skips domain clients
    fs.writeFile(
      "/home/pyodide/magmascript/__init__.py",
      `from magmascript import lang
`
    );

    logInit("Stub modules installed");

    // Step 6: Add to sys.path and test Python import
    logInit("Configuring Python path...");
    pyodide.runPython(`
import sys
sys.path.insert(0, '/home/pyodide')
`);

    logInit("Testing Python imports...");
    try {
      pyodide.runPython(`
from magmascript.lang.tokens import TokenType, Token, KEYWORDS
from magmascript.lang.lexer import Lexer
from magmascript.lang.parser import Parser
from magmascript.lang.interpreter import Interpreter
print(f"Import OK: Lexer={Lexer.__name__}, Parser={Parser.__name__}, Interpreter={Interpreter.__name__}")
`);
    } catch (e) {
      throw new Error(`Python import failed: ${e.message}`);
    }
    logInit("Python imports verified");

    // Step 7: Install the runner function
    logInit("Installing runner...");
    pyodide.runPython(RUNNER_CODE);
    logInit("Runner installed");

    // Done
    setLoading(false);
    statusInterp.innerHTML = '<span class="dot ok"></span>Pyodide';
    setStatus('<span class="dot ok"></span>Ready');
  }

  // ----------------------------------------------------------
  // Runner code (executed inside Pyodide)
  // ----------------------------------------------------------

  const RUNNER_CODE = `
import io
import sys
from magmascript.lang.lexer import Lexer
from magmascript.lang.parser import Parser
from magmascript.lang.interpreter import Interpreter

def _run(code):
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()
    try:
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens, code)
        tree = parser.parse()
        interpreter = Interpreter(source=code)
        interpreter.run(tree)
        return buffer.getvalue()
    except Exception as e:
        sys.stdout = old_stdout
        return str(e)
    finally:
        sys.stdout = old_stdout
`;

  // ----------------------------------------------------------
  // Code execution
  // ----------------------------------------------------------

  function runCode() {
    if (!pyodide) {
      logError("Interpreter not ready — still loading");
      return;
    }

    const code = editorView.state.doc.toString();
    if (!code.trim()) {
      logError("No code to run");
      return;
    }

    consoleLog.innerHTML = "";
    logInit("Running...");

    try {
      pyodide.globals.set("__code", code);
      const output = pyodide.runPython("_run(__code)");
      outputContent.textContent = output || "(no output)";
      logInit("Done");
    } catch (err) {
      outputContent.textContent = "";
      logError(`Error: ${err.message}`);
    }
  }

  // ----------------------------------------------------------
  // Example loading
  // ----------------------------------------------------------

  async function loadExample(name) {
    statusExample.textContent = `example: ${name}`;
    try {
      const resp = await fetch(`examples/${name}.mgs`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const code = await resp.text();
      originalCode = code;
      editorView.dispatch({
        changes: { from: 0, to: editorView.state.doc.length, insert: code },
      });
    } catch (err) {
      logError(`Failed to load example: ${err.message}`);
    }
  }

  function populateExamples() {
    exampleSelect.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "\u2014 select example \u2014";
    placeholder.disabled = true;
    placeholder.selected = true;
    exampleSelect.appendChild(placeholder);

    EXAMPLES.forEach((name) => {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      exampleSelect.appendChild(opt);
    });
  }

  // ----------------------------------------------------------
  // Split pane
  // ----------------------------------------------------------

  function initSplitPane() {
    let isDragging = false;
    const outputPanel = document.getElementById("output-panel");

    divider.addEventListener("mousedown", (e) => {
      isDragging = true;
      e.preventDefault();
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    });

    document.addEventListener("mousemove", (e) => {
      if (!isDragging) return;
      const container = document.querySelector("main");
      const rect = container.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      const clamped = Math.min(Math.max(pct, 20), 80);
      editorPanel.style.flex = `0 0 ${clamped}%`;
      outputPanel.style.flex = `0 0 ${100 - clamped}%`;
    });

    document.addEventListener("mouseup", () => {
      if (!isDragging) return;
      isDragging = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    });
  }

  // ----------------------------------------------------------
  // About modal
  // ----------------------------------------------------------

  function initAboutModal() {
    const modalClose = aboutModal.querySelector(".modal-close");

    aboutBtn.addEventListener("click", () => {
      aboutModal.showModal();
    });

    modalClose.addEventListener("click", () => {
      aboutModal.close();
    });

    aboutModal.addEventListener("click", (e) => {
      if (e.target === aboutModal) aboutModal.close();
    });
  }

  // ----------------------------------------------------------
  // Event wiring
  // ----------------------------------------------------------

  function wireEvents() {
    runBtn.addEventListener("click", runCode);
    resetBtn.addEventListener("click", () => {
      editorView.dispatch({
        changes: {
          from: 0,
          to: editorView.state.doc.length,
          insert: originalCode,
        },
      });
      outputContent.textContent = "";
      consoleLog.innerHTML = "";
    });

    exampleSelect.addEventListener("change", (e) => {
      if (e.target.value) loadExample(e.target.value);
    });
  }

  // ----------------------------------------------------------
  // Init — sequential, with per-step error handling
  // ----------------------------------------------------------

  try {
    // Phase 1: Editor (independent of Pyodide)
    await initEditor();

    // Phase 2: Pyodide (the heavy lift)
    await initPyodide();

    // Phase 3: UI wiring
    populateExamples();
    wireEvents();
    initSplitPane();
    initAboutModal();
  } catch (err) {
    console.error("Playground init failed:", err);
    setLoading(false);
    setStatus('<span class="dot err"></span>Error');
    logError(`Init failed: ${err.message}`);
    if (err.stack) {
      logError(err.stack.split("\n").slice(0, 3).join(" | "));
    }
  }
})();
