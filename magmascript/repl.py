from __future__ import annotations

import sys
import readline

from magmascript.lang.lexer import Lexer, LexerError
from magmascript.lang.parser import Parser, ParseError
from magmascript.lang.interpreter import Interpreter, RuntimeError as MgsRuntimeError
from magmascript.lang.ast_nodes import ExprStatement
from magmascript import __version__


# ANSI color codes
_RED = "\033[31m"
_DIM = "\033[2m"
_RESET = "\033[0m"
_BOLD = "\033[1m"


def repl() -> None:
    interpreter = Interpreter()
    buffer: list[str] = []

    print(f"MagmaScript v{__version__}")
    print("Type .exit to quit, .help for help\n")

    while True:
        try:
            if buffer:
                prompt = f"{_DIM}... {_RESET}"
            else:
                prompt = f"{_BOLD}mgs>{_RESET} "

            line = input(prompt)

            if line.strip() == ".exit":
                break

            if line.strip() == ".help":
                print("Commands:")
                print("  .exit    - Quit the REPL")
                print("  .help    - Show this help")
                print("  .clear   - Clear variables")
                print("  .ast     - Show AST for next input")
                print()
                print("Language:")
                print("  Variables:  x = 42")
                print("  Functions:  add = fn(a, b) { a + b }")
                print("  Arrow:      double = x -> x * 2")
                print("  If:         if x > 10 { print(x) }")
                print("  For:        for i in range(5) { print(i) }")
                print("  Domains:    mcp.search('query')")
                continue

            if line.strip() == ".clear":
                interpreter = Interpreter()
                print("Variables cleared.")
                continue

            if line.strip() == ".ast":
                print("Paste expression, then press Enter:")
                line = input("... ")
                try:
                    source = line + "\n"
                    tokens = Lexer(source).tokenize()
                    program = Parser(tokens).parse()
                    _print_ast(program, indent=0)
                except (LexerError, ParseError) as e:
                    _print_error(e)
                continue

            buffer.append(line)
            source = "\n".join(buffer) + "\n"

            try:
                tokens = Lexer(source).tokenize()
                program = Parser(tokens).parse()
            except (LexerError, ParseError) as e:
                if ";" in line or "{" in line or ":" in line:
                    buffer.pop()
                    source = line + "\n"
                    tokens = Lexer(source).tokenize()
                    program = Parser(tokens).parse()
                    buffer = []
                else:
                    _print_error(e)
                    buffer = []
                    continue

            buffer = []

            if len(program.body) == 1 and isinstance(program.body[0], ExprStatement):
                result = interpreter.run(program)
                if result is not None:
                    print(_format_value(result))
            else:
                interpreter.run(program)

        except MgsRuntimeError as e:
            _print_error(e)
            buffer = []
        except KeyboardInterrupt:
            print("\nUse .exit to quit.")
            buffer = []
        except EOFError:
            print()
            break


def _print_error(e: LexerError | ParseError | MgsRuntimeError) -> None:
    if hasattr(e, "format"):
        formatted = e.format()
        lines = formatted.split("\n")
        for i, line in enumerate(lines):
            if i == 0:
                print(f"{_RED}{_BOLD}{line}{_RESET}")
            elif line.startswith("  ") and "|" in line:
                print(f"{_DIM}{line}{_RESET}")
            elif line.startswith("  ") and "^" in line:
                print(f"{_RED}{line}{_RESET}")
            else:
                print(line)
    else:
        print(f"{_RED}Error: {e}{_RESET}")


def _format_value(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "none"
    if isinstance(value, list):
        items = [_format_value(item) for item in value]
        return "[" + ", ".join(items) + "]"
    return repr(value)


def _print_ast(node: object, indent: int = 0) -> None:
    from dataclasses import fields as dc_fields
    from magmascript.lang import ast_nodes as ast

    prefix = "  " * indent
    class_name = type(node).__name__
    print(f"{prefix}{class_name}")

    if not hasattr(node, "__dataclass_fields__"):
        return

    for f in dc_fields(node):
        if f.name in ("line", "column"):
            continue
        value = getattr(node, f.name)
        if isinstance(value, list):
            for item in value:
                if hasattr(item, "__dataclass_fields__"):
                    _print_ast(item, indent + 1)
                else:
                    print(f"{prefix}  {item!r}")
        elif hasattr(value, "__dataclass_fields__"):
            _print_ast(value, indent + 1)
        else:
            print(f"{prefix}  {f.name}: {value!r}")
