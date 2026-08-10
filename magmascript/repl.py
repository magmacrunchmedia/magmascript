from __future__ import annotations

import os
import sys
from pathlib import Path

from magmascript.lang.lexer import Lexer, LexerError
from magmascript.lang.parser import Parser, ParseError
from magmascript.lang.interpreter import Interpreter, RuntimeError as MgsRuntimeError, MgsString
from magmascript.lang.ast_nodes import ExprStatement
from magmascript import __version__


# ANSI color codes
_RED = "\033[31m"
_DIM = "\033[2m"
_RESET = "\033[0m"
_BOLD = "\033[1m"

# Keywords and builtins for completion
_KEYWORDS = frozenset({
    "fn", "if", "else", "for", "in", "while", "return", "break", "continue",
    "and", "or", "not", "true", "false", "none",
})
_BUILTINS = frozenset({
    "print", "echo", "len", "type", "str", "int", "float", "range",
    "keys", "values", "abs", "min", "max", "sum", "args",
})
_DOT_COMMANDS = frozenset({
    ".exit", ".help", ".clear", ".ast",
    ".magma", ".crunch", ".texas", ".toast",
})
_CRUNCH_TARGETS = frozenset({"mb", "lastfm", "search", "archive", "scores", "gh", "all"})
_TEXAS_TARGETS = _CRUNCH_TARGETS
_TOAST_TARGETS = frozenset({"cache", "mb-cache", "lastfm-cache", "scores-cache", "gh-cache", "search-index", "all"})
_STRING_METHODS = frozenset({
    "split", "join", "upper", "lower", "contains", "replace",
    "length", "startswith", "endswith", "strip",
})


def repl() -> None:
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory
        _repl_enhanced()
    except ImportError:
        print("prompt_toolkit not installed — using basic REPL")
        print("Install with: pip install 'magmascript[cli]'\n")
        _repl_basic()


def _repl_enhanced() -> None:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.lexers import PygmentsLexer
    from prompt_toolkit.styles import Style

    from magmascript.lang.pygments_mgs import MgsLexer

    interpreter = Interpreter()
    buffer: list[str] = []

    history_path = Path.home() / ".magmascript_history"
    history = FileHistory(str(history_path))

    prompt_style = Style.from_dict({
        "mgs-prompt": "bold",
        "mgs-continuation": "dim",
    })

    class MagmaScriptCompleter(Completer):
        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            word = document.get_word_before_cursor(allowed="all")

            # Dot-commands at start of line
            if word.startswith(".") or (not text.strip() and not word):
                for cmd in _DOT_COMMANDS:
                    if cmd.startswith(word):
                        yield Completion(cmd, start_position=-len(word))
                return

            # Subcommand completion for .crunch, .texas, .toast
            stripped = text.strip()
            if stripped.startswith(".crunch ") or stripped.startswith(".texas ") or stripped.startswith(".toast "):
                prefix_cmd = stripped.split()[0]
                if prefix_cmd == ".crunch":
                    targets = _CRUNCH_TARGETS
                elif prefix_cmd == ".texas":
                    targets = _TEXAS_TARGETS
                else:
                    targets = _TOAST_TARGETS
                for t in sorted(targets):
                    if t.startswith(word):
                        yield Completion(t, start_position=-len(word))
                return

            # Check if we're completing after a dot (method access)
            line_before = text[:len(text) - len(word)]
            if word == "" and line_before.endswith("."):
                prefix_text = line_before[:-1].rstrip()
                obj_name = prefix_text.split()[-1] if prefix_text else ""
                yield from self._complete_methods(obj_name, "", interpreter)
                return

            if "." in word:
                parts = word.rsplit(".", 1)
                obj_name = parts[0]
                method_prefix = parts[1]
                yield from self._complete_methods(obj_name, method_prefix, interpreter)
                return

            # Standard completion: keywords, builtins, domains, user variables
            completions = set()
            completions |= _KEYWORDS
            completions |= _BUILTINS

            # Domain names
            try:
                from magmascript.core.registry import list_domains
                completions |= set(list_domains())
            except Exception:
                pass

            # User-defined variables from interpreter globals
            completions |= set(interpreter.globals._collect_names())

            for name in sorted(completions):
                if name.startswith(word):
                    yield Completion(name, start_position=-len(word))

        def _complete_methods(self, obj_name, prefix, interp):
            # Domain proxies
            try:
                from magmascript.core.registry import list_domains
                if obj_name in list_domains():
                    proxy = interp.globals.get(obj_name)
                    if hasattr(proxy, "_client"):
                        for attr in dir(proxy._client):
                            if not attr.startswith("_") and attr.startswith(prefix):
                                yield Completion(attr, start_position=-len(prefix))
                    return
            except Exception:
                pass

            # Check if it's a user variable that might be a string
            try:
                val = interp.globals.get(obj_name)
                if isinstance(val, str):
                    for method in _STRING_METHODS:
                        if method.startswith(prefix):
                            yield Completion(method, start_position=-len(prefix))
                    return
            except Exception:
                pass

            # Fallback: offer string methods (most common case after .)
            for method in _STRING_METHODS:
                if method.startswith(prefix):
                    yield Completion(method, start_position=-len(prefix))

    completer = MagmaScriptCompleter()
    lexer = PygmentsLexer(MgsLexer)

    session = PromptSession(
        history=history,
        completer=completer,
        lexer=lexer,
        style=prompt_style,
        multiline=True,
        prompt=HTML("<mgs-prompt>mgs></mgs-prompt> "),
        continuation=HTML("<mgs-continuation>...</mgs-continuation> "),
    )

    print(f"MagmaScript v{__version__}")
    print("Type .exit to quit, .help for help\n")

    while True:
        try:
            line = session.prompt()

            if line.strip() == ".exit":
                break

            if line.strip() == ".help":
                _print_help()
                continue

            if line.strip() == ".clear":
                interpreter = Interpreter()
                print("Variables cleared.")
                continue

            if line.strip() == ".ast":
                print("Paste expression, then press Enter:")
                try:
                    line = session.prompt("... ")
                    source = line + "\n"
                    tokens = Lexer(source).tokenize()
                    program = Parser(tokens).parse()
                    _print_ast(program, indent=0)
                except (LexerError, ParseError) as e:
                    _print_error(e)
                continue

            if line.strip() == ".magma":
                _handle_magma()
                continue

            if line.strip().startswith(".crunch"):
                _handle_crunch(line.strip())
                continue

            if line.strip().startswith(".texas"):
                _handle_texas(line.strip())
                continue

            if line.strip().startswith(".toast"):
                _handle_toast(line.strip())
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
            buffer = []
        except EOFError:
            print()
            break


