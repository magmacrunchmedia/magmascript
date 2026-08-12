"""Tests for class definitions and instances."""

from __future__ import annotations

import pytest

from magmascript.lang.lexer import Lexer
from magmascript.lang.parser import Parser
from magmascript.lang.interpreter import Interpreter, RuntimeError
from magmascript.lang.ast_nodes import ClassDef, PropertyAssignment


def run(source: str) -> any:
    tokens = Lexer(source).tokenize()
    program = Parser(tokens, source=source).parse()
    return Interpreter(source=source).run(program)


class TestClassParsing:
    """Tests for parsing class definitions."""

    def test_basic_class(self):
        source = '''
class Dog {
    fn init(self, name) {
        self.name = name
    }
}
'''
        tokens = Lexer(source).tokenize()
        program = Parser(tokens, source=source).parse()
        assert len(program.body) == 1
        node = program.body[0]
        assert isinstance(node, ClassDef)
        assert node.name == "Dog"
        assert len(node.methods) == 1

    def test_class_with_multiple_methods(self):
        source = '''
class Dog {
    fn init(self, name) {
        self.name = name
    }

    fn bark(self) {
        return self.name + " says woof!"
    }
}
'''
        tokens = Lexer(source).tokenize()
        program = Parser(tokens, source=source).parse()
        node = program.body[0]
        assert isinstance(node, ClassDef)
        assert len(node.methods) == 2

    def test_property_assignment(self):
        source = '''
class Dog {
    fn init(self, name) {
        self.name = name
    }
}
'''
        tokens = Lexer(source).tokenize()
        program = Parser(tokens, source=source).parse()
        init_method = program.body[0].methods[0]
        assert isinstance(init_method.body.body[0].expr, PropertyAssignment)


class TestClassExecution:
    """Tests for executing class definitions."""

    def test_basic_class(self):
        source = '''
class Dog {
    fn init(self, name) {
        self.name = name
    }
}

rex = Dog("Rex")
'''
        interpreter = Interpreter(source=source)
        program = Parser(Lexer(source).tokenize(), source=source).parse()
        interpreter.run(program)
        assert interpreter.globals.get("rex") is not None

    def test_instance_attribute(self):
        source = '''
class Dog {
    fn init(self, name) {
        self.name = name
    }
}

rex = Dog("Rex")
result = rex.name
'''
        interpreter = Interpreter(source=source)
        program = Parser(Lexer(source).tokenize(), source=source).parse()
        interpreter.run(program)
        assert interpreter.globals.get("result") == "Rex"

    def test_method_call(self):
        source = '''
class Dog {
    fn init(self, name) {
        self.name = name
    }

    fn bark(self) {
        return self.name + " says woof!"
    }
}

rex = Dog("Rex")
result = rex.bark()
'''
        interpreter = Interpreter(source=source)
        program = Parser(Lexer(source).tokenize(), source=source).parse()
        interpreter.run(program)
        assert interpreter.globals.get("result") == "Rex says woof!"

    def test_multiple_instances(self):
        source = '''
class Counter {
    fn init(self, start) {
        self.count = start
    }

    fn increment(self) {
        self.count = self.count + 1
    }
}

a = Counter(0)
b = Counter(10)
a.increment()
a.increment()
b.increment()
'''
        interpreter = Interpreter(source=source)
        program = Parser(Lexer(source).tokenize(), source=source).parse()
        interpreter.run(program)
        a = interpreter.globals.get("a")
        b = interpreter.globals.get("b")
        assert a.attributes["count"] == 2
        assert b.attributes["count"] == 11

    def test_no_init(self):
        source = '''
class Empty {
    fn greet(self) {
        return "hello"
    }
}

e = Empty()
result = e.greet()
'''
        interpreter = Interpreter(source=source)
        program = Parser(Lexer(source).tokenize(), source=source).parse()
        interpreter.run(program)
        assert interpreter.globals.get("result") == "hello"

    def test_type_returns_class_name(self):
        source = '''
class Dog {
    fn init(self, name) {
        self.name = name
    }
}

result = type(Dog("Rex"))
'''
        interpreter = Interpreter(source=source)
        program = Parser(Lexer(source).tokenize(), source=source).parse()
        interpreter.run(program)
        assert interpreter.globals.get("result") == "Dog"

    def test_property_access_error(self):
        source = '''
class Dog {
    fn init(self, name) {
        self.name = name
    }
}

rex = Dog("Rex")
rex.nonexistent
'''
        with pytest.raises(RuntimeError, match="has no attribute"):
            run(source)

    def test_method_not_found_error(self):
        source = '''
class Dog {
    fn init(self, name) {
        self.name = name
    }
}

rex = Dog("Rex")
rex.nonexistent()
'''
        with pytest.raises(RuntimeError, match="has no method"):
            run(source)


class TestClassKeywords:
    """Tests that class and self are recognized as keywords."""

    def test_class_is_keyword(self):
        from magmascript.lang.lexer import Lexer, TokenType
        tokens = Lexer("class").tokenize()
        assert tokens[0].type == TokenType.CLASS

    def test_self_is_keyword(self):
        from magmascript.lang.lexer import Lexer, TokenType
        tokens = Lexer("self").tokenize()
        assert tokens[0].type == TokenType.SELF
