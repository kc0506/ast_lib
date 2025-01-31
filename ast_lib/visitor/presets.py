# Synced by scripts/sync_visitor_with_pyi.py with presets.proto.pyi
# Synced by scripts/sync_visitor_with_pyi.py with presets.proto.pyi
# TODO: indent level
# TODO: qualname

from __future__ import annotations
import ast
from contextlib import contextmanager
from typing import Any, Callable
from ..pattern import MatchResult
from .core import Hook, HookMode, HookProvider
from .utils import DescriptorHelper, invoke_callback

type NodeTypes[N] = type[N] | tuple[type[N], ...]
type VisitHook[VisitorT: ast.NodeVisitor, N: ast.AST] = (
    Callable[[VisitorT, N], Any] | Callable[[VisitorT, N, MatchResult], Any]
)


class ParentMap(HookProvider, DescriptorHelper):
    def get_hook(self) -> Hook:
        def setup(instance: ast.NodeVisitor) -> None:
            self._set_attr(instance, "current_node", None)
            self._set_attr(instance, "parent_map", dict())

        @contextmanager
        def func(instance: ast.NodeVisitor, node: ast.AST, _: MatchResult):
            prev = self._get_attr(instance, "current_node")
            self._set_attr(
                instance,
                "parent_map",
                self._get_attr(instance, "parent_map") | {node: prev},
            )
            yield
            self._set_attr(instance, "current_node", node)

        return Hook((ast.AST,), "wrap", func, setup)

    def __get__(
        self, instance: ast.NodeVisitor, owner: type[ast.NodeVisitor]
    ) -> dict[ast.AST, ast.AST | None]:
        return self._get_attr(instance, "parent_map")


class PureNodeVisitHook[
    VisitorT: ast.NodeVisitor,
    N: ast.AST,
](HookProvider, DescriptorHelper):
    def __init__(
        self,
        node_types: NodeTypes[N],
        func: Callable[[VisitorT, N], Any] | Callable[[VisitorT], Any],
        mode: HookMode = "before",
        before: tuple[str, ...] = (),
        after: tuple[str, ...] = (),
    ):
        if not isinstance(node_types, tuple):
            node_types = (node_types,)

        def hook_func(
            instance: ast.NodeVisitor, node: ast.AST, match_result: MatchResult
        ):
            return invoke_callback(func, instance, node, match_result=match_result)

        self.hook = Hook(
            node_types, mode, hook_func, setup=None, before=before, after=after
        )

    def get_hook(self) -> Hook:
        return self.hook


# todo: before, after, wrap
# todo:? match field (create overloads for every ast class)


def pure_visit[VisitorT: ast.NodeVisitor, N: ast.AST, *Args, Kwargs: dict](
    *node_types: type[N],
    mode: HookMode = "before",
    before: tuple[str, ...] = (),
    after: tuple[str, ...] = (),
) -> Callable[[VisitHook[VisitorT, N]], PureNodeVisitHook[VisitorT, N]]:
    #

    def wrapper(func: Callable[..., Any]) -> Any:
        return PureNodeVisitHook(node_types, func, mode, before, after)

    return wrapper
