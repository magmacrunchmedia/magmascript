"""AST visitor and transformer base classes.

Provides a generic traversal framework for the MagmaScript AST.
Subclass Visitor for read-only passes, Transformer for AST rewrites.

Usage::

    from magmascript.lang.visitor import Visitor

    class MyChecker(Visitor):
        def visit_Identifier(self, node):
            if node.name == "bad":
                self.report(node)

        def visit_FunctionDef(self, node):
            # Custom handling, then recurse into body
            self.visit(node.body)

    checker = MyChecker()
    checker.visit(program)
"""

from __future__ import annotations

from magmascript.lang import ast_nodes as ast


def children(node: ast.ASTNode) -> list[ast.ASTNode]:
    """Extract all ASTNode children from a node.

    Handles dataclass fields, lists, and dicts (used by FunctionDef.defaults).
    """
    out: list[ast.ASTNode] = []
    for value in vars(node).values():
        if isinstance(value, ast.ASTNode):
            out.append(value)
        elif isinstance(value, list):
            out.extend(v for v in value if isinstance(v, ast.ASTNode))
        elif isinstance(value, dict):
            out.extend(v for v in value.values() if isinstance(v, ast.ASTNode))
    return out


class Visitor:
    """Read-only AST visitor. Subclass and override visit_<NodeType> methods.

    The default visit() method recurses into children automatically.
    Override a visit method to customize traversal for that node type.
    """

    def visit(self, node: ast.ASTNode | None) -> None:
        if node is None:
            return
        method = getattr(self, f"visit_{type(node).__name__}", None)
        if method is not None:
            method(node)
        else:
            self._default_visit(node)

    def _default_visit(self, node: ast.ASTNode) -> None:
        for child in children(node):
            self.visit(child)


class Transformer:
    """AST transformer. Subclass and override visit_<NodeType> methods.

    Each visit method should return a (possibly modified) node.
    The default transform() recurses into children and returns the original node.
    """

    def transform(self, node: ast.ASTNode | None) -> ast.ASTNode | None:
        if node is None:
            return None
        method = getattr(self, f"visit_{type(node).__name__}", None)
        if method is not None:
            return method(node)
        return self._default_transform(node)

    def _default_transform(self, node: ast.ASTNode) -> ast.ASTNode:
        for field_name, value in vars(node).items():
            if isinstance(value, ast.ASTNode):
                setattr(node, field_name, self.transform(value))
            elif isinstance(value, list):
                new_list = []
                for item in value:
                    if isinstance(item, ast.ASTNode):
                        new_list.append(self.transform(item))
                    else:
                        new_list.append(item)
                setattr(node, field_name, new_list)
            elif isinstance(value, dict):
                new_dict = {}
                for k, v in value.items():
                    if isinstance(v, ast.ASTNode):
                        new_dict[k] = self.transform(v)
                    else:
                        new_dict[k] = v
                setattr(node, field_name, new_dict)
        return node
