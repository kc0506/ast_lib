""""""

# TODO: type stub?
# TODO: add_visit_hook, node_context, node_collector, pure_visit
# TODO: partially context, i.e. context for part of children
# TODO: yield every children
# TODO: temporarily override visit_XX
# TODO: default order: before, wrap-enter, after, wrap-exit
# TODO: name cannot be visit_XX
# TODO: sibling
# TODO: per-invoke context

from __future__ import annotations

import ast
from abc import abstractmethod
from collections import defaultdict
from typing import (
    Any,
    Callable,
    ClassVar,
    ContextManager,
    Literal,
    NamedTuple,
    Protocol,
    runtime_checkable,
)

from pydantic import Field
from pydantic.dataclasses import dataclass

from ast_lib.pattern import parse_pattern

from .. import nodes
from .exception import SkipVisit

type HookMode = Literal["before", "after", "wrap"]


@dataclass
class Hook:
    node_types: tuple[type[ast.AST], ...]
    mode: HookMode
    func: Callable[[ast.NodeVisitor, ast.AST], Any]  # TODO: fix __name__
    #
    setup: Callable[[ast.NodeVisitor], None] | None = None
    before: tuple[str, ...] = ()  # TODO: just single `deps`?
    after: tuple[str, ...] = ()
    patterns: list[str] = Field(default_factory=list)  # TODO: type hint for decorators
    #
    name: str | None = Field(init=False)


# TODO: single or multiple? parent map?
@runtime_checkable
class HookProvider(Protocol):
    @abstractmethod
    def get_hook(self) -> Hook: ...


class HookEvent(NamedTuple):
    type: Literal["enter", "exit"]
    name: str


def solve_hook_order(hooks: dict[str, Hook]) -> list[HookEvent]:
    # topological sort
    # ! 'before' cannot be after 'after', vice versa

    def check_hook_name(name: str) -> None:
        if name not in hooks:
            raise ValueError(f"Hook name {name} is not defined")

    def check_valid(cur_name: str, child_name: str) -> None:
        cur_hook = hooks[cur_name]
        child_hook = hooks[child_name]
        if cur_hook.mode == "after" and child_hook.mode == "before":
            raise ValueError(
                f"Hook {cur_name} has mode `after` but its child {child_name} has mode `before`"
            )

    children_map: dict[str, list[str]] = defaultdict(list)
    for name, hook in hooks.items():
        for before in hook.before:
            check_hook_name(before)
            children_map[name].append(before)
        for after in hook.after:
            check_hook_name(after)
            children_map[after].append(name)

    for name, children in children_map.items():
        for child in children:
            check_valid(child, name)

    status_map: dict[str, Literal["white", "gray", "black"]] = {
        name: "white" for name in hooks
    }
    reversed_hooks: list[HookEvent] = []

    def dfs(cur_name: str, path: list[str]) -> None:
        if status_map[cur_name] == "black":
            return
        if status_map[cur_name] == "gray":
            assert path.count(cur_name) == 1
            cycle_st = path.index(cur_name)
            # error_msg = "\n".join(f"{name}->" for name in path[cycle_st:]) + cur_name
            error_msg = " -> ".join(path[cycle_st:] + [cur_name])
            raise ValueError(f"Cycle detected in hooks: {cur_name}\n{error_msg}")

        status_map[cur_name] = "gray"

        for child in children_map[cur_name]:
            dfs(child, path + [cur_name])

        status_map[cur_name] = "black"
        match hooks[cur_name].mode:
            case "wrap":
                reversed_hooks.append(HookEvent(type="exit", name=cur_name))
                reversed_hooks.append(HookEvent(type="enter", name=cur_name))
            case "before":
                reversed_hooks.append(HookEvent(type="enter", name=cur_name))
            case "after":
                reversed_hooks.append(HookEvent(type="exit", name=cur_name))

    # if no edges, the order will be preserved
    for name in reversed(hooks):
        dfs(name, [])

    # while the returned hooks have `enter` and `exit` interleaved, the order are preserved within each type
    return reversed_hooks[::-1]


class BaseNodeVisitor(ast.NodeVisitor):
    __visit_hook_map__: ClassVar[dict[str, Hook]] = {}
    __visit_hook_events__: ClassVar[list[HookEvent]] = []

    def __init_subclass__(cls) -> None:
        # TODO: should this be reversed?
        hooks_map: dict[str, Hook] = {}
        for base in cls.__mro__:
            for obj_name, obj in base.__dict__.items():
                if isinstance(obj, HookProvider):
                    hooks_map[obj_name] = obj.get_hook()

        cls.__visit_hook_map__ = hooks_map
        cls.__visit_hook_events__ = solve_hook_order(hooks_map)

        return super().__init_subclass__()

    def __init__(self) -> None:
        for hook in self.__visit_hook_map__.values():
            if hook.setup is not None:
                hook.setup(self)

    def visit(self, node: ast.AST) -> ast.AST | None:
        # TODO handle return value
        # order: before, wrap-enter, wrap-exit, after
        # called by time added

        visit_events = self.__visit_hook_events__
        enter_names = [hook.name for hook in visit_events if hook.type == "enter"]
        exit_names = [hook.name for hook in visit_events if hook.type == "exit"]
        wrap_contexts: dict[str, ContextManager] = {}

        parsed_pattern_cache: dict[tuple[str, str], nodes.AST] = {}

        for name in enter_names:
            hook = self.__visit_hook_map__[name]
            if not isinstance(node, hook.node_types):
                continue

            all_matched = True
            args = []
            kwargs = {}
            for pattern in hook.patterns:
                pattern_node = parsed_pattern_cache.get(
                    (name, pattern), parse_pattern(pattern)
                )
                if not (result := pattern_node.match(node)):
                    all_matched = False
                    break

                args.extend(result.groups[:-1])
                kwargs.update(result.groups[-1])

            if not all_matched:
                continue

            try:
                if hook.mode == "before":
                    hook.func(self, node)
                elif hook.mode == "wrap":
                    ctx = hook.func(self, node, *args, **kwargs)
                    if not isinstance(ctx, ContextManager):
                        raise ValueError(
                            f"Hook {hook} with mode 'wrap' must return a context manager"
                        )

                    ctx.__enter__()
                    wrap_contexts[name] = ctx
                else:
                    raise ValueError(
                        f"Invalid hook mode for event `enter`: {hook.mode}"
                    )
            except SkipVisit as e:
                # TODO
                return e.node

        ret = super().visit(node)

        for name in exit_names:
            hook = self.__visit_hook_map__[name]
            if not isinstance(node, hook.node_types):
                continue
            if hook.mode == "after":
                hook.func(self, node)
            elif hook.mode == "wrap":
                ctx = wrap_contexts[name]
                ctx.__exit__(None, None, None)
            else:
                raise ValueError(f"Invalid hook mode for event `exit`: {hook.mode}")

        return ret
