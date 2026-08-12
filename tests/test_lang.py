"""Exhaustive tests for the MagmaScript language."""

from __future__ import annotations

import pytest

from magmascript.lang.tokens import TokenType, Token
from magmascript.lang.lexer import Lexer, LexerError
from magmascript.lang.parser import Parser, ParseError
from magmascript.lang.ast_nodes import (
    Program, Block, NumberLiteral, StringLiteral, BoolLiteral, NoneLiteral,
    Identifier, BinaryOp, UnaryOp, Assignment, PropertyAccess, IndexAccess,
    FunctionCall, MethodCall, IfExpression, ForLoop, WhileLoop,
    FunctionDef, ArrowFunction, ReturnStatement, BreakStatement,
    ContinueStatement, ListLiteral, InterpolatedString, ExprStatement,
    PrintStatement,
)
from magmascript.lang.environment import Environment, EnvironmentError
from magmascript.lang.interpreter import Interpreter, RuntimeError as MgsRuntimeError, run


# =============================================================================
# LEXER TESTS
# =============================================================================

class TestLexerNumbers:
    def test_integer(self):
        tokens = Lexer("42").tokenize()
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == 42

    def test_float(self):
        tokens = Lexer("3.14").tokenize()
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == 3.14

    def test_negative_number(self):
        tokens = Lexer("-5").tokenize()
        assert tokens[0].type == TokenType.MINUS
        assert tokens[1].type == TokenType.NUMBER
        assert tokens[1].value == 5

    def test_zero(self):
        tokens = Lexer("0").tokenize()
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == 0


class TestLexerStrings:
    def test_plain_string(self):
        tokens = Lexer('"hello"').tokenize()
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == ("plain", "hello")

    def test_single_quote_string(self):
        tokens = Lexer("'world'").tokenize()
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == ("plain", "world")

    def test_escaped_newline(self):
        tokens = Lexer('"line1\\nline2"').tokenize()
        assert tokens[0].value == ("plain", "line1\nline2")

    def test_escaped_tab(self):
        tokens = Lexer('"col1\\tcol2"').tokenize()
        assert tokens[0].value == ("plain", "col1\tcol2")

    def test_escaped_quote(self):
        tokens = Lexer('"say \\"hello\\""').tokenize()
        assert tokens[0].value == ('plain', 'say "hello"')

    def test_unterminated_string(self):
        with pytest.raises(LexerError, match="Unterminated string"):
            Lexer('"hello').tokenize()


class TestLexerFStrings:
    def test_fstring_interpolation(self):
        tokens = Lexer('f"hello {name}"').tokenize()
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value[0] == "interpolated"
        assert "name" in tokens[0].value[1]

    def test_fstring_with_expression(self):
        tokens = Lexer('f"{x + 1}"').tokenize()
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value[0] == "interpolated"


class TestLexerOperators:
    def test_arithmetic_operators(self):
        tokens = Lexer("1 + 2 - 3 * 4 / 5 % 6").tokenize()
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        assert types == [
            TokenType.NUMBER, TokenType.PLUS, TokenType.NUMBER,
            TokenType.MINUS, TokenType.NUMBER, TokenType.STAR,
            TokenType.NUMBER, TokenType.SLASH, TokenType.NUMBER,
            TokenType.PERCENT, TokenType.NUMBER,
        ]

    def test_comparison_operators(self):
        tokens = Lexer("1 == 2 != 3 < 4 > 5 <= 6 >= 7").tokenize()
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        assert types == [
            TokenType.NUMBER, TokenType.EQEQ, TokenType.NUMBER,
            TokenType.NEQ, TokenType.NUMBER, TokenType.LT,
            TokenType.NUMBER, TokenType.GT, TokenType.NUMBER,
            TokenType.LTE, TokenType.NUMBER, TokenType.GTE,
            TokenType.NUMBER,
        ]

    def test_logical_operators(self):
        tokens = Lexer("true and false or not true").tokenize()
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        assert types == [
            TokenType.TRUE, TokenType.AND, TokenType.FALSE,
            TokenType.OR, TokenType.NOT, TokenType.TRUE,
        ]

    def test_assignment_operators(self):
        tokens = Lexer("x = 1 x += 2 x -= 3").tokenize()
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        assert TokenType.EQ in types
        assert TokenType.PLUS_EQ in types
        assert TokenType.MINUS_EQ in types

    def test_arrow_operator(self):
        tokens = Lexer("->").tokenize()
        assert tokens[0].type == TokenType.ARROW

    def test_dot_operator(self):
        tokens = Lexer("obj.prop").tokenize()
        assert tokens[1].type == TokenType.DOT


class TestLexerKeywords:
    def test_all_keywords(self):
        source = "if else for in while fn return break continue and or not true false none print"
        tokens = Lexer(source).tokenize()
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        assert types == [
            TokenType.IF, TokenType.ELSE, TokenType.FOR, TokenType.IN,
            TokenType.WHILE, TokenType.FN, TokenType.RETURN, TokenType.BREAK,
            TokenType.CONTINUE, TokenType.AND, TokenType.OR, TokenType.NOT,
            TokenType.TRUE, TokenType.FALSE, TokenType.NONE, TokenType.PRINT,
        ]

    def test_identifier_not_keyword(self):
        tokens = Lexer("ifelse forin").tokenize()
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].value == "ifelse"
        assert tokens[1].type == TokenType.IDENTIFIER
        assert tokens[1].value == "forin"


class TestLexerIndentation:
    def test_indent_dedent(self):
        source = "if true:\n    x = 1\ny = 2\n"
        tokens = Lexer(source).tokenize()
        types = [t.type for t in tokens]
        assert TokenType.INDENT in types
        assert TokenType.DEDENT in types

    def test_no_indent_in_parens(self):
        source = "x = (\n    1 + 2\n)\n"
        tokens = Lexer(source).tokenize()
        types = [t.type for t in tokens]
        assert TokenType.INDENT not in types
        assert TokenType.DEDENT not in types

    def test_nested_indent(self):
        source = "if true:\n    if true:\n        x = 1\n"
        tokens = Lexer(source).tokenize()
        indent_count = sum(1 for t in tokens if t.type == TokenType.INDENT)
        dedent_count = sum(1 for t in tokens if t.type == TokenType.DEDENT)
        assert indent_count == 2
        assert dedent_count == 2


