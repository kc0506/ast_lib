import ast
import io
import sys
from contextlib import redirect_stderr
from dataclasses import field
from inspect import isclass
from typing import Any

import pytest
from loguru import logger
from pydantic import Field
from pydantic.dataclasses import dataclass

from ast_lib.pattern import parse_pattern


@dataclass
class ExpectedMatch:
    pattern: str
    node_type: type[ast.AST]
    group_types: tuple[type[Any] | str, ...] = tuple()
    kw_group_types: dict[str, type[Any] | str] = field(default_factory=dict)


@dataclass
class Case:
    pattern: str
    matches: list[str | ExpectedMatch]
    not_matches: list[str] = Field(default_factory=list)


EXAMPLES = [
    # Simple captures
    Case(
        "$x",
        [
            ExpectedMatch(
                "abc",
                ast.Name,
                kw_group_types={"x": ast.Name},
            ),
            ExpectedMatch("1", ast.Constant, kw_group_types={"x": ast.Constant}),
            ExpectedMatch("{0: None}", ast.Dict, kw_group_types={"x": ast.Dict}),
            ExpectedMatch("(1,)", ast.Tuple, kw_group_types={"x": ast.Tuple}),
        ],
    ),
    Case("$x{~}", ["abc", "1", "{0: None}", "(1,)"]),
    # Testcase("$call{~(~)}", ["f()", "a.b()", "c[0]()"]),     # TODO
    Case("$call{~()}", ["f()", "a.b()", "c[0]()"]),
    Case("$attr{~.x}", ["a.x", "a.b.x", "c.y[0].x", "[].x", "None.x"]),
    # Names and Attributes
    Case("self.method", ["self.method"], ["self.method()", "self.method(1)"]),
    Case("obj.$attr", ["obj.a"], ["obj.attr()", "obj.attr(1)"]),
    Case(
        "$obj.method",
        ["a.method", "a.b.method", "a[0].method", "None.method"],
        ["obj.method()", "obj.method(1)"],
    ),
    Case("$attr{~.method}", ["a.method", "a.b.method", "c.x[0].method"]),
    Case("$chain{~.`.`}", ["a.b.c", "a.b.c.d", "a.b.c.d.e"]),
    # Function Calls
    # TODO
    # Testcase("func()", ["func()", "func(1)", "func(x, y)"], ["foo()", "other()"]),
    # Testcase("func(arg)", ["func(arg)", "func(arg, x)"], ["func()", "func(x)"]),
    # Testcase("func(arg1, arg2)", ["func(arg1, arg2)"], ["func()", "func(arg1)"]),
    # Testcase(
    #     "$call{func(~)}", ["func()", "func(1)", "func(x, y)"], ["foo()", "other()"]
    # ),
    # Testcase("$call{~(x, y)}", ["func(x, y)", "obj.method(x, y)"], ["f()", "f(x)"]),
    # Subscripts
    Case("lst[0]", ["lst[0]"], ["lst[1]", "other[0]"]),
    Case("$sub{lst[~]}", ["lst[0]", "lst[i]", "lst[1:2]"], ["other[0]"]),
    Case("$sub{~[index]}", ["lst[index]", "arr[index]"], ["lst[0]", "lst[i]"]),
    Case("$sub{~[~]}", ["lst[0]", "arr[i]", "x[1:2]"]),
    # Assignments
    Case("x = y", ["x = y"], ["y = x", "a = b"]),
    Case("x: type = value", ["x: type = value"], ["x = value", "y: type = value"]),
    # Compound Examples
    Case(
        # TODO
        # "$call{self.$method(~)}.$attr",
        "$call{self.$method()}.$attr",
        # ["self.foo().bar", "self.method(x).attr", "self.f(1, 2).prop"],
        [
            ExpectedMatch(
                "self.foo().bar",
                ast.Attribute,
                kw_group_types={"call": ast.Call, "method": "foo", "attr": "bar"},
            ),
        ],
        ["other.method().attr"],
    ),
    Case(
        # TODO
        "$sub{items[~]}.method(~)",
        # ["items[0].method()", "items[i].method(x)", "items[1:2].method(a, b)"],
        ["items[i].method(x)"],
        ["other[0].method()", "items.method()"],
    ),
    Case(
        "$attr{~.method}($arg{~})",
        # ["obj.method(x)", "a.b.method(1)", "x.method(foo())"],
        ["obj.method(x)", "a.b.method(1)"],
        ["method(x)", "x.other(y)"],
    ),
    Case(
        # TODO
        "$chain{~.`.method(~)}",
        # ["a.b.method()", "x.y.method(1)", "foo.bar.method(x, y)"],
        ["x.y.method(1)"],
        ["method()", "a.method()"],
    ),
    Case("await a()", ["await a()"], ["a()", "await b()"]),
    # Testcase(
    #     "def __str__():...", ["def __str__(self, *args):\n\ta"], ["def str(): ..."]
    # ),
    Case("return ~.format(~*)", ['return "a".format(b, c)']),
    Case(
        "return ~.format($0{~+})",
        [
            ExpectedMatch(
                'return "a".format(b, c)',
                ast.Return,
                group_types=(list,),
            ),
        ],
        ['return "a".format()'],
    ),
]


@pytest.mark.parametrize("testcase", EXAMPLES)
def test_match_pattern(testcase: Case):
    pattern = parse_pattern(testcase.pattern)
    for match in testcase.matches:
        if isinstance(match, str):
            res = pattern.match(match)
            assert res is not None
        else:
            res = pattern.match(match.pattern)
            assert res is not None
            assert len(res.groups) == len(match.group_types)
            assert len(res.kw_groups) == len(match.kw_group_types)

            for i, group_type in enumerate(match.group_types):
                if isclass(group_type):
                    assert isinstance(res.groups[i], group_type)
                else:
                    assert res.groups[i] == group_type
            for kw, kw_type in match.kw_group_types.items():
                if isclass(kw_type):
                    assert isinstance(res.kw_groups[kw], kw_type)
                else:
                    assert res.kw_groups[kw] == kw_type

    for not_match in testcase.not_matches:
        assert pattern.match(not_match) is None


# def test_match_pattern():
#     captured = io.StringIO()
#     with redirect_stderr(captured):
#         logger.add(
#             sys.stderr,
#             level="DEBUG",
#             format="{message}",
#             filter="ast_lib.match_pattern",
#         )

#         # with nullcontext():
#         for testcase in EXAMPLES[-1:]:
#             pattern = parse_pattern(testcase.pattern)
#             for match in testcase.matches:
#                 pos = captured.tell()

#                 if not (result := pattern.match(match)):
#                     captured.seek(pos)
#                     print(captured.read())
#                     print(testcase.pattern)
#                     print(f"Pattern {pattern} does not match {match}")
#                     exit()
#                 # exit()

#             for not_match in testcase.not_matches:
#                 pos = captured.tell()

#                 if pattern.match(not_match):
#                     captured.seek(pos)
#                     print(captured.read())
#                     print(testcase.pattern)
#                     print(f"Pattern {pattern} matches {not_match}")
#                     exit()


if __name__ == "__main__":
    # test_match_pattern()
    pass

    # captured = io.StringIO()
    # with redirect_stderr(captured):
    #     for i in range(10):
    #         print(i, file=sys.stderr)
    #         print("read", '#', captured.read(), '#')
