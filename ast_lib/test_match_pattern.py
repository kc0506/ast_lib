import io
import sys
from contextlib import redirect_stderr

from loguru import logger
from pydantic import Field
from pydantic.dataclasses import dataclass

from ast_lib.pattern import parse_pattern


@dataclass
class Testcase:
    pattern: str
    matches: list[str]
    not_matches: list[str] = Field(default_factory=list)


EXAMPLES = [
    # Simple captures
    Testcase("$x", ["abc", "1", "{0: None}", "(1,)"]),
    Testcase("$x{~}", ["abc", "1", "{0: None}", "(1,)"]),
    # Testcase("$call{~(~)}", ["f()", "a.b()", "c[0]()"]),     # TODO
    Testcase("$call{~()}", ["f()", "a.b()", "c[0]()"]),
    Testcase("$attr{~.x}", ["a.x", "a.b.x", "c.y[0].x", "[].x", "None.x"]),
    # Names and Attributes
    Testcase("self.method", ["self.method"], ["self.method()", "self.method(1)"]),
    Testcase("obj.$attr", ["obj.a"], ["obj.attr()", "obj.attr(1)"]),
    Testcase(
        "$obj.method",
        ["a.method", "a.b.method", "a[0].method", "None.method"],
        ["obj.method()", "obj.method(1)"],
    ),
    Testcase("$attr{~.method}", ["a.method", "a.b.method", "c.x[0].method"]),
    Testcase("$chain{~.`.`}", ["a.b.c", "a.b.c.d", "a.b.c.d.e"]),
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
    Testcase("lst[0]", ["lst[0]"], ["lst[1]", "other[0]"]),
    Testcase("$sub{lst[~]}", ["lst[0]", "lst[i]", "lst[1:2]"], ["other[0]"]),
    Testcase("$sub{~[index]}", ["lst[index]", "arr[index]"], ["lst[0]", "lst[i]"]),
    Testcase("$sub{~[~]}", ["lst[0]", "arr[i]", "x[1:2]"]),
    # Assignments
    Testcase("x = y", ["x = y"], ["y = x", "a = b"]),
    Testcase("x: type = value", ["x: type = value"], ["x = value", "y: type = value"]),
    # Compound Examples
    Testcase(
        # TODO
        # "$call{self.$method(~)}.$attr",
        "$call{self.$method()}.$attr",
        # ["self.foo().bar", "self.method(x).attr", "self.f(1, 2).prop"],
        ["self.foo().bar"],
        ["other.method().attr"],
    ),
    Testcase(
        # TODO
        "$sub{items[~]}.method(~)",
        # ["items[0].method()", "items[i].method(x)", "items[1:2].method(a, b)"],
        ["items[i].method(x)"],
        ["other[0].method()", "items.method()"],
    ),
    Testcase(
        "$attr{~.method}($arg{~})",
        # ["obj.method(x)", "a.b.method(1)", "x.method(foo())"],
        ["obj.method(x)", "a.b.method(1)"],
        ["method(x)", "x.other(y)"],
    ),
    Testcase(
        # TODO
        "$chain{~.`.method(~)}",
        # ["a.b.method()", "x.y.method(1)", "foo.bar.method(x, y)"],
        ["x.y.method(1)"],
        ["method()", "a.method()"],
    ),
    Testcase("await a()", ["await a()"], ["a()", "await b()"]),
    # Testcase(
    #     "def __str__():...", ["def __str__(self, *args):\n\ta"], ["def str(): ..."]
    # ),
]


def test_match_pattern():
    captured = io.StringIO()
    with redirect_stderr(captured):
        logger.add(
            sys.stderr, level="DEBUG", format="{message}", filter="ast_lib.match_pattern"
        )

        # with nullcontext():
        for testcase in EXAMPLES[-1:]:
            pattern = parse_pattern(testcase.pattern)
            for match in testcase.matches:
                pos = captured.tell()

                if not (result := pattern.match(match)):
                    captured.seek(pos)
                    print(captured.read())
                    print(testcase.pattern)
                    print(f"Pattern {pattern} does not match {match}")
                    exit()
                # exit()

            for not_match in testcase.not_matches:
                pos = captured.tell()

                if pattern.match(not_match):
                    captured.seek(pos)
                    print(captured.read())
                    print(testcase.pattern)
                    print(f"Pattern {pattern} matches {not_match}")
                    exit()


if __name__ == "__main__":
    test_match_pattern()

    # captured = io.StringIO()
    # with redirect_stderr(captured):
    #     for i in range(10):
    #         print(i, file=sys.stderr)
    #         print("read", '#', captured.read(), '#')
