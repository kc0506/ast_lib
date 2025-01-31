import ast
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
)

from .core import Hook, HookMode, HookProvider
from .utils import DescriptorHelper

if TYPE_CHECKING:
    from ..pattern import MatchResult

type NodeTypes[N] = type[N] | tuple[type[N], ...]
type VisitHook[VisitorT: ast.NodeVisitor, N: ast.AST] = (
    Callable[[VisitorT, N], Any] | Callable[[VisitorT, N, MatchResult], Any]
)

__expand__ = (
    NodeTypes,
    VisitHook,
)

class ParentMap(HookProvider, DescriptorHelper):
    def get_hook(self) -> Hook: ...
    def __get__(
        self, instance: ast.NodeVisitor, owner: type[ast.NodeVisitor]
    ) -> dict[ast.AST, ast.AST | None]: ...

class PureNodeVisitHook[
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
](HookProvider, DescriptorHelper):
    def __init__(
        self,
        node_types: NodeTypes[N],
        func: Callable[[VisitorT, N], Any] | Callable[[VisitorT], Any],
        mode: HookMode = "before",
        #
        before: tuple[str, ...] = (),
        after: tuple[str, ...] = (),
    ): ...
    def get_hook(self) -> Hook: ...

def pure_visit[VisitorT: ast.NodeVisitor, N: ast.AST, *Args, Kwargs: dict](
    *node_types: type[N],
    mode: HookMode = "before",
    #
    before: tuple[str, ...] = (),
    after: tuple[str, ...] = (),
) -> Callable[[VisitHook[VisitorT, N]], PureNodeVisitHook[VisitorT, N]]: ...
