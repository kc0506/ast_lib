# Synced by scripts/sync_visitor_with_pyi.py with context.proto.pyi

from __future__ import annotations

# TODO: update context without pushing
# TODO: use protocol for typing

import ast
from contextlib import contextmanager
from typing import Callable, Iterator, Literal
from ..pattern import MatchResult
from .core import Hook, HookProvider
from .exception import SkipNode
from .utils import DescriptorHelper, invoke_callback

# ! Not used in pyi because it doesn't work, but it make us much concise here

type NodeTypes[N] = type[N] | tuple[type[N], ...]
type GetValue[VisitorT, N: ast.AST, T, *Args, Kwargs: dict] = (
    Callable[[N], T]
    | Callable[[VisitorT, N], T]
    | Callable[[VisitorT, N, MatchResult[N, *Args, Kwargs]], T]
)
type _TrueType = Literal[True]
type _FalseType = Literal[False]


class NodeContextVar[
    #
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
    T,
    _HasDefault: _TrueType | _FalseType,
    *Args,
    Kwargs: dict,
](HookProvider, DescriptorHelper):
    def __init__(
        self,
        node_types: NodeTypes[N],
        get_value: GetValue[VisitorT, N, T, *Args, Kwargs],
        *,
        # TODO: add to pyi
        default: T | None = None,
        default_factory: Callable[[], T] | None = None,
        pred: GetValue[VisitorT, N, bool, *Args, Kwargs] | None = None,
    ):
        if not isinstance(node_types, tuple):
            node_types = (node_types,)
        self.node_types = node_types
        self.get_value = get_value
        self.pred = pred or (lambda _: True)
        self.default = default
        self.default_factory = default_factory
        self.name = None

    @contextmanager
    def push(
        self, instance: ast.NodeVisitor, node: ast.AST, match_result: MatchResult
    ) -> Iterator[None]:
        stack: list[T] = self._get_attr(instance, "stack")
        try:
            if not invoke_callback(
                self.pred, instance, node, match_result=match_result
            ):
                raise SkipNode(node)
            res = invoke_callback(
                self.get_value, instance, node, match_result=match_result
            )
        except SkipNode:
            yield
            return
        stack.append(res)
        before_len = len(stack)
        yield
        assert len(stack) == before_len
        assert stack.pop() == res

    def __get__(
        self, instance: ast.NodeVisitor, owner: type[ast.NodeVisitor]
    ) -> T | None:
        stack = self._get_attr(instance, "stack")
        if len(stack) == 0:
            if self.default_factory is not None:
                return self.default_factory()
            return self.default
        return stack[-1]

    # def __set__(self, instance: ast.NodeVisitor, value: T) -> None:
    #     stack = self._get_attr(instance, "stack")
    #     if len(stack) == 0:
    #         raise ValueError("No context stack to set value")
    #     stack[-1] = value

    def get_hook(self) -> Hook:
        def setup(instance: ast.NodeVisitor) -> None:
            assert not self._has_attr(instance, "stack"), "stack already exists"
            self._set_attr(instance, "stack", [])

        # We have to use AST instead of N because callables are contravariant

        def hook(instance: ast.NodeVisitor, node: ast.AST, match: MatchResult):
            return self.push(instance, node, match)

        return Hook(self.node_types, "wrap", hook, setup)


def node_context[VisitorT: ast.NodeVisitor, N: ast.AST, T, *Args, Kwargs: dict](
    *node_types: type[N],
    #
    default: T | None = None,
    default_factory: Callable[[], T] | None = None,
    pred: GetValue[VisitorT, N, bool, *Args, Kwargs] | None = None,
):
    def decorator(func: GetValue[VisitorT, N, T, *Args, Kwargs]):
        return NodeContextVar(
            node_types,
            func,
            pred=pred,
            default=default,
            default_factory=default_factory,
        )

    return decorator


class ManualContextVar[
    VisitorT: ast.NodeVisitor,
    T,
](DescriptorHelper):
    def __init__(self, init: Callable[[], T] | T | None = None):
        self.init = init

    def __get__(
        self, instance: ast.NodeVisitor, owner: type[ast.NodeVisitor]
    ) -> T | None:
        stack: list[T] = self._set_attr_default(instance, "stack", [])
        if len(stack) == 0:
            if self.init is None:
                raise ValueError("No context stack to get value")
            if isinstance(self.init, Callable):
                return self.init()
            return self.init
        return stack[-1]

    def __set__(self, instance: ast.NodeVisitor, value: T) -> None:
        stack: list[T] = self._set_attr_default(instance, "stack", [])
        stack[-1] = value

    @contextmanager
    def push(self, instance: ast.NodeVisitor, value: T) -> Iterator[None]:
        stack: list[T] = self._get_attr(instance, "stack")
        before_len = len(stack)
        stack.append(value)
        yield
        assert len(stack) == before_len
        stack.pop()
