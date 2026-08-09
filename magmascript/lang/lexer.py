from __future__ import annotations

from magmascript.lang.tokens import Token, TokenType, KEYWORDS


class LexerError(Exception):
    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(f"Line {line}, Column {column}: {message}")
        self.line = line
        self.column = column


class Lexer:
    def __init__(self, source: str) -> None:
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []
        self.indent_stack: list[int] = [0]
        self.paren_depth = 0

    def error(self, message: str) -> LexerError:
        return LexerError(message, self.line, self.column)

    def peek(self) -> str | None:
        if self.pos < len(self.source):
            return self.source[self.pos]
        return None

    def advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
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
        while self.pos < len(self.source) and self.source[self.pos] in " \t\r":
            self.advance()

    def skip_comment(self) -> bool:
        if self.pos + 1 < len(self.source) and self.source[self.pos:self.pos + 2] == "//":
            while self.pos < len(self.source) and self.source[self.pos] != "\n":
                self.advance()
            return True
        return False

    def read_string(self) -> Token:
        line, col = self.line, self.column
        quote = self.advance()
        parts: list[str] = []
        has_interpolation = False

        while self.pos < len(self.source) and self.source[self.pos] != quote:
            if self.source[self.pos] == "\\":
                self.advance()
                if self.pos < len(self.source):
                    esc = self.advance()
                    if esc == "n":
                        parts.append("\n")
                    elif esc == "t":
                        parts.append("\t")
                    elif esc == "\\":
                        parts.append("\\")
                    elif esc == quote:
                        parts.append(quote)
                    elif esc == "{":
                        parts.append("{")
                    else:
                        parts.append("\\" + esc)
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
            raise self.error("Unterminated string")

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
        return Token(token_type, word, line, col)

    def handle_newline(self) -> None:
        line, col = self.line, self.column
        self.advance()

        if self.pos >= len(self.source) or self.source[self.pos] == "#" or self.source[self.pos:self.pos + 2] == "//":
            return

        if self.paren_depth > 0:
            return

        current_indent = 0
        while self.pos < len(self.source) and self.source[self.pos] in " \t":
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
                raise self.error("Indentation error")

    def tokenize(self) -> list[Token]:
        while self.pos < len(self.source):
            self.skip_whitespace()

            if self.pos >= len(self.source):
                break

            ch = self.source[self.pos]

            line, col = self.line, self.column

            if ch == "\n":
                if self.paren_depth == 0:
                    self.tokens.append(Token(TokenType.NEWLINE, "\\n", line, col))
                    self.handle_newline()
                else:
                    self.advance()
                continue

            if ch == "#":
                while self.pos < len(self.source) and self.source[self.pos] != "\n":
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
                    while self.pos < len(self.source) and self.source[self.pos] != "\n":
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
                    raise self.error(f"Unexpected character: !")
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
                raise self.error(f"Unexpected character: {ch}")

        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.tokens.append(Token(TokenType.DEDENT, 0, self.line, self.column))

        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return self.tokens


def tokenize(source: str) -> list[Token]:
    return Lexer(source).tokenize()
