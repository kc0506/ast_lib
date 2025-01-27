import ast
from typing import Callable, Generator, Literal, TypedDict, Unpack

from .core import Hook, HookProvider
from .utils import DescriptorHelper

type ReducerHookMode = Literal["before", "after"]

type NodeTypes[N] = type[N] | tuple[type[N], ...]
type InitialValue[T] = Callable[[], T] | T
type GetValue[VisitorT, N, T] = Callable[[N], T] | Callable[[VisitorT, N], T]
type Reducer[VisitorT, N, T] = Callable[[T, N], T] | Callable[[VisitorT, T, N], T]

# [proto] Expand these types in generated .pyi file
__expand__ = (
    NodeTypes,
    InitialValue,
    GetValue,
    Reducer,
)

class PartialReducerOptions(TypedDict, total=False):
    mode: ReducerHookMode
    before: tuple[str, ...]
    patterns: list[str] | None

class ReducerOptions(TypedDict, total=True):
    mode: ReducerHookMode
    before: tuple[str, ...]
    patterns: list[str] | None

# ------------------------------- Base Reducer ------------------------------- #

class NodeReducer[
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
    T,
](HookProvider, DescriptorHelper):
    def __init__(
        self,
        node_types: NodeTypes[N],
        initial_value: InitialValue[T],
        reducer: Reducer[VisitorT, N, T],
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
    initial_value: InitialValue[T],
    #
    **kwargs: Unpack[PartialReducerOptions],
    #
    # return_type: type[T] | None = None,  # only used for type hint
) -> Callable[
    [Reducer[Visitor, N, T]],
    NodeReducer[Visitor, N, T],
]: ...

# ----------------------------------- List ----------------------------------- #

class NodeListCollector[
    Visitor: ast.NodeVisitor,
    N: ast.AST,
    Value,
](NodeReducer[Visitor, N, list[Value]]):
    def __init__(
        self,
        node_types: NodeTypes[N],
        get_value: GetValue[Visitor, N, Generator[Value] | Value],
        #
        **kwargs: Unpack[PartialReducerOptions],
    ): ...

def nodelist_collector[Visitor: ast.NodeVisitor, N: ast.AST, Value](
    *node_types: type[N],
    #
    **kwargs: Unpack[PartialReducerOptions],
) -> Callable[
    [GetValue[Visitor, N, Generator[Value] | Value]],
    NodeListCollector[Visitor, N, Value],
]: ...

# ------------------------------------ Set ----------------------------------- #

class NodeSetCollector[
    Visitor: ast.NodeVisitor,
    N: ast.AST,
    Value,
](NodeReducer[Visitor, N, set[Value]]):
    def __init__(
        self,
        node_types: NodeTypes[N],
        get_value: GetValue[Visitor, N, Generator[Value] | Value],
        #
        **kwargs: Unpack[PartialReducerOptions],
    ): ...

def nodeset_collector[Visitor: ast.NodeVisitor, N: ast.AST, Value](
    *node_types: type[N],
    #
    **kwargs: Unpack[PartialReducerOptions],
) -> Callable[
    [GetValue[Visitor, N, Generator[Value] | Value]],
    NodeSetCollector[Visitor, N, Value],
]: ...

# ------------------------------------ Map ----------------------------------- #

class NodeMapCollector[
    Visitor: ast.NodeVisitor,
    N: ast.AST,
    Key,
    Value,
](NodeReducer[Visitor, N, dict[Key, Value]]):
    def __init__(
        self,
        node_types: NodeTypes[N],
        get_value: GetValue[Visitor, N, Value],
        #
        get_key: GetValue[Visitor, N, Key] = lambda node: node,
        #
        **kwargs: Unpack[PartialReducerOptions],
    ): ...

def nodemap_collector[Visitor: ast.NodeVisitor, N: ast.AST, Key, Value](
    *node_types: type[N],
    #
    get_key: GetValue[Visitor, N, Key] = lambda node: node,
    #
    **kwargs: Unpack[PartialReducerOptions],
) -> Callable[
    [GetValue[Visitor, N, Value]],
    NodeMapCollector[Visitor, N, Key, Value],
]: ...
