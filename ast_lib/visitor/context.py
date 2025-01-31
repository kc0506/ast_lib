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
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
    T,
    #
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
