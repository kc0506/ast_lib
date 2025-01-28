import ast
from contextlib import contextmanager
from typing import (
    Callable,
    Iterator,
    Literal,
    overload,
)

from ..match_pattern import MatchResult
from .core import Hook, HookProvider
from .utils import DescriptorHelper

type NodeTypes[N] = type[N] | tuple[type[N], ...]
type GetValue[VisitorT, N: ast.AST, T, *Args, Kwargs: dict] = (
    Callable[[N], T]
    | Callable[[VisitorT, N], T]
    | Callable[[VisitorT, N, MatchResult[N, *Args, Kwargs]], T]
)

__expand__ = (
    NodeTypes,
    GetValue,
)

type _TrueType = Literal[True]
type _FalseType = Literal[False]

class NodeContextVar[
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
    T,
    _HasDefault: _TrueType | _FalseType,
    *Args,
    Kwargs: dict,
](HookProvider, DescriptorHelper):
    @overload
    def __init__(
        self: NodeContextVar[VisitorT, N, T, _TrueType, *Args, Kwargs],  # pyright: ignore
        node_types: NodeTypes[N],
        get_value: GetValue[VisitorT, N, T, *Args, Kwargs],
        *,
        default: T,
        pred: GetValue[VisitorT, N, bool, *Args, Kwargs] | None = None,
    ): ...
    @overload
    def __init__(
        self: NodeContextVar[VisitorT, N, T, _TrueType, *Args, Kwargs],  # pyright: ignore
        node_types: NodeTypes[N],
        get_value: GetValue[VisitorT, N, T, *Args, Kwargs],
        *,
        default_factory: Callable[[], T],
        pred: GetValue[VisitorT, N, bool, *Args, Kwargs] | None = None,
    ): ...
    @overload
    def __init__(
        self: NodeContextVar[VisitorT, N, T, _FalseType, *Args, Kwargs],  # pyright: ignore
        node_types: NodeTypes[N],
        get_value: GetValue[VisitorT, N, T, *Args, Kwargs],
        *,
        pred: GetValue[VisitorT, N, bool, *Args, Kwargs] | None = None,
    ): ...
    #
    @property
    def stack_name(self) -> str: ...
    #
    @contextmanager
    def push(
        self, instance: ast.NodeVisitor, node: ast.AST, match_result: MatchResult
    ) -> Iterator[None]: ...
    #
    @overload
    def __get__(
        self: NodeContextVar[VisitorT, N, T, _TrueType, *Args, Kwargs],
        instance: VisitorT,
        owner: type[VisitorT],
    ) -> T: ...
    @overload
    def __get__(
        self: NodeContextVar[VisitorT, N, T, _FalseType, *Args, Kwargs],
        instance: VisitorT,
        owner: type[VisitorT],
    ) -> T | None: ...
    #
    def get_hook(self) -> Hook: ...

@overload
def node_context[
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
    T,
    *Args,
    Kwargs: dict,
](
    *node_types: type[N],

    pred: GetValue[VisitorT, N, bool, *Args, Kwargs] | None = None,
) -> Callable[
    [GetValue[VisitorT, N, T, *Args, Kwargs]],
    NodeContextVar[VisitorT, N, T, _FalseType, *Args, Kwargs],
]: ...
@overload
def node_context[
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
    T,
    *Args,
    Kwargs: dict,
](
    *node_types: type[N],
    default: T,
    pred: GetValue[VisitorT, N, bool, *Args, Kwargs] | None = None,
) -> Callable[
    [GetValue[VisitorT, N, T, *Args, Kwargs]],
    NodeContextVar[VisitorT, N, T, _TrueType, *Args, Kwargs],
]: ...
@overload
def node_context[
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
    T,
    *Args,
    Kwargs: dict,
](
    *node_types: type[N],
    default_factory: Callable[[], T],
    pred: GetValue[VisitorT, N, bool, *Args, Kwargs] | None = None,
) -> Callable[
    [GetValue[VisitorT, N, T, *Args, Kwargs]],
    NodeContextVar[VisitorT, N, T, _TrueType, *Args, Kwargs],
]: ...
