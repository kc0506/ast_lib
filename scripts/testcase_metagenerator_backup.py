# pyright: reportUnusedVariable=false, reportUnusedImport=false, reportIncompatibleMethodOverride=false, reportUnusedParameter=false
# ruff: noqa: F401, F841, E703, F405, F403, F634
from __future__ import annotations

import ast
import inspect
import re
import string
import textwrap
import token
from contextlib import contextmanager, nullcontext
from itertools import chain
from tokenize import TokenInfo
from typing import IO, Literal, NamedTuple, Optional, Text, cast

# Assume only these types: {NameLeaf, Opt, StringLeaf, Repeat0, Group}
from hypothesis import assume
from hypothesis import strategies as st
from pegen.grammar import *  # pyright: ignore
from pegen.parser_generator import ParserGenerator

from .utils import UsedNamesVisitor


def parse_as_expr(s: str) -> ast.expr:
    node = ast.parse(s)
    match node:
        case ast.Module(body=[ast.Expr(expr)]):
            return expr
        case _:
            raise ValueError(f"Result is not an expression:\n{ast.dump(node)}")


NODE_TYPES = set(ast.__dict__) | {"Capture", "Wildcard", "WildcardId"}


class ReplaceTransformer(ast.NodeTransformer):
    def __init__(self, name_map: dict[str, str], type_map: dict[str, str]):
        self.name_map = name_map
        self.type_map = type_map

    def visit_Name(self, node: ast.Name) -> ast.expr:
        type = None
        if node.id in self.type_map:
            type = self.type_map[node.id]

        while node.id in self.name_map:
            node.id = self.name_map[node.id]
        if type:
            return parse_as_expr(f"cast({type}, {node.id})")
        return node


class ActionTransformer(ast.NodeTransformer):
    def transform(self, node: ast.mod) -> str | None:
        match node:
            case ast.mod(body=[ast.Expr(expr)]):
                pass
            case ast.mod(body=[ast.Pass()]):
                return None
            case _:
                raise ValueError(f"Invalid node:\n{ast.dump(node)}")

        match expr:
            case ast.Call(func=ast.Name(func_name) as func, keywords=keywords):
                pass
            case _:
                return ast.unparse(self.visit(expr)) + "#! warning"
        if func_name not in NODE_TYPES:
            if func_name.startswith("_"):
                return ast.unparse(node) + "#TODO"
            return None

        for keyword in keywords:
            keyword.value = self.visit(keyword.value)

        return ast.unparse(ast.Call(parse_as_expr("st.builds"), [func], keywords))

    def visit_BoolOp(self, node: ast.BoolOp) -> ast.expr:
        match node:
            case ast.BoolOp(op=ast.Or(), values=[first, second]):
                just_second = f"st.just(('', {ast.unparse(second)}))"
                return parse_as_expr(
                    f"or_strategy({ast.unparse(first)}, {just_second})"
                )
            case _:
                return super().visit_BoolOp(node)

    def visit_Attribute(self, node: ast.Attribute) -> ast.expr:
        return parse_as_expr(f"{ast.unparse(node.value)}.map(lambda x: x.{node.attr})")

    def visit_Call(self, node: ast.Call) -> ast.expr:
        match node:
            case ast.Call(func, args=[]):
                return parse_as_expr(f"st.just({ast.unparse(func)}())")
            case ast.Call(func, args=[arg]):
                pass
            case _:
                raise ValueError(f"Invalid node:\n{ast.dump(node)}")
        arg = self.visit(arg)
        return parse_as_expr(f"{ast.unparse(arg)}.map({ast.unparse(func)})")

    def visit_Subscript(self, node: ast.Subscript) -> ast.expr:
        # TODO: is map correct?
        return parse_as_expr(
            f"{ast.unparse(node.value)}.map(lambda x: x[{ast.unparse(node.slice)}])"
        )

    def visit_Constant(self, node: ast.Constant) -> ast.expr:
        return parse_as_expr(f"st.just({repr(node.value)})")

    def visit_Dict(self, node: ast.Dict) -> ast.expr:
        return parse_as_expr("st.just()")


class Never:
    pass


class CodeItem(NamedTuple):
    type: Literal["str", "neg", "pos"]
    value: str | CodeItem

    @staticmethod
    def merge(draw: st.DrawFn, itemss: list[list[CodeItem]]) -> list[CodeItem]:
        if not itemss:
            return []
        first = itemss.pop(0)
        for items in itemss:
            for item in items:
                cur_last = first[-1]
                if cur_last.type == "pos":
                    if item.type == "str":
                        if item.value != cur_last.value:
                            return draw(st.nothing())
                    else:
                        breakpoint()
                if cur_last.type == "neg":
                    if item.type == "str":
                        if item.value == cur_last.value:
                            return draw(st.nothing())
                    else:
                        breakpoint()

        return first

    @classmethod
    def from_str(cls, s: str) -> list[CodeItem]:
        return [cls("str", s)]


