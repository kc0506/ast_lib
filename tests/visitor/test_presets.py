import ast

from ast_lib.visitor.core import BaseNodeVisitor
from ast_lib.visitor.presets import ParentMap


def test_parent_map():
    source = """
def f1():
    def f2():
        def f3():
            pass
    """

    expected_parent_maps = {
        "f1": {"f1": None},
        "f2": {"f1": None, "f2": "f1"},
        "f3": {"f1": None, "f2": "f1", "f3": "f2"},
    }

    class Visitor(BaseNodeVisitor):
        parent_map = ParentMap()

        def visit_FunctionDef(self, node: ast.FunctionDef):
            name_parent_map = {
                k.name: v
                for k, v in self.parent_map.items()
                if isinstance(k, ast.FunctionDef)
            }
            assert name_parent_map == expected_parent_maps[node.name]

    Visitor().visit(ast.parse(source))
