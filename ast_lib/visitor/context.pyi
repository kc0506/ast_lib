import ast
from contextlib import contextmanager
from typing import (
    Callable,
    Iterator,
    Literal,
    overload,
)

from .core import Hook, HookProvider
from .utils import DescriptorHelper

type _TrueType = Literal[True]
type _FalseType = Literal[False]

class NodeContextVar[
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
    T,
    _HasDefault: _TrueType | _FalseType,
](HookProvider, DescriptorHelper):
    @overload
    def __init__(
        self: NodeContextVar[VisitorT, N, T, _TrueType],  # pyright: ignore
        node_types: type[N] | tuple[type[N], ...],
        get_value: Callable[[N], T] | Callable[[VisitorT, N], T],
        default: T,
    ): ...
    @overload
    def __init__(
        self: NodeContextVar[VisitorT, N, T, _TrueType],  # pyright: ignore
        node_types: type[N] | tuple[type[N], ...],
        get_value: Callable[[N], T] | Callable[[VisitorT, N], T],
        default_factory: Callable[[], T],
    ): ...
    @overload
    def __init__(
        self: NodeContextVar[VisitorT, N, T, _FalseType],  # pyright: ignore
        node_types: type[N] | tuple[type[N], ...],
        get_value: Callable[[N], T] | Callable[[VisitorT, N], T],
    ): ...
    #
    @property
    def stack_name(self) -> str: ...
    #
    @contextmanager
    def push(self, instance: ast.NodeVisitor, node: ast.AST) -> Iterator[None]: ...
    #
    @overload
    def __get__(
        self: NodeContextVar[VisitorT, N, T, _TrueType],
        instance: VisitorT,
        owner: type[VisitorT],
    ) -> T: ...
    @overload
    def __get__(
        self: NodeContextVar[VisitorT, N, T, _FalseType],
        instance: VisitorT,
        owner: type[VisitorT],
    ) -> T | None: ...
    #
    def get_hook(self) -> Hook: ...

@overload
def node_context[VisitorT: ast.NodeVisitor, N: ast.AST, T](
    *node_types: type[N],
) -> Callable[
    [Callable[[N], T] | Callable[[VisitorT, N], T]],
    NodeContextVar[VisitorT, N, T, _FalseType],
]: ...
@overload
def node_context[Visitor: ast.NodeVisitor, N: ast.AST, T](
    *node_types: type[N],
    default: T,
) -> Callable[
    [Callable[[N], T] | Callable[[Visitor, N], T]],
    NodeContextVar[Visitor, N, T, _TrueType],
]: ...
@overload
def node_context[Visitor: ast.NodeVisitor, N: ast.AST, T](
    *node_types: type[N],
    default_factory: Callable[[], T],
) -> Callable[
    [Callable[[N], T] | Callable[[Visitor, N], T]],
    NodeContextVar[Visitor, N, T, _TrueType],
]: ...