class TestLexerErrors:
    def test_unexpected_character(self):
        with pytest.raises(LexerError, match="Unexpected character"):
            Lexer("@").tokenize()

    def test_unexpected_bang(self):
        with pytest.raises(LexerError, match="Unexpected character"):
            Lexer("!").tokenize()


class TestLexerComments:
    def test_single_line_comment(self):
        tokens = Lexer("// this is a comment\nx = 1").tokenize()
        non_newline = [t for t in tokens if t.type != TokenType.NEWLINE and t.type != TokenType.EOF]
        assert non_newline[0].type == TokenType.IDENTIFIER
        assert non_newline[0].value == "x"

    def test_hash_comment(self):
        tokens = Lexer("# this is a comment\nx = 1").tokenize()
        non_newline = [t for t in tokens if t.type != TokenType.NEWLINE and t.type != TokenType.EOF]
        assert non_newline[0].type == TokenType.IDENTIFIER
        assert non_newline[0].value == "x"


class TestLexerNewlines:
    def test_newline_tokens(self):
        tokens = Lexer("x = 1\ny = 2\n").tokenize()
        newline_count = sum(1 for t in tokens if t.type == TokenType.NEWLINE)
        assert newline_count >= 1


# =============================================================================
# PARSER TESTS
# =============================================================================

class TestParserLiterals:
    def test_number_literal(self):
        program = Parser(Lexer("42").tokenize()).parse()
        assert len(program.body) == 1
        stmt = program.body[0]
        assert isinstance(stmt, ExprStatement)
        assert isinstance(stmt.expr, NumberLiteral)
        assert stmt.expr.value == 42

    def test_string_literal(self):
        program = Parser(Lexer('"hello"').tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, ExprStatement)
        assert isinstance(stmt.expr, StringLiteral)
        assert stmt.expr.value == "hello"

    def test_bool_true(self):
        program = Parser(Lexer("true").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, ExprStatement)
        assert isinstance(stmt.expr, BoolLiteral)
        assert stmt.expr.value is True

    def test_bool_false(self):
        program = Parser(Lexer("false").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, ExprStatement)
        assert isinstance(stmt.expr, BoolLiteral)
        assert stmt.expr.value is False

    def test_none_literal(self):
        program = Parser(Lexer("none").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, ExprStatement)
        assert isinstance(stmt.expr, NoneLiteral)


class TestParserBinaryOps:
    def test_addition(self):
        program = Parser(Lexer("1 + 2").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, ExprStatement)
        assert isinstance(stmt.expr, BinaryOp)
        assert stmt.expr.op == "+"

    def test_subtraction(self):
        program = Parser(Lexer("5 - 3").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt.expr, BinaryOp)
        assert stmt.expr.op == "-"

    def test_multiplication(self):
        program = Parser(Lexer("4 * 7").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt.expr, BinaryOp)
        assert stmt.expr.op == "*"

    def test_division(self):
        program = Parser(Lexer("10 / 2").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt.expr, BinaryOp)
        assert stmt.expr.op == "/"

    def test_modulo(self):
        program = Parser(Lexer("10 % 3").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt.expr, BinaryOp)
        assert stmt.expr.op == "%"

    def test_equality(self):
        program = Parser(Lexer("x == y").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt.expr, BinaryOp)
        assert stmt.expr.op == "=="

    def test_not_equal(self):
        program = Parser(Lexer("x != y").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt.expr, BinaryOp)
        assert stmt.expr.op == "!="

    def test_less_than(self):
        program = Parser(Lexer("x < y").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt.expr, BinaryOp)
        assert stmt.expr.op == "<"

    def test_greater_than(self):
        program = Parser(Lexer("x > y").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt.expr, BinaryOp)
        assert stmt.expr.op == ">"

    def test_less_equal(self):
        program = Parser(Lexer("x <= y").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt.expr, BinaryOp)
        assert stmt.expr.op == "<="

    def test_greater_equal(self):
        program = Parser(Lexer("x >= y").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt.expr, BinaryOp)
        assert stmt.expr.op == ">="

    def test_and_operator(self):
        program = Parser(Lexer("x and y").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt.expr, BinaryOp)
        assert stmt.expr.op == "and"

    def test_or_operator(self):
        program = Parser(Lexer("x or y").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt.expr, BinaryOp)
        assert stmt.expr.op == "or"


class TestParserUnaryOps:
    def test_negation(self):
        program = Parser(Lexer("-x").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, ExprStatement)
        assert isinstance(stmt.expr, UnaryOp)
        assert stmt.expr.op == "-"

    def test_not_operator(self):
        program = Parser(Lexer("not x").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, ExprStatement)
        assert isinstance(stmt.expr, UnaryOp)
        assert stmt.expr.op == "not"


class TestParserAssignment:
    def test_simple_assignment(self):
        program = Parser(Lexer("x = 5").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, ExprStatement)
        assert isinstance(stmt.expr, Assignment)
        assert stmt.expr.name == "x"
        assert isinstance(stmt.expr.value, NumberLiteral)

    def test_plus_equals(self):
        program = Parser(Lexer("x += 3").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, Assignment)
        assert stmt.name == "x"
        assert stmt.op == "+="
        assert isinstance(stmt.value, BinaryOp)

    def test_minus_equals(self):
        program = Parser(Lexer("x -= 2").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, Assignment)
        assert stmt.name == "x"
        assert stmt.op == "-="
        assert isinstance(stmt.value, BinaryOp)


