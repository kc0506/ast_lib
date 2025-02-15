import ast


# Traditional approach - verbose and hard to read
def match_method_call(node: ast.AST) -> dict | None:
    if not isinstance(node, ast.Call):
        return None
    if not isinstance(node.func, ast.Attribute):
        return None
    if not isinstance(node.func.value, ast.Name):
        return None
    if len(node.args) != 1:
        return None
    if not isinstance(node.args[0], ast.Subscript):
        return None
    if not isinstance(node.args[0].value, ast.Name):
        return None
    if node.args[0].value.id != "self":
        return None

    return {
        "obj_name": node.func.value.id,
        "method": node.func.attr,
        "idx": node.args[0].slice,
    }


# ast_lib approach - clean and intuitive
from ast_lib.pattern import parse_pattern


def match_method_call(node: ast.AST) -> dict | None:
    pattern = parse_pattern("$obj_name.$method(self[$idx])")
    if match := pattern.match(node):
        return match.kw_groups
