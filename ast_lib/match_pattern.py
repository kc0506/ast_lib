""""""

# ! Note: there is only two possible types of list: AST or _Identifier

from __future__ import annotations

import ast
import io
import re

# from pydantic.dataclasses import dataclass
from dataclasses import dataclass
from typing import Any, Literal, cast, overload

from loguru import logger

from . import nodes
from .pattern import parse_pattern

logger.remove()


def debug_log(msg: str, depth: float):
    msg = re.sub(" at 0x[0-9a-fA-F]+>", ">", msg)
    logger.debug(f"{' ' * int(depth * 2)}{msg}")


def _match_field(
    field_pattern: Any, field_target: Any, depth: float, captures: dict[str | int, Any]
) -> bool:
    if isinstance(field_pattern, (nodes.Wildcard, nodes.WildcardId)):
        debug_log(f"Field {field_pattern} is wildcard, shortcut", depth)
        return True
    if isinstance(field_pattern, nodes.Capture):
        debug_log(f"Field {field_pattern} is capture, expand", depth)
        captures[field_pattern.name] = field_target
        return _match_field(field_pattern.pattern, field_target, depth + 1, captures)

    if isinstance(field_pattern, nodes.AST) or isinstance(field_target, ast.AST):
        debug_log(f"Not expected field type: {field_pattern} or {field_target}", depth)
        return False

    if isinstance(field_pattern, list):
        if len(field_pattern) != len(field_target):
            debug_log(f"Field {field_pattern} is list, length mismatch", depth)
            return False
        for p, t in zip(field_pattern, field_target):
            if not _match_field(p, t, depth, captures):
                debug_log(f"Field {field_pattern} is list, mismatch", depth)
                return False

        debug_log(f"Field {field_pattern} is list, match", depth)
        return True

    debug_log(f"Field {field_pattern} is not list, match", depth)
    return field_pattern == field_target


def _match_node(
    pattern_node: nodes.AST,
    target_node: ast.AST,
    depth: float,
    captures: dict[str | int, Any],
) -> bool:
    # assert isinstance(pattern_node, nodes.AST)
    # assert isinstance(target_node, ast.AST)

    debug_log(f"Matching {pattern_node} against {target_node}", depth)

    if isinstance(pattern_node, nodes.expr) and isinstance(target_node, ast.Expr):
        debug_log("Target is Expr, expand", depth)
        return _match_node(pattern_node, target_node.value, depth + 1, captures)
    if isinstance(pattern_node, nodes.Expr) and isinstance(target_node, ast.expr):
        debug_log("Pattern is Expr, expand", depth)
        return _match_node(pattern_node.value, target_node, depth + 1, captures)

    if isinstance(pattern_node, (nodes.Wildcard)):
        debug_log("Pattern is wildcard or capture, shortcut", depth)
        return True

    if isinstance(pattern_node, nodes.WildcardId):
        # raise ValueError(f"WildcardId {pattern_node} is not expected")
        debug_log("WildcardId is not expected", depth)
        return False

    if isinstance(pattern_node, nodes.Capture):
        captures[pattern_node.name] = target_node
        debug_log("Pattern is capture, expand", depth)
        assert isinstance(pattern_node.pattern, nodes.AST)
        return _match_node(pattern_node.pattern, target_node, depth + 1, captures)

    if not issubclass(target_node.__class__, pattern_node.ast_class):
        debug_log(f"{pattern_node} is not {target_node.__class__}, mismatch", depth)
        return False

    for name, field in pattern_node.fields:
        if name in pattern_node._child_fields:
            continue

        if name not in target_node._fields:
            raise ValueError(
                f"{name} not in {target_node._fields} when matching {pattern_node} against {target_node}"
            )

        if not _match_field(field, getattr(target_node, name), depth + 0.5, captures):
            debug_log(f"Field {name} mismatch", depth)
            return False

        debug_log(
            f"Field {name} matched with {repr(getattr(target_node, name))}", depth + 0.5
        )

    for name, child in pattern_node.child_fields:
        # TODO: fix

        if isinstance(child, nodes.Wildcard):
            debug_log(f"Child {name} is wildcard, shortcut", depth)
            continue

        while isinstance(child, nodes.Capture):
            captures[child.name] = getattr(target_node, name)
            debug_log(f"Child {name} is capture, expand", depth)
            child = child.pattern

        target_child = getattr(target_node, name)
        if isinstance(target_child, list):
            assert isinstance(child, list)

            if len(target_child) != len(child):
                debug_log(f"Child {name} is list, length mismatch", depth)
                return False

            for p, t in zip(child, target_child):
                if not _match_node(p, t, depth + 1, captures):
                    debug_log(f"Field {name} mismatch", depth)
                    return False
            continue

        if isinstance(child, list):
            debug_log(
                f"Child {name} is list: {child}, but target is not list: {target_child}",
                depth,
            )
            return False

        if not _match_node(child, target_child, depth + 1, captures):
            debug_log(f"Field {name} mismatch", depth)
            return False

    debug_log(f"Match {pattern_node} against {target_node} success", depth)
    return True


