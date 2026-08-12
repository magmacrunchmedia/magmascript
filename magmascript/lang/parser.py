from __future__ import annotations

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
        return f"string \"{preview}\""
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
        return "\n".join(parts)


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
        lines = self.source.split("\n")
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
            params = self.parse_params()
            self.expect(TokenType.RPAREN)
            body = self.parse_block()
            return ast.FunctionDef(
                name=name,
                params=params,
                body=body,
                line=token.line,
                column=token.column,
            )
        else:
            self.expect(TokenType.LPAREN)
            params = self.parse_params()
            self.expect(TokenType.RPAREN)
            body = self.parse_block()
            return ast.FunctionDef(
                name="",
                params=params,
                body=body,
                line=token.line,
                column=token.column,
            )

    def parse_params(self) -> list[str]:
        params = []
        if not self.check(TokenType.RPAREN):
            params.append(self.expect(TokenType.IDENTIFIER).value)
            while self.match(TokenType.COMMA):
                params.append(self.expect(TokenType.IDENTIFIER).value)
        return params

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

    def parse_expression_statement(self) -> ast.ASTNode:
        expr = self.parse_expression()

        if isinstance(expr, ast.Identifier):
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
        left = self.parse_addition()
        while self.check(TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            op = self.advance()
            right = self.parse_addition()
            left = ast.BinaryOp(
                op=op.value,
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
                index = self.parse_expression()
                self.expect(TokenType.RBRACKET)
                expr = ast.IndexAccess(
                    object=expr,
                    index=index,
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
            params = self.parse_params()
            self.expect(TokenType.RPAREN)
            if self.match(TokenType.ARROW):
                body_expr = self.parse_expression()
                return ast.ArrowFunction(
                    params=params,
                    body=body_expr,
                    line=token.line,
                    column=token.column,
                )
            else:
                body = self.parse_block()
                return ast.FunctionDef(
                    name="",
                    params=params,
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
