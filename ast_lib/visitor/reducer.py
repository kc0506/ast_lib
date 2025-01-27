from __future__ import annotations

import ast
from typing import Callable, Generator, Literal, TypedDict, Unpack, cast

from .core import Hook, HookProvider
from .exception import SkipNode
from .utils import DescriptorHelper, call_with_optional_self

# ! Not used in pyi
type NodeTypes[N] = type[N] | tuple[type[N], ...]
type GetValue[VisitorT, N, T] = Callable[[N], T] | Callable[[VisitorT, N], T]
type Reducer[VisitorT, N, T] = Callable[[T, N], T] | Callable[[VisitorT, T, N], T]


type ReducerHookMode = Literal["before", "after"]


class PartialReducerOptions(TypedDict, total=False):
    mode: ReducerHookMode
    before: tuple[str, ...]
    patterns: list[str] | None


class ReducerOptions(TypedDict, total=True):
    mode: ReducerHookMode
    before: tuple[str, ...]
    patterns: list[str] | None


_DEFAULT_OPTIONS: ReducerOptions = {
    "mode": "before",
    "before": (),
    "patterns": None,
}


# TODO: raise error
# TODO: Use TypedDict?
class NodeReducer[VisitorT: ast.NodeVisitor, N: ast.AST, T](
    HookProvider, DescriptorHelper
):
    def __init__(
        self,
        node_types: NodeTypes[N],
        initial_value: Callable[[], T] | T,
        reducer: Callable[..., T],
        #
        **kwargs: Unpack[PartialReducerOptions],
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

        def func(instance: ast.NodeVisitor, node: ast.AST):
            prev_value = self._get_attr(instance, "value")
            try:
                value = call_with_optional_self(
                    self.reducer, instance, prev_value, node
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
            patterns=self.options.get("patterns", _DEFAULT_OPTIONS["patterns"]) or [],
        )


def node_reducer[Visitor: ast.NodeVisitor, N: ast.AST, T](
    *node_types: type[N],
    initial_value: Callable[[], T] | T,
    # return_type: type[T]
    # | None = None,  # only used for type hint
    **kwargs: Unpack[PartialReducerOptions],
):
    def decorator(reducer: Reducer[Visitor, N, T]):
        return NodeReducer[Visitor, N, T](node_types, initial_value, reducer, **kwargs)

    return decorator


class NodeListCollector[Visitor: ast.NodeVisitor, N: ast.AST, Value](
    NodeReducer[Visitor, N, list[Value]]
):
    def __init__(
        self,
        node_types: tuple[type[N], ...],
        get_value: GetValue[Visitor, N, Value | Generator[Value]],
        #
        **kwargs: Unpack[PartialReducerOptions],
    ):
        def reducer(instance: Visitor, acc: list[Value], node: N) -> list[Value]:
            value = call_with_optional_self(get_value, instance, node)
            if isinstance(value, Generator):
                return acc + list(value)
            return acc + [value]

        super().__init__(
            node_types,
            lambda: list(),
            reducer,
            **kwargs,
        )


# TODO: add init
# TODO: can we pass prev_value here?
# TODO: combine with context
def nodelist_collector[Visitor: ast.NodeVisitor, N: ast.AST, Value](
    *node_types: type[N],
    #
    **kwargs: Unpack[PartialReducerOptions],
):
    def decorator(
        get_value: GetValue[Visitor, N, Value | Generator[Value]],  # TODO
    ):
        return NodeListCollector(node_types, get_value, **kwargs)

    return decorator


class NodeSetCollector[Visitor: ast.NodeVisitor, N: ast.AST, Value](
    NodeReducer[Visitor, N, set[Value]]
):
    def __init__(
        self,
        node_types: tuple[type[N], ...],
        get_value: GetValue[Visitor, N, Value],
        #
        **kwargs: Unpack[PartialReducerOptions],
    ):
        super().__init__(
            node_types,
            lambda: set(),
            lambda instance, acc, node: acc
            | {call_with_optional_self(get_value, instance, node)},
            **kwargs,
        )


def nodeset_collector[Visitor: ast.NodeVisitor, N: ast.AST, Value](
    *node_types: type[N],
    #
    **kwargs: Unpack[PartialReducerOptions],
):
    def decorator(get_value: GetValue[Visitor, N, Value]):
        return NodeSetCollector(node_types, get_value, **kwargs)

    return decorator


class NodeMapCollector[Visitor: ast.NodeVisitor, N: ast.AST, Key, Value](
    NodeReducer[Visitor, N, dict[Key, Value]]
):
    def __init__(
        self,
        node_types: tuple[type[N], ...],
        # default_value: Value,
        get_value: GetValue[Visitor, N, Value],
        #
        get_key: GetValue[Visitor, N, Key] = lambda node: node,  # type: ignore
        #
        **kwargs: Unpack[PartialReducerOptions],
    ):
        def reducer(
            instance: Visitor, acc: dict[Key, Value], node: N
        ) -> dict[Key, Value]:
            key = call_with_optional_self(get_key, instance, node)
            value = call_with_optional_self(get_value, instance, node)
            return acc | {key: value}

        super().__init__(
            node_types,
            lambda: dict(),
            reducer,
            **kwargs,
        )


def nodemap_collector[Visitor: ast.NodeVisitor, N: ast.AST, Key, Value](
    *node_types: type[N],
    #
    get_key: GetValue[Visitor, N, Key] = lambda node: node,  # type: ignore
    #
    **kwargs: Unpack[PartialReducerOptions],
):
    def decorator(get_value: GetValue[Visitor, N, Value]):
        return NodeMapCollector(node_types, get_value, get_key, **kwargs)

    return decorator
