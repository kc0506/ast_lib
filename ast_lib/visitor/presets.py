""""""

# TODO: indent level

from __future__ import annotations

import ast
from contextlib import contextmanager
from typing import (
    Any,
    Callable,
)

from .core import Hook, HookMode, HookProvider
from .utils import DescriptorHelper


class ParentMap(HookProvider, DescriptorHelper):
    def get_hook(self) -> Hook:
        def setup(instance: ast.NodeVisitor) -> None:
            self._set_attr(instance, "current_node", None)
            self._set_attr(instance, "parent_map", dict())

        @contextmanager
        def func(instance: ast.NodeVisitor, node: ast.AST):
            prev = self._get_attr(instance, "current_node")
            self._set_attr(
                instance,
                "parent_map",
                self._get_attr(instance, "parent_map") | {node: prev},
            )
            yield
            self._set_attr(instance, "current_node", node)

        return Hook(
            (ast.AST,),
            "wrap",
            func,
            setup,
        )

    def __get__(
        self, instance: ast.NodeVisitor, owner: type[ast.NodeVisitor]
    ) -> dict[ast.AST, ast.AST | None]:
        return self._get_attr(instance, "parent_map")


class PureNodeVisitHook(HookProvider):
    def __init__(
        self,
        node_types: tuple[type[ast.AST], ...],
        func: Callable[[ast.NodeVisitor, ast.AST], Any],
        mode: HookMode = "before",
        #
        before: tuple[str, ...] = (),
        after: tuple[str, ...] = (),
    ):
        self.hook = Hook(
            node_types,
            mode,
            func,
            setup=None,
            before=before,
            after=after,
        )

    def get_hook(self) -> Hook:
        return self.hook


# todo: before, after, wrap
# todo:? match field (create overloads for every ast class)
def pure_visit(
    *node_types: type[ast.AST],
    mode: HookMode = "before",
    #
    before: tuple[str, ...] = (),
    after: tuple[str, ...] = (),
) -> Callable[[Callable[..., Any]], Any]:
    def wrapper(func: Callable[..., Any]) -> Any:
        return PureNodeVisitHook(node_types, func, mode, before, after)

    return wrapper