class TestParserPropertyAccess:
    def test_dot_access(self):
        program = Parser(Lexer("obj.prop").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, ExprStatement)
        assert isinstance(stmt.expr, PropertyAccess)
        assert stmt.expr.property == "prop"

    def test_chained_access(self):
        program = Parser(Lexer("a.b.c").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt.expr, PropertyAccess)
        assert isinstance(stmt.expr.object, PropertyAccess)
        assert stmt.expr.object.property == "b"
        assert isinstance(stmt.expr.object.object, Identifier)
        assert stmt.expr.object.object.name == "a"


class TestParserIndexAccess:
    def test_bracket_access(self):
        program = Parser(Lexer("arr[0]").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, ExprStatement)
        assert isinstance(stmt.expr, IndexAccess)
        assert isinstance(stmt.expr.index, NumberLiteral)


class TestParserFunctionCalls:
    def test_simple_call(self):
        program = Parser(Lexer("print(42)").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, PrintStatement)
        assert len(stmt.arguments) == 1

    def test_method_call(self):
        program = Parser(Lexer("obj.method(arg)").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, ExprStatement)
        assert isinstance(stmt.expr, MethodCall)
        assert stmt.expr.method == "method"
        assert len(stmt.expr.arguments) == 1

    def test_multiple_args(self):
        program = Parser(Lexer("fn add(a, b, c) { a + b + c }").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, FunctionDef)
        assert len(stmt.params) == 3


class TestParserControlFlow:
    def test_if_brace_block(self):
        source = "if true { x = 1 }\n"
        program = Parser(Lexer(source).tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, IfExpression)
        assert isinstance(stmt.then_block, Block)

    def test_if_indent_block(self):
        source = "if true:\n    x = 1\n"
        program = Parser(Lexer(source).tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, IfExpression)
        assert isinstance(stmt.then_block, Block)

    def test_if_else(self):
        source = "if true { x = 1 } else { x = 2 }\n"
        program = Parser(Lexer(source).tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, IfExpression)
        assert stmt.else_block is not None

    def test_for_loop(self):
        source = "for i in items { print(i) }\n"
        program = Parser(Lexer(source).tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, ForLoop)
        assert stmt.variable == "i"

    def test_while_loop(self):
        source = "while x > 0 { x = x - 1 }\n"
        program = Parser(Lexer(source).tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, WhileLoop)


class TestParserFunctions:
    def test_function_def(self):
        source = "fn add(a, b) { a + b }\n"
        program = Parser(Lexer(source).tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, FunctionDef)
        assert stmt.name == "add"
        assert stmt.params == ["a", "b"]

    def test_arrow_function(self):
        source = "double = x -> x * 2\n"
        program = Parser(Lexer(source).tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, ExprStatement)
        assert isinstance(stmt.expr, Assignment)
        assert isinstance(stmt.expr.value, ArrowFunction)
        assert stmt.expr.value.params == ["x"]

    def test_return_statement(self):
        source = "fn f() { return 42 }\n"
        program = Parser(Lexer(source).tokenize()).parse()
        fn_def = program.body[0]
        assert isinstance(fn_def, FunctionDef)
        assert isinstance(fn_def.body, Block)
        assert isinstance(fn_def.body.body[0], ReturnStatement)

    def test_break_statement(self):
        source = "while true { break }\n"
        program = Parser(Lexer(source).tokenize()).parse()
        while_loop = program.body[0]
        assert isinstance(while_loop, WhileLoop)
        assert isinstance(while_loop.body, Block)
        assert isinstance(while_loop.body.body[0], BreakStatement)

    def test_continue_statement(self):
        source = "for i in items { continue }\n"
        program = Parser(Lexer(source).tokenize()).parse()
        for_loop = program.body[0]
        assert isinstance(for_loop, ForLoop)
        assert isinstance(for_loop.body, Block)
        assert isinstance(for_loop.body.body[0], ContinueStatement)


class TestParserLists:
    def test_empty_list(self):
        program = Parser(Lexer("[]").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, ExprStatement)
        assert isinstance(stmt.expr, ListLiteral)
        assert len(stmt.expr.elements) == 0

    def test_list_with_elements(self):
        program = Parser(Lexer("[1, 2, 3]").tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt.expr, ListLiteral)
        assert len(stmt.expr.elements) == 3


class TestParserFStrings:
    def test_interpolated_string(self):
        program = Parser(Lexer('f"hello {name}"').tokenize()).parse()
        stmt = program.body[0]
        assert isinstance(stmt, ExprStatement)
        assert isinstance(stmt.expr, InterpolatedString)
        assert len(stmt.expr.parts) == 2


class TestParserPrecedence:
    def test_multiply_before_add(self):
        program = Parser(Lexer("1 + 2 * 3").tokenize()).parse()
        expr = program.body[0].expr
        assert isinstance(expr, BinaryOp)
        assert expr.op == "+"
        assert isinstance(expr.right, BinaryOp)
        assert expr.right.op == "*"

    def test_parentheses_override(self):
        program = Parser(Lexer("(1 + 2) * 3").tokenize()).parse()
        expr = program.body[0].expr
        assert isinstance(expr, BinaryOp)
        assert expr.op == "*"
        assert isinstance(expr.left, BinaryOp)
        assert expr.left.op == "+"

    def test_and_before_or(self):
        program = Parser(Lexer("a or b and c").tokenize()).parse()
        expr = program.body[0].expr
        assert isinstance(expr, BinaryOp)
        assert expr.op == "or"
        assert isinstance(expr.right, BinaryOp)
        assert expr.right.op == "and"


class TestParserErrors:
    def test_unexpected_token(self):
        with pytest.raises(ParseError, match="Expected '\\)'"):
            Parser(Lexer("(1 + 2").tokenize()).parse()


# =============================================================================
# ENVIRONMENT TESTS
# =============================================================================

