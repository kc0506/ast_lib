from __future__ import annotations

import ast
import copy
import shutil
import tokenize
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Generator

from typer import Typer

from ast_lib.visitor.context import node_context
from ast_lib.visitor.core import BaseNodeVisitor
from ast_lib.visitor.reducer import nodelist_collector, nodemap_collector

from .unparser import UnparserWithComments
from .utils import DiscardNodes

app = Typer()


class SubstituteVariables(ast.NodeTransformer):
    def __init__(self, name_map: dict[str, ast.expr]):
        self.name_map = name_map

    def visit_Name(self, node: ast.Name) -> ast.expr:
        if node.id in self.name_map:
            return self.name_map[node.id]
        return node


class TransformVisitorPyi(BaseNodeVisitor, ast.NodeTransformer):
    def __init__(self):
        super().__init__()
        self.discarded_nodes = set()

    @nodemap_collector(ast.TypeAlias, get_key=lambda node: node.name.id)
    def type_alias_map(self, node: ast.TypeAlias) -> ast.TypeAlias:
        return node

    @nodelist_collector(ast.Assign, patterns=["__expand__=~"])
    def expands(self, node: ast.Assign) -> Generator[str]:
        self.discarded_nodes.add(node)
        value = node.value
        match value:
            case ast.Tuple(elts=elts):
                for elt in elts:
                    if isinstance(elt, ast.Name):
                        self.discarded_nodes.add(self.type_alias_map[elt.id])
                        yield elt.id
            case _:
                raise ValueError(f"Invalid target type: {ast.unparse(value)}")

    def visit_Subscript(self, node: ast.Subscript) -> ast.expr:
        assert isinstance(node.value, ast.Name)
        if node.value.id not in self.expands:
            self.generic_visit(node)
            return node

        match node.slice:
            case ast.Tuple(elts=elts):
                pass
            case ast.Name(id=id):
                elts = [ast.Name(id=id)]
            case _:
                raise ValueError(f"Invalid slice type: {ast.unparse(node.slice)}")

        type_alias_node = self.type_alias_map[node.value.id]
        names: list[str] = []
        for type_param in type_alias_node.type_params:
            assert isinstance(type_param, ast.TypeVar)
            names.append(type_param.name)

        assert len(names) == len(elts)
        name_map = dict(zip(names, elts))
        return SubstituteVariables(name_map).visit(copy.deepcopy(type_alias_node.value))

    def transform(self):
        pass


# if TYPE_CHECKING:
#     Unparser = ast.NodeVisitor
# else:
#     Unparser = ast._Unparser


@app.command()
def transform_pyi(module_name: str):
    proto_path = (
        Path(__file__).parent.parent / f"ast_lib/visitor/{module_name}.proto.pyi"
    )
    if not proto_path.exists():
        print(f"Proto file for {module_name} does not exist, aborting")
        return

    original_path = proto_path.parent / f"{module_name}.pyi"
    backup_path = proto_path.parent / f"{module_name}.backup.pyi"
    shutil.copy(original_path, backup_path)

    with open(proto_path, "r", encoding="utf-8") as f:
        proto_content = f.read()

    visitor = TransformVisitorPyi()
    m = visitor.visit(ast.parse(proto_content))
    assert m is not None
    print(visitor.discarded_nodes)
    # breakpoint()
    m = DiscardNodes(visitor.discarded_nodes).visit(m)
    assert m is not None

    with open(proto_path, "r", encoding="utf-8") as f:
        tokens = tokenize.generate_tokens(f.readline)
        unparser = UnparserWithComments(tokens, ignore_prefixes=["[proto]"])
        # transformed: str = unparser.visit(ast.fix_missing_locations(m))
        transformed: str = unparser.visit(m)

    # new_path = proto_path.parent / f"{module_name}.new.pyi"
    new_path = original_path
    with open(new_path, "w", encoding="utf-8") as f:
        f.write(transformed)


if __name__ == "__main__":
    app()
