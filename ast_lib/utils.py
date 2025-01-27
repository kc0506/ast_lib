import ast
from typing import overload


def parse_as_expr(s: str) -> ast.expr:
    node = ast.parse(s)
    match node:
        case ast.Module(body=[ast.Expr(expr)]):
            return expr
        case _:
            raise ValueError(f"Result is not an expression:\n{ast.dump(node)}")


@overload
def parse_as_stmt[T: ast.stmt](s: str, tp: type[T]) -> T: ...


@overload
def parse_as_stmt[T: type[ast.stmt]](s: str) -> ast.stmt: ...


def parse_as_stmt[T: ast.stmt](s: str, tp: type[T] = ast.stmt) -> T:  # type: ignore
    node = ast.parse(s)
    match node:
        case ast.Module(body=[ast.stmt() as stmt]):
            if isinstance(stmt, tp):
                return stmt
            raise ValueError(
                f"Result is not an statement of type {tp}:\n{ast.dump(node)}"
            )
        case _:
            raise ValueError(f"Result is not an statement:\n{ast.dump(node)}")


def expand_union(node: ast.expr) -> list[ast.expr]:
    match node:
        case ast.BinOp(left=left, right=right):
            left_list = expand_union(left)
            right_list = expand_union(right)
            return left_list + right_list
        case _:
            return [node]
