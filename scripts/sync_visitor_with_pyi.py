from __future__ import annotations

import ast
import tokenize
from pathlib import Path
from typing import Annotated

import typer
from typer import Typer

from ast_lib.visitor.context import node_context
from ast_lib.visitor.core import BaseNodeVisitor
from ast_lib.visitor.exception import SkipNode
from ast_lib.visitor.presets import pure_visit
from ast_lib.visitor.reducer import nodemap_collector

from .unparser import UnparserWithComments

app = Typer()


class CollectNodes(BaseNodeVisitor):
    @node_context(ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.TypeAlias)
    def qualname(
        self,
        node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef | ast.TypeAlias,
    ) -> str:
        if isinstance(node, ast.TypeAlias):
            name = node.name.id
        else:
            name = node.name

        qualname = ".".join(self.qualname_namespace + [name])
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

    @nodemap_collector(
        ast.FunctionDef,
        ast.ClassDef,
        ast.TypeAlias,
        get_key=lambda self, node: self.qualname,
    )
    def node_map(self, node: ast.AST) -> ast.AST:
        match node:
            case ast.FunctionDef(decorator_list=[ast.Name(id="overload")]):
                raise SkipNode(node)

        return node


class SyncWithVisitorPyi(BaseNodeVisitor, ast.NodeTransformer):
    def __init__(self, node_map: dict[str, ast.AST]):
        super().__init__()
        self.node_map = node_map

    @node_context(ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.TypeAlias)
    def qualname(
        self,
        node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef | ast.TypeAlias,
    ) -> str:
        if isinstance(node, ast.TypeAlias):
            name = node.name.id
        else:
            name = node.name

        qualname = ".".join(self.qualname_namespace + [name])
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

    @pure_visit(ast.FunctionDef, ast.ClassDef, ast.TypeAlias)
    def replace_node(
        self, node: ast.FunctionDef | ast.ClassDef | ast.TypeAlias
    ) -> None:
        name = self.qualname
        if name not in self.node_map:
            return

        replace_node = self.node_map[name]
        assert isinstance(replace_node, type(node))

        match node:
            case ast.ClassDef(bases=[ast.Name("TypedDict")]):
                include_body = True
            case _:
                include_body = False

        for field, value in ast.iter_fields(replace_node):
            if field == "body" and not include_body:
                continue

            def filter_decorator(deco: ast.expr) -> bool:
                match deco:
                    case ast.Name(id="overload"):
                        return False
                    case _:
                        return True

            if field == "decorator_list":
                value = [deco for deco in value if filter_decorator(deco)]

            setattr(node, field, value)
        return

        # TODO

        if not isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            return
        assert isinstance(replace_node, type(node))

        # In the following, we assume the replace node is only used once, so we can mutate it.

        location_fields = (
            "lineno",
            "col_offset",
            "end_lineno",
            "end_col_offset",
        )

        cur_body = node.body
        node.body = []
        replace_node.body = []

        cur_children = list(ast.walk(node))
        replace_children = list(ast.walk(replace_node))
        assert len(cur_children) == len(replace_children), node.name

        for cur_child, replace_child in zip(cur_children, replace_children):
            assert type(cur_child) is type(replace_child)
            for field in location_fields:
                if hasattr(replace_child, field):
                    setattr(replace_child, field, getattr(cur_child, field))

        for field, value in ast.iter_fields(replace_node):
            # if field == "body" or field in location_fields:
            #     continue
            setattr(node, field, value)
        node.body = cur_body


def sync_with_pyi(module_name: str):
    """
    Update `FunctionDef`, `ClassDef`, `TypeAlias` with same name.
    """

    # Fix: explicit replace type.
    # TODO: blank line, comments.

    proto_path = (
        Path(__file__).parent.parent / f"ast_lib/visitor/{module_name}.proto.pyi"
    )
    if not proto_path.exists():
        print(f"Proto file for {module_name} does not exist, aborting")
        return

    original_path = proto_path.parent / f"{module_name}.py"
    with open(original_path, "r", encoding="utf-8") as f:
        original_content = f.read()

    with open(proto_path, "r", encoding="utf-8") as f:
        proto_content = f.read()

    collector = CollectNodes()
    collector.visit(ast.parse(proto_content))

    visitor = SyncWithVisitorPyi(collector.node_map)
    m = visitor.visit(ast.parse(original_content))
    assert m is not None

    with open(original_path, "r", encoding="utf-8") as f:
        tokens = tokenize.generate_tokens(f.readline)
        unparser = UnparserWithComments(tokens, ignore_prefixes=["[proto]"])
        # transformed: str = unparser.visit(ast.fix_missing_locations(m))
        transformed: str = unparser.visit(m)

    header = f"# Synced by scripts/{Path(__file__).name} with {proto_path.name}\n\n"

    # new_path = proto_path.parent / f"{module_name}.new.py"
    new_path = original_path
    with open(new_path, "w", encoding="utf-8") as f:
        if not original_content.startswith(header):
            f.write(header)
        f.write(transformed)


@app.command()
def sync_visitors(module_names: Annotated[list[str], typer.Argument()]):
    for module_name in module_names:
        sync_with_pyi(module_name)


if __name__ == "__main__":
    app()