class TestEnvironment:
    def test_define_and_get(self):
        env = Environment()
        env.define("x", 42)
        assert env.get("x") == 42

    def test_get_undefined(self):
        env = Environment()
        with pytest.raises(EnvironmentError, match="Undefined variable"):
            env.get("x")

    def test_set_existing(self):
        env = Environment()
        env.define("x", 10)
        env.set("x", 20)
        assert env.get("x") == 20

    def test_set_undefined_creates(self):
        env = Environment()
        env.set("x", 42)
        assert env.get("x") == 42

    def test_child_scope_inherits(self):
        parent = Environment()
        parent.define("x", 10)
        child = parent.child()
        assert child.get("x") == 10

    def test_child_scope_shadows(self):
        parent = Environment()
        parent.define("x", 10)
        child = parent.child()
        child.define("x", 20)
        assert child.get("x") == 20
        assert parent.get("x") == 10

    def test_child_set_modifies_parent(self):
        parent = Environment()
        parent.define("x", 10)
        child = parent.child()
        child.set("x", 20)
        assert parent.get("x") == 20

    def test_has_variable(self):
        env = Environment()
        env.define("x", 1)
        assert env.has("x") is True
        assert env.has("y") is False

    def test_has_checks_parent(self):
        parent = Environment()
        parent.define("x", 1)
        child = parent.child()
        assert child.has("x") is True


# =============================================================================
# INTERPRETER TESTS
# =============================================================================

