"""Tests for the import system (intent keyword)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from magmascript.lang.lexer import Lexer
from magmascript.lang.parser import Parser, ParseError
from magmascript.lang.interpreter import Interpreter, RuntimeError
from magmascript.lang.ast_nodes import ImportStatement


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestImportParsing:
    """Tests for parsing import statements."""

    def test_simple_import(self):
        source = 'intent "greeter.mgs"'
        tokens = Lexer(source).tokenize()
        program = Parser(tokens, source=source).parse()
        
        assert len(program.body) == 1
        node = program.body[0]
        assert isinstance(node, ImportStatement)
        assert node.module == "greeter.mgs"
        assert node.names == []
        assert node.alias == ""
        assert node.from_import is False

    def test_import_with_alias(self):
        source = 'intent "greeter.mgs" as g'
        tokens = Lexer(source).tokenize()
        program = Parser(tokens, source=source).parse()
        
        assert len(program.body) == 1
        node = program.body[0]
        assert isinstance(node, ImportStatement)
        assert node.module == "greeter.mgs"
        assert node.alias == "g"
        assert node.from_import is False

    def test_from_import_single_name(self):
        source = 'intent { greet } from "greeter.mgs"'
        tokens = Lexer(source).tokenize()
        program = Parser(tokens, source=source).parse()
        
        assert len(program.body) == 1
        node = program.body[0]
        assert isinstance(node, ImportStatement)
        assert node.module == "greeter.mgs"
        assert node.names == ["greet"]
        assert node.from_import is True

    def test_from_import_multiple_names(self):
        source = 'intent { greet, farewell } from "greeter.mgs"'
        tokens = Lexer(source).tokenize()
        program = Parser(tokens, source=source).parse()
        
        assert len(program.body) == 1
        node = program.body[0]
        assert isinstance(node, ImportStatement)
        assert node.module == "greeter.mgs"
        assert node.names == ["greet", "farewell"]
        assert node.from_import is True

    def test_from_import_with_alias(self):
        source = 'intent { greet, farewell } from "greeter.mgs" as g'
        tokens = Lexer(source).tokenize()
        program = Parser(tokens, source=source).parse()
        
        assert len(program.body) == 1
        node = program.body[0]
        assert isinstance(node, ImportStatement)
        assert node.module == "greeter.mgs"
        assert node.names == ["greet", "farewell"]
        assert node.alias == "g"
        assert node.from_import is True


class TestImportExecution:
    """Tests for executing import statements."""

    def test_simple_import(self):
        source = f'intent "{FIXTURES_DIR}/greeter.mgs"\nresult = greeter.greet("World")'
        filename = str(FIXTURES_DIR / "test_script.mgs")
        result = Interpreter(source=source, filename=filename).run(Parser(Lexer(source, filename=filename).tokenize(), source=source, filename=filename).parse())
        assert result == "Hello, World!"

    def test_import_with_alias(self):
        source = f'intent "{FIXTURES_DIR}/greeter.mgs" as g\nresult = g.greet("World")'
        filename = str(FIXTURES_DIR / "test_script.mgs")
        result = Interpreter(source=source, filename=filename).run(Parser(Lexer(source, filename=filename).tokenize(), source=source, filename=filename).parse())
        assert result == "Hello, World!"

    def test_from_import_single_name(self):
        source = f'intent {{ greet }} from "{FIXTURES_DIR}/greeter.mgs"\nresult = greet("World")'
        filename = str(FIXTURES_DIR / "test_script.mgs")
        result = Interpreter(source=source, filename=filename).run(Parser(Lexer(source, filename=filename).tokenize(), source=source, filename=filename).parse())
        assert result == "Hello, World!"

    def test_from_import_multiple_names(self):
        source = f'intent {{ greet, farewell }} from "{FIXTURES_DIR}/greeter.mgs"\nresult = farewell("World")'
        filename = str(FIXTURES_DIR / "test_script.mgs")
        result = Interpreter(source=source, filename=filename).run(Parser(Lexer(source, filename=filename).tokenize(), source=source, filename=filename).parse())
        assert result == "Goodbye, World!"

    def test_from_import_with_alias(self):
        source = f'intent {{ greet, farewell }} from "{FIXTURES_DIR}/greeter.mgs" as g\nresult = g.greet("World")'
        filename = str(FIXTURES_DIR / "test_script.mgs")
        result = Interpreter(source=source, filename=filename).run(Parser(Lexer(source, filename=filename).tokenize(), source=source, filename=filename).parse())
        assert result == "Hello, World!"

    def test_import_constant(self):
        source = f'intent "{FIXTURES_DIR}/greeter.mgs"\nresult = greeter.PI'
        filename = str(FIXTURES_DIR / "test_script.mgs")
        result = Interpreter(source=source, filename=filename).run(Parser(Lexer(source, filename=filename).tokenize(), source=source, filename=filename).parse())
        assert result == pytest.approx(3.14159)

    def test_import_module_not_found(self):
        source = 'intent "nonexistent.mgs"'
        with pytest.raises(RuntimeError, match="Module not found"):
            Interpreter(source=source).run(Parser(Lexer(source).tokenize(), source=source).parse())

    def test_from_import_name_not_found(self):
        source = f'intent {{ nonexistent }} from "{FIXTURES_DIR}/greeter.mgs"'
        filename = str(FIXTURES_DIR / "test_script.mgs")
        with pytest.raises(RuntimeError, match="Name 'nonexistent' not found"):
            Interpreter(source=source, filename=filename).run(Parser(Lexer(source, filename=filename).tokenize(), source=source, filename=filename).parse())


class TestImportCircular:
    """Tests for circular import detection."""

    def test_circular_import_detected(self):
        # Create temporary files with circular imports
        with tempfile.TemporaryDirectory() as tmpdir:
            file_a = Path(tmpdir) / "a.mgs"
            file_b = Path(tmpdir) / "b.mgs"
            
            file_a.write_text(f'intent "{tmpdir}/b.mgs"\nx = 1')
            file_b.write_text(f'intent "{tmpdir}/a.mgs"\ny = 2')
            
            source = f'intent "{tmpdir}/a.mgs"'
            filename = str(Path(tmpdir) / "main.mgs")
            with pytest.raises(RuntimeError, match="Circular import"):
                Interpreter(source=source, filename=filename).run(Parser(Lexer(source, filename=filename).tokenize(), source=source, filename=filename).parse())


class TestImportModuleCache:
    """Tests for module caching behavior."""

    def test_module_cached(self):
        # Import the same module twice - should only execute once
        source = f'''
intent "{FIXTURES_DIR}/greeter.mgs"
intent "{FIXTURES_DIR}/greeter.mgs" as g
result = greeter.greet("World")
'''
        filename = str(FIXTURES_DIR / "test_script.mgs")
        result = Interpreter(source=source, filename=filename).run(Parser(Lexer(source, filename=filename).tokenize(), source=source, filename=filename).parse())
        assert result == "Hello, World!"


class TestImportKeywordToken:
    """Tests that 'intent' is recognized as a keyword."""

    def test_intent_is_keyword(self):
        from magmascript.lang.lexer import Lexer, TokenType
        tokens = Lexer("intent").tokenize()
        assert tokens[0].type == TokenType.INTENT

    def test_from_is_keyword(self):
        from magmascript.lang.lexer import Lexer, TokenType
        tokens = Lexer("from").tokenize()
        assert tokens[0].type == TokenType.FROM

    def test_as_is_keyword(self):
        from magmascript.lang.lexer import Lexer, TokenType
        tokens = Lexer("as").tokenize()
        assert tokens[0].type == TokenType.AS
