"""Tests for try/haunter and throw (error handling)."""

from __future__ import annotations

import pytest

from magmascript.lang.lexer import Lexer
from magmascript.lang.parser import Parser
from magmascript.lang.interpreter import Interpreter, RuntimeError
from magmascript.lang.ast_nodes import TryCatch, ThrowStatement


def run(source: str) -> any:
    tokens = Lexer(source).tokenize()
    program = Parser(tokens, source=source).parse()
    return Interpreter(source=source).run(program)


class TestTryCatchParsing:
    """Tests for parsing try/haunter blocks."""

    def test_basic_try_catch(self):
        source = 'try {\n  x = 1\n} haunter (e) {\n  print(e)\n}'
        tokens = Lexer(source).tokenize()
        program = Parser(tokens, source=source).parse()
        
        assert len(program.body) == 1
        node = program.body[0]
        assert isinstance(node, TryCatch)
        assert node.catch_param == "e"

    def test_try_with_function_call(self):
        source = '''
fn risky() {
    throw fire toad("something went wrong")
}

try {
    result = risky()
} haunter (e) {
    print(e.message)
}
'''
        tokens = Lexer(source).tokenize()
        program = Parser(tokens, source=source).parse()
        assert len(program.body) == 2


class TestTryCatchExecution:
    """Tests for executing try/haunter blocks."""

    def test_try_no_error(self):
        source = '''
x = 0
try {
    x = 42
} haunter (e) {
    x = -1
}
'''
        result = run(source)
        # After execution, x should be 42 (no error occurred)
        interpreter = Interpreter(source=source)
        program = Parser(Lexer(source).tokenize(), source=source).parse()
        interpreter.run(program)
        assert interpreter.globals.get("x") == 42

    def test_try_catches_error(self):
        source = '''
x = 0
try {
    x = 1 / 0
} haunter (e) {
    x = -1
}
'''
        interpreter = Interpreter(source=source)
        program = Parser(Lexer(source).tokenize(), source=source).parse()
        interpreter.run(program)
        assert interpreter.globals.get("x") == -1

    def test_catch_receives_error_message(self):
        source = '''
msg = ""
try {
    throw fire toad("test error")
} haunter (e) {
    msg = e.message
}
'''
        interpreter = Interpreter(source=source)
        program = Parser(Lexer(source).tokenize(), source=source).parse()
        interpreter.run(program)
        assert interpreter.globals.get("msg") == "test error"

    def test_catch_receives_error_details(self):
        source = '''
prefix = ""
try {
    throw fire toad("test")
} haunter (e) {
    prefix = e.prefix
}
'''
        interpreter = Interpreter(source=source)
        program = Parser(Lexer(source).tokenize(), source=source).parse()
        interpreter.run(program)
        assert interpreter.globals.get("prefix") == "fire toad"

    def test_try_with_function(self):
        source = '''
fn risky() {
    throw fire toad("function error")
}

msg = ""
try {
    risky()
} haunter (e) {
    msg = e.message
}
'''
        interpreter = Interpreter(source=source)
        program = Parser(Lexer(source).tokenize(), source=source).parse()
        interpreter.run(program)
        assert interpreter.globals.get("msg") == "function error"

    def test_nested_try_catch(self):
        source = '''
result = ""
try {
    try {
        throw fire toad("inner error")
    } haunter (e) {
        result = "caught inner"
    }
} haunter (e) {
    result = "caught outer"
}
'''
        interpreter = Interpreter(source=source)
        program = Parser(Lexer(source).tokenize(), source=source).parse()
        interpreter.run(program)
        assert interpreter.globals.get("result") == "caught inner"

    def test_catch_execution_continues(self):
        source = '''
x = 0
try {
    throw fire toad("error")
} haunter (e) {
    x = 1
}
y = x + 1
'''
        interpreter = Interpreter(source=source)
        program = Parser(Lexer(source).tokenize(), source=source).parse()
        interpreter.run(program)
        assert interpreter.globals.get("y") == 2


class TestThrowParsing:
    """Tests for parsing throw statements."""

    def test_throw_fire_toad(self):
        source = 'throw fire toad("error message")'
        tokens = Lexer(source).tokenize()
        program = Parser(tokens, source=source).parse()
        
        assert len(program.body) == 1
        node = program.body[0]
        assert isinstance(node, ThrowStatement)
        assert node.error_type == "fire toad"


class TestThrowExecution:
    """Tests for executing throw statements."""

    def test_throw_basic(self):
        source = 'throw fire toad("test error")'
        with pytest.raises(RuntimeError, match="test error"):
            run(source)

    def test_throw_in_function(self):
        source = '''
fn divide(a, b) {
    if b == 0 {
        throw fire toad("Cannot divide by zero")
    }
    return a / b
}

result = ""
try {
    divide(10, 0)
} haunter (e) {
    result = e.message
}
'''
        interpreter = Interpreter(source=source)
        program = Parser(Lexer(source).tokenize(), source=source).parse()
        interpreter.run(program)
        assert interpreter.globals.get("result") == "Cannot divide by zero"


class TestTryCatchKeywords:
    """Tests that try, haunter, throw are recognized as keywords."""

    def test_try_is_keyword(self):
        from magmascript.lang.lexer import Lexer, TokenType
        tokens = Lexer("try").tokenize()
        assert tokens[0].type == TokenType.TRY

    def test_haunter_is_keyword(self):
        from magmascript.lang.lexer import Lexer, TokenType
        tokens = Lexer("haunter").tokenize()
        assert tokens[0].type == TokenType.HAUNTER

    def test_throw_is_keyword(self):
        from magmascript.lang.lexer import Lexer, TokenType
        tokens = Lexer("throw").tokenize()
        assert tokens[0].type == TokenType.THROW
