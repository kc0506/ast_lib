import ast
from typing import Set


class UsedNamesVisitor(ast.NodeVisitor):
    def generic_visit(self, node: ast.AST) -> Set[str]:
        result = set()
        for _, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        result.update(self.visit(item))
            elif isinstance(value, ast.AST):
                result.update(self.visit(value))
        return result

    def visit_Name(self, node: ast.Name) -> Set[str]:
        return {node.id}


class DiscardNodes(ast.NodeTransformer):
    def __init__(self, discarded_nodes: set[ast.AST]):
        self.discarded_nodes = discarded_nodes

    def visit(self, node: ast.AST) -> ast.AST | None:
        if node in self.discarded_nodes:
            return None
        return super().visit(node)
