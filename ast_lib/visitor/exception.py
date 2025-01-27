
import ast


class SkipNode(Exception):
    def __init__(self, node: ast.AST):
        super().__init__()
        self.node = node


class SkipVisit(Exception):
    def __init__(self, node: ast.AST):
        super().__init__()
        self.node = node
