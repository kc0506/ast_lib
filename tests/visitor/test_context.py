import ast
import inspect

from ast_lib.visitor.context import node_context
from ast_lib.visitor.core import BaseNodeVisitor
from ast_lib.visitor.exception import SkipNode


def dfs_walk(node: ast.AST):
    """
    Recursively yield all descendant nodes in the tree starting at *node*
    (including *node* itself) in depth-first order.
    """
    yield node
    for child in ast.iter_child_nodes(node):
        yield from dfs_walk(child)


def test_dfs_walk():
    source = inspect.getsource(ast)
    mod = ast.parse(source)

    nodes = []

    class Visitor(ast.NodeVisitor):
        def visit(self, node: ast.AST):
            nodes.append(node)
            super().visit(node)

    Visitor().visit(mod)

    assert nodes == list(dfs_walk(mod))


def test_context_simple():
    source = """
def f1():
    x1: int = 1

    def f2():
        y1: int = 1

        class c1:
            def f3():
                z1: int = 1
            z2: int = 1
        y2: int = 1
    x2: int = 1

class c2:    
    v: int = 1
    """

    expected_function = {
        "x1": "f1",
        "y1": "f2",
        "z1": "f3",
        "z2": "f2",
        "y2": "f2",
        "x2": "f1",
        "v": None,
    }

    expected_function_or_class = {
        "x1": "f1",
        "y1": "f2",
        "z1": "f3",
        "z2": "c1",
        "y2": "f2",
        "x2": "f1",
        "v": "c2",
    }

    class Visitor(BaseNodeVisitor):
        @node_context(ast.FunctionDef)
        def current_function(self, node: ast.FunctionDef) -> str:
            return node.name

        @node_context(ast.FunctionDef, ast.ClassDef)
        def current_function_or_class(
            self, node: ast.FunctionDef | ast.ClassDef
        ) -> str:
            return node.name

        def visit_AnnAssign(self, node: ast.AnnAssign):
            assert isinstance(node.target, ast.Name)
            assert self.current_function == expected_function[node.target.id]
            assert (
                self.current_function_or_class
                == expected_function_or_class[node.target.id]
            )

    Visitor().visit(ast.parse(source))


def test_context_independent():
    source = """\
def f1():
    x1: int = 1
    x2: int = 1
"""

    class Visitor(BaseNodeVisitor):
        @node_context(ast.FunctionDef)
        def current_function(self, node: ast.FunctionDef) -> str:
            assert Visitor().current_function is None
            return node.name

    Visitor().visit(ast.parse(source))


def test_skip():
    source = """\
def f1():
    x1: int = 1

    def _f2():
        y1: int = 1

        def f3():
            z1: int = 1
        y2: int = 1

    x2: int = 1
"""

    expected_function = {
        "x1": "f1",
        "y1": "f1",
        "z1": "f3",
        "y2": "f1",
        "x2": "f1",
    }

    class Visitor(BaseNodeVisitor):
        @node_context(ast.FunctionDef)
        def current_function(self, node: ast.FunctionDef) -> str:
            if node.name.startswith("_"):
                raise SkipNode(node)
            return node.name

        def visit_AnnAssign(self, node: ast.AnnAssign):
            assert isinstance(node.target, ast.Name)
            assert self.current_function == expected_function[node.target.id]

    Visitor().visit(ast.parse(source))