# @st.composite
def repeat_strategy[T](
    draw: st.DrawFn,
    arg: st.SearchStrategy[tuple[list[CodeItem], T]],
    min_size: int,
) -> tuple[list[CodeItem], list[T]]:
    # ss, vs =
    samples = draw(st.lists(arg, min_size=min_size))
    ss = [s for s, _ in samples]
    vs = [v for _, v in samples]
    return CodeItem.merge(draw, ss), vs


# @st.composite
def gather_strategy[T0, T1](
    draw: st.DrawFn,
    call: st.SearchStrategy[tuple[list[CodeItem], T0]],
    separator: st.SearchStrategy[tuple[list[CodeItem], T1]],
) -> tuple[list[CodeItem], list[T0]]:
    # TODO: is this correct?
    calls = draw(st.lists(call, min_size=0))
    assume(len(calls) > 0)
    assert len(calls) > 0

    num_seps = len(calls) - 1
    seps = draw(st.lists(separator, min_size=num_seps, max_size=num_seps)) + [
        ([], cast(T1, None))
    ]

    x = list(chain(*zip(calls, seps)))[:-1]
    ss = [s for s, _ in x]
    vs = [v for _, v in calls]
    return CodeItem.merge(draw, ss), vs


def fake_tokeninfo(s: str, type: int) -> TokenInfo:
    if s in token.EXACT_TOKEN_TYPES:
        type = token.EXACT_TOKEN_TYPES[s]
    return TokenInfo(type=type, string=s, start=(0, 0), end=(0, len(s)), line="")


# (func, is_composite)
COPY_FUNCS = (
    (Never, False),
    (CodeItem, False),
    (repeat_strategy, True),
    (gather_strategy, True),
    (fake_tokeninfo, False),
)


class TestcaseGeneratorBase:
    def name(
        self, max_depth: int
    ) -> st.SearchStrategy[tuple[list[CodeItem], TokenInfo]]:
        if max_depth <= 0:
            return st.nothing()

        @st.composite
        def func(draw: st.DrawFn) -> tuple[list[CodeItem], TokenInfo]:
            s = draw(
                st.from_regex(
                    r"[a-zA-Z_][a-zA-Z0-9_]*",
                    fullmatch=True,
                )
            )
            return CodeItem.from_str(s), fake_tokeninfo(s, token.NAME)

        return func()

    def number(
        self, max_depth: int
    ) -> st.SearchStrategy[tuple[list[CodeItem], TokenInfo]]:
        if max_depth <= 0:
            return st.nothing()

        @st.composite
        def func(draw: st.DrawFn) -> tuple[list[CodeItem], TokenInfo]:
            # todo: negative numbers
            s = draw(
                st.one_of(
                    [
                        st.integers(min_value=0),
                        st.floats(min_value=0, allow_infinity=False),
                    ]
                )
            )
            return CodeItem.from_str(str(s)), fake_tokeninfo(str(s), token.NUMBER)

        return func()

    def string(
        self, max_depth: int
    ) -> st.SearchStrategy[tuple[list[CodeItem], TokenInfo]]:
        if max_depth <= 0:
            return st.nothing()

        @st.composite
        def func(draw: st.DrawFn) -> tuple[list[CodeItem], TokenInfo]:
            s = draw(
                st.one_of(
                    [
                        st.from_regex(
                            r'"[^"\n\s]*"', alphabet=string.printable, fullmatch=True
                        ),
                        st.from_regex(
                            r"'[^'\n\s]*'", alphabet=string.printable, fullmatch=True
                        ),
                    ]
                )
            )
            return CodeItem.from_str(s), fake_tokeninfo(s, token.STRING)

        return func()


