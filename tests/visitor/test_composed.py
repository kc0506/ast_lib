import ast
import inspect
from types import ModuleType
from typing import Any, Hashable

import pytest

import ast_lib.visitor.core
from ast_lib.visitor.context import node_context
from ast_lib.visitor.core import BaseNodeVisitor
from ast_lib.visitor.presets import ParentMap


def collect_qualname_set(module: ModuleType) -> set[str]:
    qualname_set = set()

    visited = set()

    def get_key(obj: Any) -> str:
        if isinstance(obj, Hashable):
            return str(hash(obj))
        return repr(obj)

    def recur(obj: Any):
        if get_key(obj) in visited:
            return
        visited.add(get_key(obj))

        if hasattr(obj, "__dict__"):
            for value in obj.__dict__.values():
                recur(value)

        if getattr(obj, "__module__", None) != module.__name__:
            return

        qualname = getattr(obj, "__qualname__", None)
        if qualname is not None:
            try:
                # ? if source is not available, we cannot visit this node
                inspect.getsource(obj)
                qualname_set.add(qualname)
            except OSError:
                pass

    recur(module)

    return qualname_set


@pytest.mark.parametrize(["module"], [[ast], [ast_lib.visitor.core]])
def test_basic_visitor(module):
    source = inspect.getsource(module)
    mod = ast.parse(source)
    expected_qualname_set = collect_qualname_set(module)
    assert expected_qualname_set

    qualname_set = set()

    class Visitor(BaseNodeVisitor):
        parent_map = ParentMap()

        # TODO: why not working
        # current_node: NodeContextVar["A", ast.AST, ast.AST | None, Literal[True]] = (
        #     NodeContextVar(ast.AST, lambda node: node, default=None)
        # )

        # TODO: add these to presets?
        @node_context(ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        def qualname(
            self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ) -> str:
            qualname = ".".join(self.qualname_namespace + [node.name])
            qualname_set.add(qualname)
            return qualname

        @node_context(
            ast.ClassDef,
            ast.FunctionDef,
            ast.AsyncFunctionDef,
            default_factory=lambda: [],
        )
        def qualname_namespace(
            self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ) -> list[str]:
            ns = self.qualname_namespace + [node.name]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                ns = ns + ["<locals>"]
            return ns

    visitor = Visitor()
    visitor.visit(mod)
    assert qualname_set >= expected_qualname_set
    # raise Exception("stop")