def _repl_basic() -> None:
    import readline

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
                _print_help()
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

            if line.strip() == ".magma":
                _handle_magma()
                continue

            if line.strip().startswith(".crunch"):
                _handle_crunch(line.strip())
                continue

            if line.strip().startswith(".texas"):
                _handle_texas(line.strip())
                continue

            if line.strip().startswith(".toast"):
                _handle_toast(line.strip())
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


def _handle_magma() -> None:
    from magmascript.core.commands import magma
    try:
        status = magma()
        print(f"\nMagmaScript v{status.version}\n")
        print("Domains:")
        for name, state in status.domains.items():
            print(f"  {name:<12} {state}")
        print()
        cache = status.cache
        size = cache.get("total_size_bytes", 0)
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        print(f"Cache: {cache['total_files']} files, {size_str}")
        for dname, dinfo in cache.get("domains", {}).items():
            if isinstance(dinfo, dict):
                print(f"  {dname}: {dinfo.get('files', 0)} files")
        print()
    except Exception as e:
        print(f"Error: {e}")


def _handle_crunch(line: str) -> None:
    from magmascript.core.commands import crunch
    parts = line.split()
    target = parts[1] if len(parts) > 1 else ""
    dry_run = "--dry-run" in parts

    if not target:
        print("Usage: .crunch <target> [--dry-run]")
        print("Targets: mb, lastfm, search, archive, scores, gh, all")
        return

    try:
        result = crunch(target, dry_run=dry_run)
        _print_crunch_result(result)
    except Exception as e:
        print(f"Error: {e}")


def _handle_texas(line: str) -> None:
    from magmascript.core.commands import texas
    parts = line.split()
    target = parts[1] if len(parts) > 1 else ""
    dry_run = "--dry-run" in parts

    if not target:
        print("Usage: .texas <target> [--dry-run]")
        print("Targets: mb, lastfm, search, archive, scores, gh, all")
        return

    try:
        result = texas(target, dry_run=dry_run)
        _print_crunch_result(result)
    except Exception as e:
        print(f"Error: {e}")


def _handle_toast(line: str) -> None:
    from magmascript.core.commands import toast
    parts = line.split()
    target = parts[1] if len(parts) > 1 else ""
    domain = None
    if "--domain" in parts:
        idx = parts.index("--domain")
        if idx + 1 < len(parts):
            domain = parts[idx + 1]

    if not target:
        print("Usage: .toast <target> [--domain <name>]")
        print("Targets: cache, mb-cache, lastfm-cache, scores-cache, gh-cache, search-index, all")
        return

    try:
        result = toast(target, domain=domain)
        if result.message:
            print(result.message)
    except Exception as e:
        print(f"Error: {e}")


def _print_crunch_result(result) -> None:
    if result.completed:
        print(f"\n{result.target}: {result.completed} completed")
    if result.skipped:
        print(f"  {result.skipped} skipped")
    if result.elapsed_seconds:
        print(f"  {result.elapsed_seconds:.1f}s")
    if result.details:
        if isinstance(result.details, dict):
            for k, v in result.details.items():
                print(f"  {k}: {v}")
        else:
            print(f"  {result.details}")
    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for err in result.errors:
            print(f"  {err}")
    print()


def _print_help() -> None:
    print("Commands:")
    print("  .exit    - Quit the REPL")
    print("  .help    - Show this help")
    print("  .clear   - Clear variables")
    print("  .ast     - Show AST for next input")
    print("  .magma   - Show system status dashboard")
    print("  .crunch  - Run a pipeline (mb, lastfm, search, archive, scores, gh, all)")
    print("  .texas   - Full/heavy operation (same targets, no shortcuts)")
    print("  .toast   - Burn/clear caches (cache, mb-cache, all, etc.)")
    print()
    print("Language:")
    print("  Variables:  x = 42")
    print("  Functions:  add = fn(a, b) { a + b }")
    print("  Arrow:      double = x -> x * 2")
    print("  If:         if x > 10 { print(x) }")
    print("  For:        for i in range(5) { print(i) }")
    print("  Domains:    mcp.search('query')")


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