class TestcaseCallMakerVisitor(GrammarVisitor):
    def __init__(self, gen: ParserGenerator):
        self.gen = gen
        self.cache: dict[Any, Any] = {}

    def visit_NamedItem(self, node: NamedItem) -> tuple[Optional[str], str]:
        name, call = self.visit(node.item)
        if node.name:
            name = node.name
        return name, call

    def visit_NameLeaf(self, node: NameLeaf) -> tuple[Optional[str], str]:
        name = node.value.lower()
        return name, f"self.{name}(max_depth-1)"

    def visit_Opt(self, node: Opt) -> tuple[Optional[str], str]:
        try:
            _, call = self.visit(node.node)
        except Exception as e:
            breakpoint()
            raise e
        return (
            "opt",
            f"st.one_of([st.tuples(st.just([CodeItem('str', '')]), st.none()), {call}])",
        )

    def visit_StringLeaf(self, node: StringLeaf) -> tuple[Optional[str], str]:
        return (
            "literal",
            f"st.just(cast(tuple[list[CodeItem], object], ([CodeItem('str', {node.value})], fake_tokeninfo({node.value}, token.STRING))))",
        )

    def visit_Repeat0(self, node: Repeat0) -> tuple[Optional[str], str]:
        _, call = self.visit(node.node)
        return "repeat0", f"repeat_strategy({call}, min_size=0)"

    def visit_Repeat1(self, node: Repeat1) -> tuple[Optional[str], str]:
        _, call = self.visit(node.node)
        return "repeat1", f"repeat_strategy({call}, min_size=1)"

    def visit_Gather(self, node: Gather) -> Tuple[str, str]:
        if node in self.cache:
            return self.cache[node]
        _, call = self.visit(node.node)
        _, separator = self.visit(node.separator)

        self.cache[node] = "gather", f"gather_strategy({call}, {separator})"
        return self.cache[node]

    def visit_Group(self, node: Group) -> tuple[Optional[str], str]:
        return self.visit(node.rhs)

    def visit_Rhs(self, node: Rhs) -> tuple[Optional[str], str]:
        if node in self.cache:
            return self.cache[node]
        if len(node.alts) == 1 and len(node.alts[0].items) == 1:
            self.cache[node] = self.visit(node.alts[0].items[0])
        else:
            name = self.gen.artifical_rule_from_rhs(node)
            self.cache[node] = name, f"self.{name}(max_depth-1)"
        return self.cache[node]

    def visit_Cut(self, node: Cut) -> Tuple[None, str]:
        assert False

    def visit_PositiveLookahead(self, node: PositiveLookahead) -> tuple[None, str]:
        _, call = self.visit(node.node)
        return None, f"{call}.map(lambda x: CodeItem('pos', x[0]), Never())"

    def visit_NegativeLookahead(self, node: NegativeLookahead) -> tuple[None, str]:
        _, call = self.visit(node.node)
        return None, f"{call}.map(lambda x: CodeItem('neg', x[0]), Never())"


# TODO: 1. alts -> one of
# TODO: 2.
# TODO: 3.
# TODO: 4.
# TODO: 5.
# TODO: 6.
# TODO: 7.