class TestInterpreterArithmetic:
    def test_addition(self):
        assert run("print(1 + 2)") is None  # print returns None

    def test_subtraction(self):
        result = run("x = 10 - 3\nx")
        # Last expression is evaluated
        assert isinstance(result, (int, float))

    def test_multiplication(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = 4 * 5\n").tokenize()).parse())
        assert env.globals.get("x") == 20

    def test_division(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = 10 / 2\n").tokenize()).parse())
        assert env.globals.get("x") == 5.0

    def test_modulo(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = 10 % 3\n").tokenize()).parse())
        assert env.globals.get("x") == 1

    def test_division_by_zero(self):
        with pytest.raises(MgsRuntimeError, match="Division by zero"):
            run("1 / 0")

    def test_operator_precedence(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = 1 + 2 * 3\n").tokenize()).parse())
        assert env.globals.get("x") == 7

    def test_parentheses(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = (1 + 2) * 3\n").tokenize()).parse())
        assert env.globals.get("x") == 9

    def test_unary_negation(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = -5\n").tokenize()).parse())
        assert env.globals.get("x") == -5


class TestInterpreterStrings:
    def test_string_literal(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "hello"\n').tokenize()).parse())
        assert env.globals.get("x") == "hello"

    def test_string_concatenation(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "hello" + " " + "world"\n').tokenize()).parse())
        assert env.globals.get("x") == "hello world"

    def test_string_repetition(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "ab" * 3\n').tokenize()).parse())
        assert env.globals.get("x") == "ababab"

    def test_fstring_interpolation(self):
        env = Interpreter()
        env.run(Parser(Lexer('name = "world"\nx = f"hello {name}"\n').tokenize()).parse())
        assert env.globals.get("x") == "hello world"

    def test_fstring_expression(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = f"{1 + 2}"\n').tokenize()).parse())
        assert env.globals.get("x") == "3"


class TestInterpreterComparisons:
    def test_equal(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = 5 == 5\n").tokenize()).parse())
        assert env.globals.get("x") is True

    def test_not_equal(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = 5 != 3\n").tokenize()).parse())
        assert env.globals.get("x") is True

    def test_less_than(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = 3 < 5\n").tokenize()).parse())
        assert env.globals.get("x") is True

    def test_greater_than(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = 5 > 3\n").tokenize()).parse())
        assert env.globals.get("x") is True

    def test_less_equal(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = 5 <= 5\n").tokenize()).parse())
        assert env.globals.get("x") is True

    def test_greater_equal(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = 5 >= 5\n").tokenize()).parse())
        assert env.globals.get("x") is True


class TestInterpreterBooleans:
    def test_and_true(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = true and true\n").tokenize()).parse())
        assert env.globals.get("x") is True

    def test_and_false(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = true and false\n").tokenize()).parse())
        assert env.globals.get("x") is False

    def test_or_true(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = false or true\n").tokenize()).parse())
        assert env.globals.get("x") is True

    def test_or_false(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = false or false\n").tokenize()).parse())
        assert env.globals.get("x") is False

    def test_not_true(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = not true\n").tokenize()).parse())
        assert env.globals.get("x") is False

    def test_not_false(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = not false\n").tokenize()).parse())
        assert env.globals.get("x") is True


class TestInterpreterVariables:
    def test_define_and_read(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = 42\n").tokenize()).parse())
        assert env.globals.get("x") == 42

    def test_reassign(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = 1\nx = 2\n").tokenize()).parse())
        assert env.globals.get("x") == 2

    def test_plus_equals(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = 10\nx += 5\n").tokenize()).parse())
        assert env.globals.get("x") == 15

    def test_minus_equals(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = 10\nx -= 3\n").tokenize()).parse())
        assert env.globals.get("x") == 7

    def test_undefined_variable(self):
        with pytest.raises(MgsRuntimeError, match="Undefined variable"):
            run("x")


class TestInterpreterScope:
    def test_if_block_shares_scope(self):
        env = Interpreter()
        source = "x = 0\nif true {\n    x = 1\n}\n"
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("x") == 1

    def test_for_block_shares_scope(self):
        env = Interpreter()
        source = "x = 0\nfor i in [1, 2, 3] {\n    x = x + i\n}\n"
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("x") == 6

    def test_function_creates_scope(self):
        env = Interpreter()
        source = "fn f() { x = 42 }\nf()\n"
        env.run(Parser(Lexer(source).tokenize()).parse())
        # x is not in globals because it was defined in function scope
        assert not env.globals.has("x")


class TestInterpreterFunctions:
    def test_define_and_call(self):
        env = Interpreter()
        source = "fn double(x) { x * 2 }\nresult = double(21)\n"
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("result") == 42

    def test_return_value(self):
        env = Interpreter()
        source = "fn f() { return 42 }\nx = f()\n"
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("x") == 42

    def test_closure(self):
        env = Interpreter()
        source = "x = 10\nfn f() { return x }\nx = f()\n"
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("x") == 10

    def test_arrow_function(self):
        env = Interpreter()
        source = "double = x -> x * 2\nresult = double(5)\n"
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("result") == 10

    def test_higher_order_function(self):
        env = Interpreter()
        source = "fn apply(f, x) { f(x) }\ndouble = x -> x * 2\nresult = apply(double, 5)\n"
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("result") == 10

    def test_wrong_arg_count(self):
        with pytest.raises(MgsRuntimeError, match="takes 1 argument but 2 were given"):
            run("fn f(x) { x }\nf(1, 2)")

    def test_call_non_function(self):
        with pytest.raises(MgsRuntimeError, match="Cannot call non-function"):
            run("x = 42\nx()")

    def test_recursive_function(self):
        env = Interpreter()
        source = "fn fib(n) {\n    if n <= 1 { return n }\n    return fib(n - 1) + fib(n - 2)\n}\nresult = fib(10)\n"
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("result") == 55


class TestInterpreterControlFlow:
    def test_if_true(self):
        env = Interpreter()
        source = "x = 0\nif true { x = 1 }\n"
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("x") == 1

    def test_if_false(self):
        env = Interpreter()
        source = "x = 0\nif false { x = 1 }\n"
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("x") == 0

    def test_if_else(self):
        env = Interpreter()
        source = "x = 0\nif false { x = 1 } else { x = 2 }\n"
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("x") == 2

    def test_for_loop(self):
        env = Interpreter()
        source = "x = 0\nfor i in [1, 2, 3] { x = x + i }\n"
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("x") == 6

    def test_while_loop(self):
        env = Interpreter()
        source = "x = 0\nwhile x < 5 { x = x + 1 }\n"
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("x") == 5

    def test_break(self):
        env = Interpreter()
        source = "x = 0\nwhile true { x = x + 1\nif x == 3 { break } }\n"
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("x") == 3

    def test_continue(self):
        env = Interpreter()
        source = "x = 0\nfor i in [1, 2, 3, 4, 5] {\n    if i == 3 { continue }\n    x = x + 1\n}\n"
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("x") == 4

    def test_indent_block_if(self):
        env = Interpreter()
        source = "x = 0\nif true:\n    x = 1\n"
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("x") == 1


class TestInterpreterLists:
    def test_list_literal(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = [1, 2, 3]\n").tokenize()).parse())
        assert env.globals.get("x") == [1, 2, 3]

    def test_list_index(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = [10, 20, 30]\ny = x[1]\n").tokenize()).parse())
        assert env.globals.get("y") == 20

    def test_list_index_out_of_bounds(self):
        with pytest.raises(MgsRuntimeError, match="out of range"):
            run("x = [1, 2, 3]\nx[5]")

    def test_list_concatenation(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = [1, 2] + [3, 4]\n").tokenize()).parse())
        assert env.globals.get("x") == [1, 2, 3, 4]


class TestInterpreterBuiltins:
    def test_len_string(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = len("hello")\n').tokenize()).parse())
        assert env.globals.get("x") == 5

    def test_len_list(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = len([1, 2, 3])\n").tokenize()).parse())
        assert env.globals.get("x") == 3

    def test_type_int(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = type(42)\n').tokenize()).parse())
        assert env.globals.get("x") == "int"

    def test_type_string(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = type("hello")\n').tokenize()).parse())
        assert env.globals.get("x") == "string"

    def test_type_none(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = type(none)\n").tokenize()).parse())
        assert env.globals.get("x") == "none"

    def test_str_conversion(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = str(42)\n').tokenize()).parse())
        assert env.globals.get("x") == "42"

    def test_int_conversion(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = int("42")\n').tokenize()).parse())
        assert env.globals.get("x") == 42

    def test_float_conversion(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = float("3.14")\n').tokenize()).parse())
        assert env.globals.get("x") == 3.14

    def test_range(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = range(5)\n").tokenize()).parse())
        result = env.globals.get("x")
        assert list(result) == [0, 1, 2, 3, 4]

    def test_range_start_stop(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = range(2, 5)\n").tokenize()).parse())
        result = env.globals.get("x")
        assert list(result) == [2, 3, 4]

    def test_abs(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = abs(-5)\n").tokenize()).parse())
        assert env.globals.get("x") == 5

    def test_min(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = min(3, 1, 2)\n").tokenize()).parse())
        assert env.globals.get("x") == 1

    def test_max(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = max(3, 1, 2)\n").tokenize()).parse())
        assert env.globals.get("x") == 3

    def test_sum(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = sum([1, 2, 3])\n").tokenize()).parse())
        assert env.globals.get("x") == 6

    def test_keys(self):
        env = Interpreter()
        # Create a dict using a mock domain object or string keys
        source = 'x = keys({"a": 1, "b": 2})\n'
        # Dict literals aren't supported yet, so we'll skip this test
        pytest.skip("Dict literals not yet supported")

    def test_quarry_reads_file(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")
        env = Interpreter()
        env.run(Parser(Lexer(f'x = quarry("{test_file}")\n').tokenize()).parse())
        assert env.globals.get("x") == "hello world"

    def test_litho_writes_file(self, tmp_path):
        test_file = tmp_path / "output.txt"
        env = Interpreter()
        env.run(Parser(Lexer(f'litho("{test_file}", "hello world")\n').tokenize()).parse())
        assert test_file.read_text() == "hello world"

    def test_litho_creates_file(self, tmp_path):
        test_file = tmp_path / "new.txt"
        assert not test_file.exists()
        env = Interpreter()
        env.run(Parser(Lexer(f'litho("{test_file}", "created")\n').tokenize()).parse())
        assert test_file.exists()
        assert test_file.read_text() == "created"

    def test_litho_overwrites_file(self, tmp_path):
        test_file = tmp_path / "overwrite.txt"
        test_file.write_text("old content")
        env = Interpreter()
        env.run(Parser(Lexer(f'litho("{test_file}", "new content")\n').tokenize()).parse())
        assert test_file.read_text() == "new content"

    def test_quarry_not_found(self):
        env = Interpreter()
        with pytest.raises(FileNotFoundError):
            env.run(Parser(Lexer('quarry("/nonexistent/file.txt")\n').tokenize()).parse())

    def test_exec_basic(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = exec("echo hello")\n').tokenize()).parse())
        result = env.globals.get("x")
        assert result["stdout"] == "hello\n"
        assert result["exit_code"] == 0

    def test_exec_returns_stderr(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = exec("echo error >&2")\n').tokenize()).parse())
        result = env.globals.get("x")
        assert result["stderr"] == "error\n"

    def test_exec_nonzero_exit(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = exec("exit 1")\n').tokenize()).parse())
        result = env.globals.get("x")
        assert result["exit_code"] == 1

    def test_http_get(self):
        from unittest.mock import patch, MagicMock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"hello": "world"}'
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"hello": "world"}

        with patch("httpx.get", return_value=mock_response) as mock_get:
            env = Interpreter()
            env.run(Parser(Lexer('x = http.get("https://example.com")\n').tokenize()).parse())
            result = env.globals.get("x")
            assert result["status"] == 200
            assert result["json"] == {"hello": "world"}
            mock_get.assert_called_once()

    def test_http_post(self):
        from unittest.mock import patch, MagicMock
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.text = '{"created": true}'
        mock_response.headers = {}
        mock_response.json.return_value = {"created": True}

        with patch("httpx.post", return_value=mock_response) as mock_post:
            env = Interpreter()
            env.run(Parser(Lexer('x = http.post("https://example.com", body={"key": "value"})\n').tokenize()).parse())
            result = env.globals.get("x")
            assert result["status"] == 201
            assert result["json"] == {"created": True}
            mock_post.assert_called_once()

    def test_in_operator_list(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = 2 in [1, 2, 3]\n').tokenize()).parse())
        assert env.globals.get("x") is True

    def test_in_operator_list_not_found(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = 5 in [1, 2, 3]\n').tokenize()).parse())
        assert env.globals.get("x") is False

    def test_in_operator_string(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "ell" in "hello"\n').tokenize()).parse())
        assert env.globals.get("x") is True

    def test_in_operator_string_not_found(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "xyz" in "hello"\n').tokenize()).parse())
        assert env.globals.get("x") is False

    def test_in_operator_dict(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "name" in {"name": "Jake", "age": 30}\n').tokenize()).parse())
        assert env.globals.get("x") is True

    def test_in_operator_dict_not_found(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "email" in {"name": "Jake", "age": 30}\n').tokenize()).parse())
        assert env.globals.get("x") is False

    def test_string_match(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "123abc".match("\\d+")\n').tokenize()).parse())
        assert env.globals.get("x") == ["123"]

    def test_string_match_no_match(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "abc".match("\\d+")\n').tokenize()).parse())
        assert env.globals.get("x") is None

    def test_string_findall(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "abc123def456".findall("\\d+")\n').tokenize()).parse())
        assert env.globals.get("x") == ["123", "456"]

    def test_string_findall_letters(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "hello world".findall("[a-z]+")\n').tokenize()).parse())
        assert env.globals.get("x") == ["hello", "world"]

    def test_string_findall_empty(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "abc".findall("\\d+")\n').tokenize()).parse())
        assert env.globals.get("x") == []


class TestInterpreterErrors:
    def test_syntax_error_line_number(self):
        with pytest.raises(MgsRuntimeError) as exc_info:
            run("x = 1 / 0")
        assert exc_info.value.line == 1

    def test_runtime_error_line_number(self):
        with pytest.raises(MgsRuntimeError) as exc_info:
            run("x = 1 / 0")
        assert exc_info.value.line > 0

    def test_error_has_source_line(self):
        with pytest.raises(MgsRuntimeError) as exc_info:
            source = "x = 1 / 0"
            tokens = Lexer(source).tokenize()
            program = Parser(tokens, source=source).parse()
            interp = Interpreter(source=source)
            interp.run(program)
        assert exc_info.value.source_line == "x = 1 / 0"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegrationHello:
    def test_hello_world(self):
        source = 'print("Hello, MagmaScript!")\n'
        # Should not raise
        run(source)

    def test_hello_variables(self):
        source = 'name = "World"\nprint(f"Hello, {name}!")\n'
        run(source)

    def test_hello_functions(self):
        source = "double = fn(x) { x * 2 }\nresult = double(21)\n"
        env = Interpreter()
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("result") == 42

    def test_hello_arrows(self):
        source = "triple = x -> x * 3\nresult = triple(7)\n"
        env = Interpreter()
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("result") == 21


class TestIntegrationFibonacci:
    def test_fibonacci(self):
        source = """fn fib(n) {
    if n <= 1 { return n }
    return fib(n - 1) + fib(n - 2)
}
result = fib(10)
"""
        env = Interpreter()
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("result") == 55

    def test_factorial(self):
        source = """fn factorial(n) {
    result = 1
    i = 2
    while i <= n {
        result = result * i
        i = i + 1
    }
    return result
}
result = factorial(10)
"""
        env = Interpreter()
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("result") == 3628800


class TestIntegrationComplex:
    def test_nested_control_flow(self):
        source = """x = 0
for i in range(10) {
    if i % 2 == 0 {
        x = x + i
    }
}
"""
        env = Interpreter()
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("x") == 20  # 0 + 2 + 4 + 6 + 8

    def test_function_composition(self):
        source = """fn compose(f, g) {
    return x -> f(g(x))
}
double = x -> x * 2
add_one = x -> x + 1
double_after_add = compose(double, add_one)
result = double_after_add(5)
"""
        env = Interpreter()
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("result") == 12  # (5 + 1) * 2

    def test_list_operations(self):
        source = """numbers = [1, 2, 3, 4, 5]
doubled = []
for n in numbers {
    doubled = doubled + [n * 2]
}
"""
        env = Interpreter()
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("doubled") == [2, 4, 6, 8, 10]

    def test_string_interpolation_complex(self):
        source = 'name = "Magma"\nversion = 2\nresult = f"{name}Script v{version}"\n'
        env = Interpreter()
        env.run(Parser(Lexer(source).tokenize()).parse())
        assert env.globals.get("result") == "MagmaScript v2"


# =============================================================================
# ERROR FORMATTING TESTS
# =============================================================================

class TestLexerErrorFormatting:
    def test_unterminated_string_error(self):
        with pytest.raises(LexerError) as exc_info:
            Lexer('"hello').tokenize()
        assert "Unterminated string" in str(exc_info.value.message)

    def test_indentation_error(self):
        with pytest.raises(LexerError) as exc_info:
            Lexer("if true:\n    x = 1\n  y = 2\n").tokenize()
        assert "Indentation error" in str(exc_info.value.message)

    def test_unexpected_bang_error(self):
        with pytest.raises(LexerError) as exc_info:
            Lexer("!").tokenize()
        assert "did you mean '!='?" in str(exc_info.value.message)

    def test_error_has_source_line(self):
        with pytest.raises(LexerError) as exc_info:
            Lexer('"hello').tokenize()
        assert exc_info.value.source_line == '"hello'

    def test_error_has_filename(self):
        with pytest.raises(LexerError) as exc_info:
            Lexer('"hello', filename="test.mgs").tokenize()
        assert exc_info.value.filename == "test.mgs"

    def test_error_format(self):
        with pytest.raises(LexerError) as exc_info:
            Lexer('"hello', filename="test.mgs").tokenize()
        formatted = exc_info.value.format()
        assert "test.mgs" in formatted
        assert "line 1" in formatted
        assert "Unterminated string" in formatted


class TestParseErrorFormatting:
    def test_error_has_source_line(self):
        with pytest.raises(ParseError) as exc_info:
            tokens = Lexer("(1 + 2").tokenize()
            Parser(tokens, source="(1 + 2").parse()
        assert exc_info.value.source_line == "(1 + 2"

    def test_error_has_filename(self):
        with pytest.raises(ParseError) as exc_info:
            tokens = Lexer("(1 + 2").tokenize()
            Parser(tokens, source="(1 + 2", filename="test.mgs").parse()
        assert exc_info.value.filename == "test.mgs"

    def test_error_format(self):
        with pytest.raises(ParseError) as exc_info:
            tokens = Lexer("(1 + 2").tokenize()
            Parser(tokens, source="(1 + 2", filename="test.mgs").parse()
        formatted = exc_info.value.format()
        assert "test.mgs" in formatted
        assert "line 1" in formatted
        assert "')'" in formatted

    def test_error_includes_token_value(self):
        with pytest.raises(ParseError) as exc_info:
            tokens = Lexer("(1 + 2 }").tokenize()
            Parser(tokens).parse()
        assert "')'" in str(exc_info.value.message)


class TestRuntimeErrorFormatting:
    def test_error_has_line_and_column(self):
        with pytest.raises(MgsRuntimeError) as exc_info:
            run("x = 1 / 0")
        assert exc_info.value.line == 1
        assert exc_info.value.column == 7

    def test_error_has_source_line(self):
        with pytest.raises(MgsRuntimeError) as exc_info:
            run("x = 1 / 0")
        assert exc_info.value.source_line == "x = 1 / 0"

    def test_error_has_filename(self):
        with pytest.raises(MgsRuntimeError) as exc_info:
            source = "x = 1 / 0"
            tokens = Lexer(source, filename="test.mgs").tokenize()
            program = Parser(tokens, source=source, filename="test.mgs").parse()
            interp = Interpreter(source=source, filename="test.mgs")
            interp.run(program)
        assert exc_info.value.filename == "test.mgs"

    def test_error_format(self):
        with pytest.raises(MgsRuntimeError) as exc_info:
            source = "x = 1 / 0"
            tokens = Lexer(source, filename="test.mgs").tokenize()
            program = Parser(tokens, source=source, filename="test.mgs").parse()
            interp = Interpreter(source=source, filename="test.mgs")
            interp.run(program)
        formatted = exc_info.value.format()
        assert "test.mgs" in formatted
        assert "line 1" in formatted
        assert "Division by zero" in formatted

    def test_undefined_variable_suggestion(self):
        with pytest.raises(MgsRuntimeError) as exc_info:
            run("greeting = 1\ngreting")
        assert "did you mean" in exc_info.value.message.lower()

    def test_function_name_in_error(self):
        with pytest.raises(MgsRuntimeError) as exc_info:
            run("fn fib(n) { n }\nfib()")
        assert "fib()" in exc_info.value.message

    def test_call_stack(self):
        with pytest.raises(MgsRuntimeError) as exc_info:
            run("fn inner() { 1 / 0 }\nfn outer() { inner() }\nouter()")
        assert len(exc_info.value.call_stack) > 0

    def test_index_out_of_bounds_with_length(self):
        with pytest.raises(MgsRuntimeError) as exc_info:
            run("x = [1, 2, 3]\nx[10]")
        assert "has 3 element" in exc_info.value.message

    def test_cannot_call_non_function(self):
        with pytest.raises(MgsRuntimeError) as exc_info:
            run("x = 42\nx()")
        assert "Cannot call non-function" in exc_info.value.message

    def test_cannot_iterate(self):
        with pytest.raises(MgsRuntimeError) as exc_info:
            run("for i in 42 { print(i) }")
        assert "Cannot iterate" in exc_info.value.message


# =============================================================================
# DICT LITERAL TESTS
# =============================================================================

class TestDictLiterals:
    def test_empty_dict(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = {}").tokenize()).parse())
        assert env.globals.get("x") == {}

    def test_single_entry(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = {"a": 1}').tokenize()).parse())
        assert env.globals.get("x") == {"a": 1}

    def test_multiple_entries(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = {"a": 1, "b": 2, "c": 3}').tokenize()).parse())
        assert env.globals.get("x") == {"a": 1, "b": 2, "c": 3}

    def test_string_keys(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = {"name": "Jake", "age": 30}').tokenize()).parse())
        assert env.globals.get("x") == {"name": "Jake", "age": 30}

    def test_integer_keys(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = {1: \"one\", 2: \"two\"}").tokenize()).parse())
        assert env.globals.get("x") == {1: "one", 2: "two"}

    def test_nested_dicts(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = {"inner": {"a": 1}}').tokenize()).parse())
        assert env.globals.get("x") == {"inner": {"a": 1}}

    def test_dict_access(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = {"a": 1}\ny = x["a"]').tokenize()).parse())
        assert env.globals.get("y") == 1

    def test_dict_with_expressions(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = 5\ny = {"val": x * 2}').tokenize()).parse())
        assert env.globals.get("y") == {"val": 10}

    def test_keys_method(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = {"a": 1, "b": 2}\ny = keys(x)').tokenize()).parse())
        result = env.globals.get("y")
        assert "a" in result
        assert "b" in result

    def test_values_method(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = {"a": 1, "b": 2}\ny = values(x)').tokenize()).parse())
        result = env.globals.get("y")
        assert 1 in result
        assert 2 in result

    def test_dict_in_for_loop(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = {"a": 1, "b": 2}\ny = 0\nfor k in keys(x) { y = y + x[k] }').tokenize()).parse())
        assert env.globals.get("y") == 3


# =============================================================================
# LIST COMPREHENSION TESTS
# =============================================================================

class TestListComprehensions:
    def test_simple_comprehension(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = [1, 2, 3]\ny = [x * 2 for x in x]").tokenize()).parse())
        assert env.globals.get("y") == [2, 4, 6]

    def test_comprehension_with_condition(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = [1, 2, 3, 4, 5]\ny = [x for x in x if x % 2 == 0]").tokenize()).parse())
        assert env.globals.get("y") == [2, 4]

    def test_comprehension_with_range(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = [i * i for i in range(5)]").tokenize()).parse())
        assert env.globals.get("x") == [0, 1, 4, 9, 16]

    def test_comprehension_string_transform(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = ["hello", "world"]\ny = [x.upper() for x in x]').tokenize()).parse())
        assert env.globals.get("y") == ["HELLO", "WORLD"]

    def test_comprehension_nested_loop(self):
        # Note: Nested loops in comprehensions need multiple 'for' clauses
        # For now, we support single 'for' with optional 'if'
        # This test uses a workaround with flatten
        env = Interpreter()
        env.run(Parser(Lexer("x = [[1, 2], [3, 4]]\ny = []\nfor sub in x { for i in sub { y = y + [i] } }").tokenize()).parse())
        assert env.globals.get("y") == [1, 2, 3, 4]

    def test_comprehension_filter_and_transform(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = [1, 2, 3, 4, 5]\ny = [x * x for x in x if x > 3]").tokenize()).parse())
        assert env.globals.get("y") == [16, 25]

    def test_comprehension_empty_result(self):
        env = Interpreter()
        env.run(Parser(Lexer("x = [1, 2, 3]\ny = [x for x in x if x > 10]").tokenize()).parse())
        assert env.globals.get("y") == []


# =============================================================================
# STRING METHOD TESTS
# =============================================================================

class TestStringMethods:
    def test_split_with_separator(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "a,b,c".split(",")').tokenize()).parse())
        assert env.globals.get("x") == ["a", "b", "c"]

    def test_split_without_separator(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "hello world".split()').tokenize()).parse())
        assert env.globals.get("x") == ["hello", "world"]

    def test_join(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "-".join(["a", "b", "c"])').tokenize()).parse())
        assert env.globals.get("x") == "a-b-c"

    def test_upper(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "hello".upper()').tokenize()).parse())
        assert env.globals.get("x") == "HELLO"

    def test_lower(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "HELLO".lower()').tokenize()).parse())
        assert env.globals.get("x") == "hello"

    def test_contains_true(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "hello world".contains("world")').tokenize()).parse())
        assert env.globals.get("x") is True

    def test_contains_false(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "hello world".contains("xyz")').tokenize()).parse())
        assert env.globals.get("x") is False

    def test_replace(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "hello world".replace("world", "there")').tokenize()).parse())
        assert env.globals.get("x") == "hello there"

    def test_length(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "hello".length()').tokenize()).parse())
        assert env.globals.get("x") == 5

    def test_startswith_true(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "hello".startswith("hel")').tokenize()).parse())
        assert env.globals.get("x") is True

    def test_startswith_false(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "hello".startswith("xyz")').tokenize()).parse())
        assert env.globals.get("x") is False

    def test_endswith_true(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "hello".endswith("llo")').tokenize()).parse())
        assert env.globals.get("x") is True

    def test_endswith_false(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "hello".endswith("xyz")').tokenize()).parse())
        assert env.globals.get("x") is False

    def test_strip(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "  hello  ".strip()').tokenize()).parse())
        assert env.globals.get("x") == "hello"

    def test_string_method_chain(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "  Hello World  ".strip().lower()').tokenize()).parse())
        assert env.globals.get("x") == "hello world"

    def test_split_then_join(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = "-".join("a,b,c".split(","))').tokenize()).parse())
        assert env.globals.get("x") == "a-b-c"

    def test_comprehension_with_string_methods(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = ["hello", "world"]\ny = [w.upper() for w in x]').tokenize()).parse())
        assert env.globals.get("y") == ["HELLO", "WORLD"]

    def test_dict_with_string_methods(self):
        env = Interpreter()
        env.run(Parser(Lexer('x = {"name": "  Jake  "}\ny = x["name"].strip()').tokenize()).parse())
        assert env.globals.get("y") == "Jake"

    def test_csv_parsing_example(self):
        env = Interpreter()
        env.run(Parser(Lexer('csv = "apple,banana,cherry"\nfruits = csv.split(",")\nupper = [f.upper() for f in fruits]\nresult = " | ".join(upper)').tokenize()).parse())
        assert env.globals.get("result") == "APPLE | BANANA | CHERRY"
