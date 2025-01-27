import ast
from typing import Callable, Generator, Literal, TypedDict, Unpack
from .core import Hook, HookProvider
from .utils import DescriptorHelper

type ReducerHookMode = Literal["before", "after"]
# [proto] Expand these types in generated .pyi file

class PartialReducerOptions(TypedDict, total=False):
    mode: ReducerHookMode
    before: tuple[str, ...]
    patterns: list[str] | None

class ReducerOptions(TypedDict, total=True):
    mode: ReducerHookMode
    before: tuple[str, ...]
    patterns: list[str] | None

# ------------------------------- Base Reducer ------------------------------- #

class NodeReducer[VisitorT: ast.NodeVisitor, N: ast.AST, T](
    HookProvider, DescriptorHelper
):
    def __init__(
        self,
        node_types: type[N] | tuple[type[N], ...],
        initial_value: Callable[[], T] | T,
        reducer: Callable[[T, N], T] | Callable[[VisitorT, T, N], T],
        #
        **kwargs: Unpack[PartialReducerOptions],
        #
        # visitor_type: type[VisitorT] | None = None,  # only used for type hint
    ): ...
    def __get__(self, instance: VisitorT, owner: type[VisitorT]) -> T: ...
    def get_hook(self) -> Hook: ...

def node_reducer[Visitor: ast.NodeVisitor, N: ast.AST, T](
    # This do not need union
    *node_types: type[N],
    initial_value: Callable[[], T] | T,
    #
    **kwargs: Unpack[PartialReducerOptions],
    #
    # return_type: type[T] | None = None,  # only used for type hint
) -> Callable[
    [Callable[[T, N], T] | Callable[[Visitor, T, N], T]], NodeReducer[Visitor, N, T]
]: ...

# ----------------------------------- List ----------------------------------- #

class NodeListCollector[Visitor: ast.NodeVisitor, N: ast.AST, Value](
    NodeReducer[Visitor, N, list[Value]]
):
    def __init__(
        self,
        node_types: type[N] | tuple[type[N], ...],
        get_value: Callable[[N], Generator[Value] | Value]
        | Callable[[Visitor, N], Generator[Value] | Value],
        #
        **kwargs: Unpack[PartialReducerOptions],
    ): ...

def nodelist_collector[Visitor: ast.NodeVisitor, N: ast.AST, Value](
    *node_types: type[N],
    #
    **kwargs: Unpack[PartialReducerOptions],
) -> Callable[
    [
        Callable[[N], Generator[Value] | Value]
        | Callable[[Visitor, N], Generator[Value] | Value]
    ],
    NodeListCollector[Visitor, N, Value],
]: ...

# ------------------------------------ Set ----------------------------------- #

class NodeSetCollector[Visitor: ast.NodeVisitor, N: ast.AST, Value](
    NodeReducer[Visitor, N, set[Value]]
):
    def __init__(
        self,
        node_types: type[N] | tuple[type[N], ...],
        get_value: Callable[[N], Generator[Value] | Value]
        | Callable[[Visitor, N], Generator[Value] | Value],
        #
        **kwargs: Unpack[PartialReducerOptions],
    ): ...

def nodeset_collector[Visitor: ast.NodeVisitor, N: ast.AST, Value](
    *node_types: type[N],
    #
    **kwargs: Unpack[PartialReducerOptions],
) -> Callable[
    [
        Callable[[N], Generator[Value] | Value]
        | Callable[[Visitor, N], Generator[Value] | Value]
    ],
    NodeSetCollector[Visitor, N, Value],
]: ...

# ------------------------------------ Map ----------------------------------- #

class NodeMapCollector[Visitor: ast.NodeVisitor, N: ast.AST, Key, Value](
    NodeReducer[Visitor, N, dict[Key, Value]]
):
    def __init__(
        self,
        node_types: type[N] | tuple[type[N], ...],
        get_value: Callable[[N], Value] | Callable[[Visitor, N], Value],
        #
        get_key: Callable[[N], Key] | Callable[[Visitor, N], Key] = lambda node: node,
        #
        **kwargs: Unpack[PartialReducerOptions],
    ): ...

def nodemap_collector[Visitor: ast.NodeVisitor, N: ast.AST, Key, Value](
    *node_types: type[N],
    #
    get_key: Callable[[N], Key] | Callable[[Visitor, N], Key] = lambda node: node,
    #
    **kwargs: Unpack[PartialReducerOptions],
) -> Callable[
    [Callable[[N], Value] | Callable[[Visitor, N], Value]],
    NodeMapCollector[Visitor, N, Key, Value],
]: ...
