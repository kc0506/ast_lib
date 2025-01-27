from __future__ import annotations

import ast
import inspect
from typing import Any, Callable


def call_with_optional_self[R](func: Callable[..., R], *args) -> R:
    sig = inspect.signature(func)
    if len(sig.parameters) == len(args):
        return func(*args)

    assert len(sig.parameters) == len(args) - 1
    _, *args = args
    return func(*args)


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