@dataclass(frozen=True)
class MatchResult[N: ast.AST, *T, K: dict]:
    node: N
    groups: tuple[*T]
    kw_groups: K

    def to_tuple(self) -> tuple[N, *T, K]:
        return (self.node, *self.groups, self.kw_groups)


class MatchTypeHint[N: ast.AST, *T, K: dict]:
    pass


MATCH_TYPE_HINT_DEFAULT = MatchTypeHint[ast.AST, *tuple[Any, ...], dict]()


@overload
def match_node[N: ast.AST, *T, K: dict](
    pattern_node: nodes.AST,
    target: ast.AST,
    #
    assert_match: Literal[True],
    match_type_hint: MatchTypeHint[N, *T, K] = MATCH_TYPE_HINT_DEFAULT,
) -> MatchResult[N, *T, K]: ...


@overload
def match_node[N: ast.AST, *T, K: dict](
    pattern_node: nodes.AST,
    target: ast.AST,
    #
    assert_match: Literal[False] = False,
    match_type_hint: MatchTypeHint[N, *T, K] = MATCH_TYPE_HINT_DEFAULT,
) -> MatchResult[N, *T, K] | None: ...


def match_node[N: ast.AST, *T, K: dict](
    pattern_node: nodes.AST,
    target: ast.AST,
    #
    assert_match: bool = False,
    match_type_hint: MatchTypeHint[N, *T, K] = MATCH_TYPE_HINT_DEFAULT,  # pyright: ignore
) -> MatchResult[N, *T, K] | None:
    sink = io.StringIO()
    handler_id = logger.add(sink, format="{message}")

    captures: dict[str | int, Any] = {}
    res = _match_node(pattern_node, target, 0, captures)

    logger.remove(handler_id)

    if res:
        int_keys = [k for k in captures.keys() if isinstance(k, int)]
        if int_keys:
            assert int_keys == list(range(min(int_keys), max(int_keys) + 1))

        args: Any = [None] * len(int_keys) + [captures]
        for k in int_keys:
            args[k] = captures.pop(k)

        return cast(Any, MatchResult(node=target, groups=tuple(args), kw_groups=captures))

    if assert_match:
        raise ValueError(
            f"Pattern {pattern_node} does not match:\n{ast.unparse(target)}\n"
            "Traceback:\n"
            f"{sink.getvalue()}"
        )
    return None


@overload
def match_pattern[N: ast.AST, *T, K: dict](
    pattern: str,
    target: ast.AST,
    assert_match: Literal[False] = False,
    match_type_hint: MatchTypeHint[N, *T, K] = MATCH_TYPE_HINT_DEFAULT,
) -> MatchResult[N, *T, K] | None: ...


@overload
def match_pattern[N: ast.AST, *T, K: dict](
    pattern: str,
    target: ast.AST,
    #
    assert_match: Literal[True],
    match_type_hint: MatchTypeHint[N, *T, K] = MATCH_TYPE_HINT_DEFAULT,
) -> MatchResult[N, *T, K]: ...


def match_pattern[N: ast.AST, *T, K: dict](
    pattern: str,
    target: ast.AST,
    #
    assert_match: bool = False,
    match_type_hint: MatchTypeHint[N, *T, K] = MATCH_TYPE_HINT_DEFAULT,  # pyright: ignore
) -> MatchResult[N, *T, K] | None:
    pattern_node = parse_pattern(pattern)
    return match_node(pattern_node, target, assert_match=assert_match)  # pyright: ignore
