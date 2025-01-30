# pyright: reportUnusedImport=false, reportUnusedFunction=false, reportUnusedVariable=false, reportUnusedClass=false
from __future__ import annotations

import ast
from typing import Generator, assert_type

from ast_lib.match_pattern import MatchResult, MatchTypeHint
from ast_lib.visitor.context import NodeContextVar, node_context
from ast_lib.visitor.core import BaseNodeVisitor
from ast_lib.visitor.presets import pure_visit
from ast_lib.visitor.reducer import node_reducer, nodelist_collector, nodemap_collector


def test_context_class():
    class Visitor(BaseNodeVisitor):
        a = NodeContextVar(ast.FunctionDef, lambda node: node.name)
        b = NodeContextVar(ast.FunctionDef, lambda node: node.name, default="default")
        c = NodeContextVar(
            (ast.FunctionDef, ast.ClassDef), lambda node: node.name, default="default"
        )

        def func(self, node: ast.FunctionDef | ast.ClassDef) -> str:
            return self.b + node.name

        d = NodeContextVar(
            (ast.FunctionDef, ast.ClassDef),
            func,
            default_factory=lambda: "default",
        )

    assert_type(Visitor().a, str | None)
    assert_type(Visitor().b, str)


def test_context_decorator():
    class Visitor(BaseNodeVisitor):
        @node_context(ast.FunctionDef)
        def a(self, node: ast.FunctionDef) -> str:
            return node.name

        @node_context(ast.FunctionDef, default="default")
        def b(self, node: ast.FunctionDef) -> str:
            return node.name

        @node_context(ast.FunctionDef, default_factory=lambda: "default")
        def c(self, node: ast.FunctionDef) -> str:
            return node.name

        @node_context(ast.FunctionDef, default_factory=lambda: "default")
        def d(self, node: ast.FunctionDef) -> str:
            return self.c + node.name

        @node_context(ast.FunctionDef, default_factory=lambda: "default")
        def test_match_result(
            self,
            node: ast.FunctionDef,
            match_result: MatchResult[ast.FunctionDef, int, dict],
        ) -> str: ...

    assert_type(Visitor().a, str | None)
    assert_type(Visitor().b, str)
    assert_type(Visitor().c, str)
    assert_type(Visitor().d, str)


def test_pure_visit():
    class Visitor(BaseNodeVisitor):
        field: str = ""

        @pure_visit(ast.FunctionDef, mode="before")
        def func1(self, node: ast.FunctionDef) -> str:
            assert_type(self.field, str)
            return node.name

        @pure_visit(ast.FunctionDef, mode="before")
        def test_match_result(
            self,
            node: ast.FunctionDef,
            match_result: MatchResult[ast.FunctionDef, int, dict],
        ) -> str:
            (x,) = match_result.groups
            assert_type(x, int)
            assert_type(self.field, str)
            return node.name

        @pure_visit(ast.FunctionDef)
        def func2(self, node: ast.FunctionDef) -> str:
            assert_type(self.field, str)
            return node.name


def test_reducer():
    class Visitor(BaseNodeVisitor):
        @node_reducer(ast.FunctionDef, initial_value=lambda: 0)
        def func(self, prev: int, node: ast.FunctionDef) -> int: ...

        @nodelist_collector(ast.FunctionDef)
        def func_list(self, node: ast.FunctionDef) -> ast.FunctionDef:
            return node

        @nodelist_collector(ast.FunctionDef, pattern="def $name():...")
        def func_list_with_pattern(self, node: ast.FunctionDef) -> ast.FunctionDef:
            return node

        @nodelist_collector(ast.FunctionDef)
        def func_list_with_generator(self, node: ast.FunctionDef) -> Generator[int]:
            yield len(self.func_list)

        @nodelist_collector(
            ast.FunctionDef, match_type_hint=MatchTypeHint[ast.FunctionDef, dict]()
        )
        def func_list_with_type_hint(
            self,
            node: ast.FunctionDef,
            match_result: MatchResult[ast.FunctionDef, dict],
        ) -> Generator[int]:
            yield len(self.func_list)

        @nodelist_collector(ast.FunctionDef)
        def func_list_with_match_result(
            self,
            node: ast.FunctionDef,
            match_result: MatchResult[ast.FunctionDef, dict],
        ) -> Generator[int]:
            yield len(self.func_list)

        @nodemap_collector(
            ast.FunctionDef,
            get_key=lambda node: (assert_type(node, ast.FunctionDef), node.name)[1],
        )
        def func_map(self, node: ast.FunctionDef) -> ast.FunctionDef:
            return node

    assert_type(Visitor().func, int)
    assert_type(Visitor().func_list, list[ast.FunctionDef])
    assert_type(Visitor().func_map, dict[str, ast.FunctionDef])
