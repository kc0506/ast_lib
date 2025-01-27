from dataclasses import dataclass

from .nodes import *
from .pattern import parse_pattern


@dataclass
class Testcase:
    patterns: list[str]
    expected: AST


EXAMPLES = [
    # Simple captures
    Testcase(
        ["$x"],
        Expr(Capture("x", expr())),
    ),
    Testcase(
        ["$x{~}"],
        Expr(Capture("x", Wildcard())),
    ),
    Testcase(
        ["$call{~(~)}"],
        Expr(Capture("call", Call(Wildcard(), [Wildcard()]))),
    ),
    Testcase(
        ["$attr{~.x}"],
        Expr(Capture("attr", Attribute(Wildcard(), "x"))),
    ),
    # Names and Attributes
    Testcase(
        ["self.method"],
        Expr(Attribute(Name("self"), "method")),
    ),
    Testcase(
        ["obj.$attr"],
        Expr(Attribute(Name("obj"), Capture("attr", WildcardId()))),
    ),
    Testcase(
        ["$obj.method"],
        Expr(Attribute(Capture("obj", expr()), "method")),
    ),
    Testcase(
        ["$attr{~.method}"],
        Expr(Capture("attr", Attribute(Wildcard(), "method"))),
    ),
    Testcase(
        ["$chain{~.`.`}"],
        Expr(
            Capture(
                "chain",
                Attribute(Attribute(Wildcard(), WildcardId()), WildcardId()),
            )
        ),
    ),
    # Function Calls
    Testcase(
        ["func()"],
        Expr(Call(Name("func"), [])),
    ),
    Testcase(
        ["func(arg)"],
        Expr(Call(Name("func"), [Name("arg")])),
    ),
    Testcase(
        ["func(arg1, arg2)"],
        Expr(Call(Name("func"), [Name("arg1"), Name("arg2")])),
    ),
    Testcase(
        ["$call{func(~)}"],
        Expr(Capture("call", Call(Name("func"), [Wildcard()]))),
    ),
    Testcase(
        ["$call{~(x, y)}"],
        Expr(Capture("call", Call(Wildcard(), [Name("x"), Name("y")]))),
    ),
    # Subscripts
    Testcase(
        ["lst[0]"],
        Expr(Subscript(Name("lst"), Constant(0))),
    ),
    Testcase(
        ["$sub{lst[~]}"],
        Expr(Capture("sub", Subscript(Name("lst"), Wildcard()))),
    ),
    Testcase(
        ["$sub{~[index]}"],
        Expr(Capture("sub", Subscript(Wildcard(), Name("index")))),
    ),
    Testcase(
        ["$sub{~[~]}"],
        Expr(Capture("sub", Subscript(Wildcard(), Wildcard()))),
    ),
    # Assignments
    Testcase(
        ["x = y"],
        Assign([Name("x")], Name("y")),
    ),
    Testcase(
        ["x: type = value"],
        AnnAssign(Name("x"), Name("type"), Name("value")),
    ),
    # Compound Examples
    Testcase(
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
    Testcase(
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
    Testcase(
        ["$attr{~.method}($arg{~})"],
        Expr(
            Call(
                Capture("attr", Attribute(Wildcard(), "method")),
                [Capture("arg", Wildcard())],
            )
        ),
    ),
    Testcase(
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
    Testcase(
        ["await a()"],
        Expr(Await(Call(Name("a"), []))),
    ),
    Testcase(
        ["def f():..."],
        FunctionDef(
            name="f",
            args=arguments.make_empty(),
            # args=[],
            decorator_list=[],
        ),
    ),
    Testcase(
        ["async def f():..."],
        AsyncFunctionDef(
            name="f",
            args=arguments.make_empty(),
            # args=[],
            decorator_list=[],
        ),
    ),
    Testcase(
        ["$0 .a"],
        Expr(Attribute(Capture(0, expr()), "a")),
    ),
    Testcase(
        ["$0{self.`[~]}"],
        Expr(
            value=Capture(
                name=0, pattern=Subscript(value=Attribute(value=Name(id="self")))
            )
        ),
    ),
]


def test_patterns():
    for testcase in EXAMPLES[-1:]:
        for pattern in testcase.patterns:
            parsed = parse_pattern(pattern)
            assert parsed == testcase.expected, f"""
Pattern: {pattern}
Parsed:  {parsed}
Expected: {testcase.expected}
"""


if __name__ == "__main__":
    # TODO: validate captures

    test_patterns()
    # parser = from_string("{ x*1**2 or 3 and 4+5 , '5', abc}")
    # print(parser.expr())

    # hash(FunctionDef(args=[]))
