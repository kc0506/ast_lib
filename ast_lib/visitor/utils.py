from __future__ import annotations

import ast
import inspect
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ..match_pattern import MatchResult


def check_callback_signature(
    func: Callable[..., Any],
    num_args: int,
):
    sig = inspect.signature(func)
    for name, param in sig.parameters.items():
        if param.kind == (
            inspect.Parameter.KEYWORD_ONLY,
            inspect.Parameter.VAR_KEYWORD,
            inspect.Parameter.VAR_POSITIONAL,
        ):
            raise ValueError(f"Invalid parameter kind of {name}: {param.kind}")

    params = list(sig.parameters.values())
    if len(params) not in range(
        num_args, num_args + 3
    ):  # (*args), (self, *args), (self, *args, match_result)
        raise ValueError(f"Expected {num_args} arguments, got {len(params)}")


def invoke_callback[R](
    func: Callable[..., R],
    self: ast.NodeVisitor,
    *args: Any,
    match_result: MatchResult,
) -> R:
    sig = inspect.signature(func)
    num_params = len(sig.parameters)
    check_callback_signature(func, num_params)

    if num_params == len(args):
        return func(*args)
    if num_params == len(args) + 1:
        return func(self, *args)
    if num_params == len(args) + 2:
        return func(self, *args, match_result)

    raise ValueError(f"Expected {num_params} arguments, got {len(args)}")


class DescriptorHelper:
    _name: str | None = None

    def __set_name__(self, owner: type[ast.NodeVisitor], name: str) -> None:
        self._name = name

    def _make_attr_name(self, name: str) -> str:
        if self._name is None:
            raise ValueError("DescriptorHelper is not initialized")
        return f"_{self._name}_{name}"

    def _has_attr(self, instance: ast.NodeVisitor, name: str) -> bool:
        return hasattr(instance, self._make_attr_name(name))

    def _get_attr(self, instance: ast.NodeVisitor, name: str) -> Any:
        return getattr(instance, self._make_attr_name(name))

    def _set_attr(self, instance: ast.NodeVisitor, name: str, value: Any) -> None:
        setattr(instance, self._make_attr_name(name), value)
