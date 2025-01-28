from __future__ import annotations

# TODO: update context without pushing


import ast
from contextlib import contextmanager
from typing import (
    Callable,
    Iterator,
    cast,
)

from .core import Hook, HookProvider
from .exception import SkipNode
from .utils import DescriptorHelper, call_with_optional_self

# ! Not used in pyi because it doesn't work, but it make us much concise here
type NodeTypes[N] = type[N] | tuple[type[N], ...]
type GetValue[V, N, T] = Callable[[N], T] | Callable[[V, N], T]

# TODO: use protocol for typing


class NodeContextVar[Visitor: ast.NodeVisitor, N: ast.AST, T](
    HookProvider, DescriptorHelper
):
    def __init__(
        self,
        node_types: NodeTypes[N],
        get_value: GetValue[Visitor, N, T],
        #
        pred: GetValue[Visitor, N, bool] | None = None,
        default: T | None = None,
        default_factory: Callable[[], T] | None = None,
    ):
        if not isinstance(node_types, tuple):
            node_types = (node_types,)

        self.node_types = node_types
        self.get_value = get_value

        # TODO: add to pyi
        self.pred = pred or (lambda _: True)
        self.default = default
        self.default_factory = default_factory

        self.name = None

    @contextmanager
    def push(self, instance: ast.NodeVisitor, node: ast.AST) -> Iterator[None]:
        stack: list[T] = self._get_attr(instance, "stack")

        try:
            if not call_with_optional_self(self.pred, instance, node):
                raise SkipNode(node)
            res = call_with_optional_self(self.get_value, instance, node)
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
        def hook(instance: ast.NodeVisitor, node: ast.AST):
            return self.push(instance, node)

        return Hook(self.node_types, "wrap", hook, setup)


def node_context[Visitor: ast.NodeVisitor, N: ast.AST, T](
    *node_types: type[N],
    #
    pred: GetValue[Visitor, N, bool] | None = None,
    default: T | None = None,
    default_factory: Callable[[], T] | None = None,
):
    def decorator(func: GetValue[Visitor, N, T]):
        return NodeContextVar(
            node_types,
            func,
            pred=pred,
            default=default,
            default_factory=default_factory,
        )

    return decorator
