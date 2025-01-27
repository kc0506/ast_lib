import ast
from typing import (
    Any,
    Callable,
)

from .core import Hook, HookMode, HookProvider
from .utils import DescriptorHelper

class ParentMap(HookProvider, DescriptorHelper):
    def get_hook(self) -> Hook: ...
    #
    def __get__(
        self, instance: ast.NodeVisitor, owner: type[ast.NodeVisitor]
    ) -> dict[ast.AST, ast.AST | None]: ...

class PureNodeVisitHook[VisitorT: ast.NodeVisitor, N: ast.AST](
    HookProvider, DescriptorHelper
):
    def __init__(
        self,
        node_types: tuple[type[N], ...],
        func: Callable[[VisitorT, N], Any] | Callable[[VisitorT], Any],
        mode: HookMode = "before",
        #
        before: tuple[str, ...] = (),
        after: tuple[str, ...] = (),
    ): ...
    def get_hook(self) -> Hook: ...

def pure_visit[VisitorT: ast.NodeVisitor, N: ast.AST](
    *node_types: type[N],
    mode: HookMode = "before",
    #
    before: tuple[str, ...] = (),
    after: tuple[str, ...] = (),
) -> Callable[[Callable[[VisitorT, N], Any] | Callable[[VisitorT], Any]], Any]: ...
