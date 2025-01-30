from dataclasses import dataclass

import pytest
from hypothesis import given

from ast_lib.nodes import *
from ast_lib.pattern import parse_pattern


@dataclass
class Case:
    patterns: list[str]
    expected: AST


EXAMPLES = [
    # Simple captures
    Case(
        ["$x"],
        Expr(Capture("x", expr())),
    ),
    Case(
        ["$x{~}"],
        Expr(Capture("x", Wildcard())),
    ),
    Case(
        ["$call{~(~)}"],
        Expr(Capture("call", Call(Wildcard(), [Wildcard()]))),
    ),
    Case(
        ["$attr{~.x}"],
        Expr(Capture("attr", Attribute(Wildcard(), "x"))),
    ),
    # Names and Attributes
    Case(
        ["self.method"],
        Expr(Attribute(Name("self"), "method")),
    ),
    Case(
        ["obj.$attr"],
        Expr(Attribute(Name("obj"), Capture("attr", WildcardId()))),
    ),
    Case(
        ["$obj.method"],
        Expr(Attribute(Capture("obj", expr()), "method")),
    ),
    Case(
        ["$attr{~.method}"],
        Expr(Capture("attr", Attribute(Wildcard(), "method"))),
    ),
    Case(
        ["$chain{~.`.`}"],
        Expr(
            Capture(
                "chain",
                Attribute(Attribute(Wildcard(), WildcardId()), WildcardId()),
            )
        ),
    ),
    # Function Calls
    Case(
        ["func()"],
        Expr(Call(Name("func"), [])),
    ),
    Case(
        ["func(arg)"],
        Expr(Call(Name("func"), [Name("arg")])),
    ),
    Case(
        ["func(arg1, arg2)"],
        Expr(Call(Name("func"), [Name("arg1"), Name("arg2")])),
    ),
    Case(
        ["$call{func(~)}"],
        Expr(Capture("call", Call(Name("func"), [Wildcard()]))),
    ),
    Case(
        ["$call{~(x, y)}"],
        Expr(Capture("call", Call(Wildcard(), [Name("x"), Name("y")]))),
    ),
    # Subscripts
    Case(
        ["lst[0]"],
        Expr(Subscript(Name("lst"), Constant(0))),
    ),
    Case(
        ["$sub{lst[~]}"],
        Expr(Capture("sub", Subscript(Name("lst"), Wildcard()))),
    ),
    Case(
        ["$sub{~[index]}"],
        Expr(Capture("sub", Subscript(Wildcard(), Name("index")))),
    ),
    Case(
        ["$sub{~[~]}"],
        Expr(Capture("sub", Subscript(Wildcard(), Wildcard()))),
    ),
    # Assignments
    Case(
        ["x = y"],
        Assign([Name("x")], Name("y")),
    ),
    Case(
        ["x: type = value"],
        AnnAssign(Name("x"), Name("type"), Name("value")),
    ),
    # Compound Examples
    Case(
        ["$call{self.$method(~)}.$attr"],
        Expr(
            Attribute(
                Capture(
                    "call",
                    Call(
                        Attribute(Name("self"), Capture("method", WildcardId())),
                        [Wildcard()],
                    ),
                ),
                Capture("attr", WildcardId()),
            )
        ),
    ),
    Case(
        ["$sub{items[~]}.method(~)"],
        Expr(
            Call(
                Attribute(
                    Capture("sub", Subscript(Name("items"), Wildcard())), "method"
                ),
                [Wildcard()],
            )
        ),
    ),
    Case(
        ["$attr{~.method}($arg{~})"],
        Expr(
            Call(
                Capture("attr", Attribute(Wildcard(), "method")),
                [Capture("arg", Wildcard())],
            )
        ),
    ),
    Case(
        ["$chain{~.`.method(~)}"],
        Expr(
            Capture(
                "chain",
                Call(
                    Attribute(Attribute(Wildcard(), WildcardId()), "method"),
                    [Wildcard()],
                ),
            )
        ),
    ),
    Case(
        ["await a()"],
        Expr(Await(Call(Name("a"), []))),
    ),
    Case(
        ["def f():..."],
        FunctionDef(
            name="f",
            args=arguments.make_empty(),
            # args=[],
            decorator_list=[],
        ),
    ),
    Case(
        ["async def f():..."],
        AsyncFunctionDef(
            name="f",
            args=arguments.make_empty(),
            # args=[],
            decorator_list=[],
        ),
    ),
    Case(
        ["$0 .a"],
        Expr(Attribute(Capture(0, expr()), "a")),
    ),
    Case(
        ["$0{self.`[~]}"],
        Expr(
            value=Capture(
                name=0, pattern=Subscript(value=Attribute(value=Name(id="self")))
            )
        ),
    ),
]


@pytest.mark.parametrize("testcase", EXAMPLES)
def test_patterns(testcase: Case):
    for pattern in testcase.patterns:
        parsed = parse_pattern(pattern)
        assert parsed == testcase.expected, f"""
Pattern: {pattern}
Parsed:  {parsed}
Expected: {testcase.expected}
"""


if __name__ == "__main__":
    # TODO: validate captures

    # test_patterns()
    pass

    # parser = from_string("{ x*1**2 or 3 and 4+5 , '5', abc}")
    # print(parser.expr())

    # hash(FunctionDef(args=[]))
