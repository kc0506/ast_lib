import ast
from typing import Callable, Generator, Literal, TypedDict, Unpack

from ..match_pattern import MatchResult, MatchTypeHint
from .core import Hook, HookProvider
from .utils import DescriptorHelper

type ReducerHookMode = Literal["before", "after"]

type NodeTypes[N] = type[N] | tuple[type[N], ...]
type InitialValue[T] = Callable[[], T] | T
type GetValue[VisitorT, N: ast.AST, T, *Args, Kwargs: dict] = (
    Callable[[N], T]
    | Callable[[VisitorT, N], T]
    | Callable[[VisitorT, N, MatchResult[N, *Args, Kwargs]], T]
)
type Reducer[VisitorT, N: ast.AST, T, *Args, Kwargs: dict] = (
    Callable[[T, N], T]
    | Callable[[VisitorT, T, N], T]
    | Callable[[VisitorT, T, N, MatchResult[N, *Args, Kwargs]], T]
)  # ? Do we have to use protocol

# [proto] Expand these types in generated .pyi file
__expand__ = (
    NodeTypes,
    InitialValue,
    GetValue,
    Reducer,
)

class PartialReducerOptions[N: ast.AST, *Args, Kwargs: dict](TypedDict, total=False):
    mode: ReducerHookMode
    before: tuple[str, ...]
    pattern: str | None
    # This is generally not that useful because we have to type hint in decorated function either way
    match_type_hint: MatchTypeHint[N, *Args, Kwargs]

class ReducerOptions[N: ast.AST, *Args, Kwargs: dict](TypedDict, total=True):
    mode: ReducerHookMode
    before: tuple[str, ...]
    pattern: str | None
    match_type_hint: MatchTypeHint[N, *Args, Kwargs]

# ------------------------------- Base Reducer ------------------------------- #

class NodeReducer[
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
    T,
    *Args,
    Kwargs: dict,
](HookProvider, DescriptorHelper):
    def __init__(
        self,
        node_types: NodeTypes[N],
        initial_value: InitialValue[T],
        reducer: Reducer[VisitorT, N, T, *Args, Kwargs],
        #
        **kwargs: Unpack[PartialReducerOptions],
        #
        # visitor_type: type[VisitorT] | None = None,  # only used for type hint
    ): ...
    def __get__(self, instance: VisitorT, owner: type[VisitorT]) -> T: ...
    def get_hook(self) -> Hook: ...

def node_reducer[
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
    T,
    *Args,
    Kwargs: dict,
](
    # This do not need union
    *node_types: type[N],
    initial_value: InitialValue[T],
    #
    **kwargs: Unpack[PartialReducerOptions],
    #
    # return_type: type[T] | None = None,  # only used for type hint
) -> Callable[
    [Reducer[VisitorT, N, T, *Args, Kwargs]],
    NodeReducer[VisitorT, N, T, *Args, Kwargs],
]: ...

# ----------------------------------- List ----------------------------------- #

class NodeListCollector[
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
    Value,
    *Args,
    Kwargs: dict,
](NodeReducer[VisitorT, N, list[Value], *Args, Kwargs]):
    def __init__(
        self,
        node_types: NodeTypes[N],
        get_value: GetValue[VisitorT, N, Generator[Value] | Value, *Args, Kwargs],
        #
        **kwargs: Unpack[PartialReducerOptions],
    ): ...

def nodelist_collector[
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
    Value,
    *Args,
    Kwargs: dict,
](
    *node_types: type[N],
    #
    **kwargs: Unpack[PartialReducerOptions],
) -> Callable[
    [GetValue[VisitorT, N, Generator[Value] | Value, *Args, Kwargs]],
    NodeListCollector[VisitorT, N, Value, *Args, Kwargs],
]: ...

# ------------------------------------ Set ----------------------------------- #

class NodeSetCollector[
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
    Value,
    *Args,
    Kwargs: dict,
](NodeReducer[VisitorT, N, set[Value], *Args, Kwargs]):
    def __init__(
        self,
        node_types: NodeTypes[N],
        get_value: GetValue[VisitorT, N, Generator[Value] | Value, *Args, Kwargs],
        #
        **kwargs: Unpack[PartialReducerOptions],
    ): ...

def nodeset_collector[
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
    Value,
    *Args,
    Kwargs: dict,
](
    *node_types: type[N],
    #
    **kwargs: Unpack[PartialReducerOptions],
) -> Callable[
    [GetValue[VisitorT, N, Generator[Value] | Value, *Args, Kwargs]],
    NodeSetCollector[VisitorT, N, Value, *Args, Kwargs],
]: ...

# ------------------------------------ Map ----------------------------------- #

class NodeMapCollector[
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
    Key,
    Value,
    *Args,
    Kwargs: dict,
](NodeReducer[VisitorT, N, dict[Key, Value], *Args, Kwargs]):
    def __init__(
        self,
        node_types: NodeTypes[N],
        get_value: GetValue[VisitorT, N, Value, *Args, Kwargs],
        #
        get_key: GetValue[VisitorT, N, Key, *Args, Kwargs] = lambda node: node,
        #
        **kwargs: Unpack[PartialReducerOptions],
    ): ...

def nodemap_collector[
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
    Key,
    Value,
    *Args,
    Kwargs: dict,
](
    *node_types: type[N],
    #
    get_key: GetValue[VisitorT, N, Key, *Args, Kwargs] = lambda node: node,
    #
    **kwargs: Unpack[PartialReducerOptions],
) -> Callable[
    [GetValue[VisitorT, N, Value, *Args, Kwargs]],
    NodeMapCollector[VisitorT, N, Key, Value, *Args, Kwargs],
]: ...
