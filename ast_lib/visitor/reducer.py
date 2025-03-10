# Synced by scripts/sync_visitor_with_pyi.py with reducer.proto.pyi
# TODO: multiple map
# TODO: return key-value pair in map collector
# TODO: visitor_type, return_type

from __future__ import annotations
import ast
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generator,
    Literal,
    TypedDict,
    Unpack,
    cast,
)
from .core import Hook, HookProvider
from .exception import SkipNode
from .utils import DescriptorHelper, invoke_callback

if TYPE_CHECKING:
    from ..pattern import MatchResult, MatchTypeHint

# ---------------------------------------------------------------------------- #
#                         Types (overlapped with .pyi)                         #
# ---------------------------------------------------------------------------- #

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
)


class PartialReducerOptions[
    N: ast.AST,
    *Args,
    Kwargs: dict,
](TypedDict, total=False):
    mode: ReducerHookMode
    before: tuple[str, ...]
    pattern: str | None
    match_type_hint: MatchTypeHint[N, *Args, Kwargs]


class ReducerOptions[
    N: ast.AST,
    *Args,
    Kwargs: dict,
](TypedDict, total=True):
    mode: ReducerHookMode
    before: tuple[str, ...]
    pattern: str | None
    match_type_hint: MatchTypeHint[N, *Args, Kwargs]


# ---------------------------------------------------------------------------- #
#                                Implementation                                #
# ---------------------------------------------------------------------------- #

_DEFAULT_OPTIONS: ReducerOptions = {
    "mode": "before",
    "before": (),
    "pattern": None,
    "match_type_hint": cast(Any, None),
}

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
        **kwargs: Unpack[PartialReducerOptions],
        #
        #
        # visitor_type: type[VisitorT] | None = None,  # only used for type hint
    ):
        if not isinstance(node_types, tuple):
            node_types = (node_types,)
        self.node_types = node_types
        self.initial_value = initial_value
        self.reducer = reducer
        self.options = kwargs

    def __get__(self, instance: VisitorT, owner: type[VisitorT]) -> T:
        return self._get_attr(instance, "value")

    def get_hook(self) -> Hook:
        def setup(instance: ast.NodeVisitor) -> None:
            value: T
            if callable(self.initial_value):
                value = cast(T, self.initial_value())
            else:
                value = cast(T, self.initial_value)
            self._set_attr(instance, "value", value)

        def func(instance: ast.NodeVisitor, node: ast.AST, match_result: MatchResult):
            prev_value = self._get_attr(instance, "value")
            try:
                value = invoke_callback(
                    self.reducer, instance, prev_value, node, match_result=match_result
                )
            except SkipNode:
                return
            self._set_attr(instance, "value", value)

        return Hook(
            self.node_types,
            self.options.get("mode", _DEFAULT_OPTIONS["mode"]),
            func,
            setup=setup,
            before=self.options.get("before", _DEFAULT_OPTIONS["before"]),
            pattern=self.options.get("pattern", _DEFAULT_OPTIONS["pattern"]),
        )


def node_reducer[VisitorT: ast.NodeVisitor, N: ast.AST, T, *Args, Kwargs: dict](
    *node_types: type[N],
    initial_value: InitialValue[T],
    **kwargs: Unpack[PartialReducerOptions],
    # return_type: type[T]
    # | None = None,  # only used for type hint
) -> Callable[
    [Reducer[VisitorT, N, T, *Args, Kwargs]], NodeReducer[VisitorT, N, T, *Args, Kwargs]
]:
    def decorator(reducer: Reducer[VisitorT, N, T, *Args, Kwargs]):
        return NodeReducer[VisitorT, N, T, *Args, Kwargs](
            node_types, initial_value, reducer, **kwargs
        )

    return decorator


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
        **kwargs: Unpack[PartialReducerOptions],
        #
    ):
        def reducer(
            instance: VisitorT, acc: list[Value], node: N, match_result: MatchResult
        ) -> list[Value]:
            value = invoke_callback(
                get_value, instance, node, match_result=match_result
            )
            if isinstance(value, Generator):
                return acc + list(value)
            return acc + [value]

        super().__init__(node_types, lambda: list(), reducer, **kwargs)


# TODO: add init
# TODO: can we pass prev_value here?
# TODO: combine with context


def nodelist_collector[
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
    Value,
    *Args,
    Kwargs: dict,
](
    *node_types: type[N],
    **kwargs: Unpack[PartialReducerOptions],
    #
) -> Callable[
    [GetValue[VisitorT, N, Generator[Value] | Value, *Args, Kwargs]],
    NodeListCollector[VisitorT, N, Value, *Args, Kwargs],
]:
    def decorator(
        # TODO
        get_value: GetValue[VisitorT, N, Value | Generator[Value], *Args, Kwargs],
    ):
        return NodeListCollector(node_types, get_value, **kwargs)

    return decorator


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
        **kwargs: Unpack[PartialReducerOptions],
        #
    ):
        def reducer(
            instance: VisitorT, acc: set[Value], node: N, match_result: MatchResult
        ) -> set[Value]:
            value = invoke_callback(
                get_value, instance, node, match_result=match_result
            )
            if isinstance(value, Generator):
                return acc | set(value)
            return acc | {value}

        super().__init__(node_types, lambda: set(), reducer, **kwargs)


def nodeset_collector[
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
    Value,
    *Args,
    Kwargs: dict,
](
    *node_types: type[N],
    **kwargs: Unpack[PartialReducerOptions],
    #
) -> Callable[
    [GetValue[VisitorT, N, Generator[Value] | Value, *Args, Kwargs]],
    NodeSetCollector[VisitorT, N, Value, *Args, Kwargs],
]:
    def decorator(
        get_value: GetValue[VisitorT, N, Generator[Value] | Value, *Args, Kwargs],
    ):
        return NodeSetCollector(node_types, get_value, **kwargs)

    return decorator


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
        get_key: GetValue[VisitorT, N, Key, *Args, Kwargs] = lambda node: node,
        **kwargs: Unpack[PartialReducerOptions],
        # default_value: Value,
        #
        # type: ignore
        #
    ):
        def reducer(
            instance: VisitorT,
            acc: dict[Key, Value],
            node: N,
            match_result: MatchResult,
        ) -> dict[Key, Value]:
            key = invoke_callback(get_key, instance, node, match_result=match_result)
            value = invoke_callback(
                get_value, instance, node, match_result=match_result
            )
            return acc | {key: value}

        super().__init__(node_types, lambda: dict(), reducer, **kwargs)


def nodemap_collector[
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
    Key,
    Value,
    *Args,
    Kwargs: dict,
](
    *node_types: type[N],
    get_key: GetValue[VisitorT, N, Key, *Args, Kwargs] = lambda node: node,
    **kwargs: Unpack[PartialReducerOptions],
    #
    # type: ignore
    #
) -> Callable[
    [GetValue[VisitorT, N, Value, *Args, Kwargs]],
    NodeMapCollector[VisitorT, N, Key, Value, *Args, Kwargs],
]:
    def decorator(get_value: GetValue[VisitorT, N, Value, *Args, Kwargs]):
        return NodeMapCollector(node_types, get_value, get_key, **kwargs)

    return decorator
