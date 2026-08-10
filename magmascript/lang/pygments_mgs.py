"""Pygments lexer for MagmaScript (.mgs) files."""

from pygments.lexer import RegexLexer, bygroups, using
from pygments.token import (
    Comment,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Whitespace,
)

__all__ = ["MgsLexer"]


class MgsLexer(RegexLexer):
    name = "MagmaScript"
    aliases = ["magmascript", "mgs"]
    filenames = ["*.mgs"]
    mimetypes = ["text/x-magmascript"]

    tokens = {
        "root": [
            # Whitespace
            (r"\s+", Whitespace),

            # Comments
            (r"//.*$", Comment.Single),
            (r"#.*$", Comment.Single),

            # F-strings
            (r'f"(?:[^"\\]|\\.)*"', String.Interpol),
            (r"f'(?:[^'\\]|\\.)*'", String.Interpol),

            # Strings
            (r'"(?:[^"\\]|\\.)*"', String.Double),
            (r"'(?:[^'\\]|\\.)*'", String.Single),

            # Numbers
            (r"\d+\.\d+", Number.Float),
            (r"\d+", Number.Integer),

            # Keywords
            (r"\b(fn|if|else|for|in|while|return|break|continue)\b", Keyword),
            (r"\b(and|or|not)\b", Keyword),
            (r"\b(true|false|none)\b", Keyword.Constant),

            # Builtins
            (
                r"\b(print|echo|len|type|str|int|float|range|keys|values|abs|min|max|sum|args)\b",
                Name.Builtin,
            ),

            # Identifiers
            (r"[A-Za-z_]\w*", Name),

            # Operators
            (r"->|==|!=|<=|>=|\+=|-=|[+\-*/%=<>]", Operator),

            # Punctuation
            (r"[{}()\[\],.]", Punctuation),
        ],
    }