class TestcaseMetaGenerator(ParserGenerator, GrammarVisitor):
    """
    Used to generate a hypothesis strategy for the DSL parser.

    When a rule of TestcaseGenerator is called, one of the alts will be drawed.
    The returned value by rules will be a tuple: (pattern_str, pattern_node).
    i.e. we simultaneously build a pattern_node, and a pattern string that will be parsed into that node.
    """

    def __init__(
        self,
        grammar: Grammar,
        file: Optional[IO[Text]],
        tokens: Set[str] = set(token.tok_name.values()),  # pyright: ignore
        location_formatting: Optional[str] = None,
        unreachable_formatting: Optional[str] = None,
    ):
        grammar.rules.pop("stmts")
        grammar.rules["start"] = Rule(
            name="start",
            type="stmt",
            rhs=Rhs(alts=[Alt(items=[NamedItem(None, item=NameLeaf(value="stmt"))])]),
        )

        super().__init__(grammar, tokens, file)
        self.callmakervisitor = TestcaseCallMakerVisitor(self)
        self.used_names_visitor = UsedNamesVisitor()
        self.cleanup_statements: List[str] = []
        self.rule_stack: list[str] = []

    def generate(self, filename: str) -> None:
        metas = self.grammar.metas
        header = metas.get("header") or ""
        header = header.replace(", Parser", "")
        header += """\
import string
import token
from typing import Literal, NamedTuple
from itertools import chain
from tokenize import TokenInfo
from hypothesis import strategies as st
from hypothesis import assume

from rich.traceback import install
"""
        self.print(header.rstrip("\n").format(filename=filename))

        subheader = metas.get("subheader") or ""
        subheader += "\n" + inspect.getsource(TestcaseGeneratorBase)
        for copy_func, is_composite in COPY_FUNCS:
            if is_composite:
                subheader += "\n@st.composite"
            subheader += "\n" + inspect.getsource(inspect.unwrap(copy_func))
        subheader += "\n" + "install()"
        subheader += "\n" + "debug_cnt=0"
        self.print(subheader)

        cls_name = "TestcaseGenerator"
        self.print(
            "# Keywords and soft keywords are listed at the end of the parser definition."
        )
        self.print(f"class {cls_name}(TestcaseGeneratorBase):")
        while self.todo:
            for rulename, rule in list(self.todo.items()):
                del self.todo[rulename]
                self.print()
                with self.indent():
                    self.visit(rule)

        self.print()

        trailer = self.grammar.metas.get("trailer", None)
        if trailer is not None:
            self.print(trailer.rstrip("\n"))

    def current_rule(self) -> str:
        return self.rule_stack[-1]

    def add_return(self, value: str) -> None:
        self.print(f"return {value}")

    @contextmanager
    def with_rule(self, name: str):
        self.rule_stack.append(name)
        yield
        self.rule_stack.pop()

    def visit_Rule(self, node: Rule) -> None:
        is_loop = node.is_loop()
        is_gather = node.is_gather()
        rhs = node.flatten()

        node_type = node.type or "Any"
        return_type = f"st.SearchStrategy[tuple[list[CodeItem], {node_type}]]"
        self.print(f"def {node.name}(self, max_depth: int) -> {return_type}:")
        with self.indent():
            self.print("if max_depth <= 0:")
            with self.indent():
                self.print("return st.nothing()")

            self.print(f"# {node.name}: {rhs}")

            self.print(f"choices: list[{return_type}]=[]")

            with self.with_rule(node.name):
                self.visit(rhs, is_loop=is_loop, is_gather=is_gather)

            self.add_return("st.one_of(choices)")

    def print_action(
        self,
        action: Optional[str],
        local_names_offset: int,
        name_map: dict[str, str],
        item_type_map: dict[str, str],
    ) -> bool:
        local_names = self.local_variable_names[local_names_offset:]

        if not action:
            if len(local_names) == 1:
                action = local_names[0]
            else:
                action = ",".join(local_names)
                action = f"[{action}]"

        strategy_name = self.dedupe(f"{self.current_rule()}_st")

        self.print("@st.composite")
        self.print(
            f"def {strategy_name}(draw: st.DrawFn) -> tuple[list[CodeItem], Any]:"
        )
        with self.indent():
            self.print("global debug_cnt")
            self.print("debug_cnt += 1")

            str_names: list[str] = []
            for name in local_names:
                name1, name2 = self.dedupe(name), self.dedupe(name)
                str_names.append(name1)
                name_map[name] = name2

                self.print(f"{name1}, {name2} = draw({name})")

            # if strategy_name == "set_expr_st":
            #     self.print("if e_1 == '':")
            #     with self.indent():
            #         self.print("if e_2 is not None:")
            #         with self.indent():
            #             self.print("breakpoint()")

            self.print(f"merged_items = CodeItem.merge(draw, [{', '.join(str_names)}])")

            action = ast.unparse(
                ReplaceTransformer(name_map=name_map, type_map=item_type_map).visit(
                    ast.parse(action)
                )
            )
            self.print(f"return merged_items, {action}")
        self.print(f"choices.append({strategy_name}())")

        return True

    def visit_Rhs(
        self, node: Rhs, is_loop: bool = False, is_gather: bool = False
    ) -> None:
        if is_loop:
            assert len(node.alts) == 1

        # breakpoint()
        with self.local_variable_context():
            for alt in node.alts:
                self.visit(alt, is_loop=is_loop, is_gather=is_gather)

    def visit_Alt(self, node: Alt, is_loop: bool, is_gather: bool) -> None:
        has_cut = any(isinstance(item.item, Cut) for item in node.items)

        action = node.action

        locations = False
        unreachable = False
        used = None

        item_type_map: dict[str, str] = {}
        name_map: dict[str, str] = {}
        local_names_offset = len(self.local_variable_names)

        # with self.local_variable_context():
        with nullcontext():
            # if has_cut:
            #     self.print("cut = False")
            # if is_loop:
            #     self.print("while (")
            # else:
            self.print("if (")

            with self.indent():
                # with nullcontext():
                first = True
                for item in node.items:
                    if first:
                        first = False
                    else:
                        self.print("and")
                    self.visit(
                        item,
                        used=used,
                        unreachable=unreachable,
                        item_type_map=item_type_map,
                        name_map=name_map,
                    )
                    if is_gather:
                        self.print("is not None")

            self.print("):")
            with self.indent():
                # flake8 complains that visit_Alt is too complicated, so here we are :P
                if not self.print_action(
                    action, local_names_offset, name_map, item_type_map
                ):
                    print(node)
                    print()

    def visit_NamedItem(
        self,
        node: NamedItem,
        used: Optional[Set[str]],
        unreachable: bool,
        item_type_map: dict[str, str | None],
        name_map: dict[str, str],
    ) -> None:
        name, call = self.callmakervisitor.visit(node.item)
        if unreachable:
            name = None
        elif node.name:
            name = node.name

        # if used is not None and name not in used:
        #     name = None

        if not name:
            # Parentheses are needed because the trailing comma may appear :>
            self.print(f"({call},)")
        else:
            if name != "cut":
                original_name = name
                name = self.dedupe(name)
                name_map[original_name] = name
            self.print(f"({name} := {call},)")

        if isinstance(node.item, NameLeaf):
            # nameleaf_type = self.rules[node.item.value].type
            nameleaf_type = node.item.value
        else:
            nameleaf_type = None

        if name:
            item_type_map[name] = node.type  # or nameleaf_type
