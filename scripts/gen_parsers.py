from __future__ import annotations

import token
import tokenize
from pathlib import Path
from typing import IO, Callable, Optional

from pegen.grammar import *
from pegen.grammar_parser import GeneratedParser
from pegen.python_generator import PythonCallMakerVisitor, PythonParserGenerator
from pegen.tokenizer import Tokenizer
from typer import Typer


# TODO: custom base

METAGRAMMAR_FILE = Path(__file__).parent / "data" / "modified_metagrammar.gram"
GRAMMAR_FILE = Path(__file__).parent / "data" / "match.gram"

GENERATED_PARSER_FILE = Path(__file__).parent / "generated_parser.py"
DSL_PARSER_FILE = Path() / "ast_lib" / "pattern" / "dsl_parser.py"
TESTCASE_GENERATOR_FILE = Path() / "ast_lib" / "testcase_generator.py"

app = Typer()


@app.command("meta")
def gen_grammar_parser():
    with open(METAGRAMMAR_FILE) as file:
        tokenizer = Tokenizer(tokenize.generate_tokens(file.readline))
        parser = GeneratedParser(tokenizer)
        grammar = parser.start()

        if not grammar:
            raise parser.make_syntax_error(str(METAGRAMMAR_FILE))

    with open(GENERATED_PARSER_FILE, "w") as file:
        gen = PythonParserGenerator(grammar, file)
        gen.generate(str(METAGRAMMAR_FILE))


class RemoveRuleVisitor(GrammarVisitor):
    def __init__(self, to_remove: set[str]):
        self.to_remove = to_remove

    def visit_Alt(self, node: Alt) -> None:
        new_items = []

        for item in node.items:
            match item:
                case NamedItem(item=NameLeaf(value=name)):
                    if name in self.to_remove:
                        continue
                case _:
                    pass
            new_items.append(item)
        node.items = new_items

        self.generic_visit(node)


class TestVisitor(GrammarVisitor):
    def visit_NameLeaf(self, node: NameLeaf) -> None:
        if node.value == "_":
            breakpoint()


class CustomPythonCallMakerVisitor(PythonCallMakerVisitor):
    # def visit_Group(self, node: Group) -> tuple[Optional[str], str]:
    #     return super().visit_Group(node)

    def add_repeat_type(self, name: str):
        # if name=='_loop1_8':
        #     breakpoint()

        assert name in self.gen.todo
        rule = self.gen.todo[name]
        assert len(rule.rhs.alts) == 1
        alt = rule.rhs.alts[0]
        assert isinstance(alt, Alt)
        assert len(alt.items) == 1
        item = alt.items[0]
        if isinstance(item.item, NameLeaf):
            if leaf_rule := self.gen.all_rules.get(item.item.value):
                rule.type = f"list[{leaf_rule.type}]"

    def visit_Repeat0(self, node: Repeat0) -> tuple[str, str]:
        name, call = super().visit_Repeat0(node)
        self.add_repeat_type(name)
        return name, call

    def visit_Repeat1(self, node: Repeat1) -> tuple[str, str]:
        name, call = super().visit_Repeat1(node)
        self.add_repeat_type(name)
        return name, call


item_types = set()


class DSLParserGenerator(PythonParserGenerator):
    def __init__(
        self,
        grammar: Grammar,
        file: Optional[IO[str]],
        tokens: set[str] = set(token.tok_name.values()),  # pyright: ignore
        location_formatting: Optional[str] = None,
        unreachable_formatting: Optional[str] = None,
    ):
        super().__init__(
            grammar, file, tokens, location_formatting, unreachable_formatting
        )
        self.all_rules.update(self.rules)

    def validate_rule_names(self) -> None:
        pass

    def visit_Rule(self, node: Rule) -> None:
        
        # if node.name =='_loop0_4':
        #     print(repr(node.rhs.alts[0].itemskjj))
        #     breakpoint()

        if node.name == "start":
            self.print("@wrap_start")
        elif node.name == "stmt":
            self.print("@wrap_stmt")
        self.all_rules[node.name] = node

        # modified from pegen.python_generator.PythonParserGenerator.visit_Rule
        is_loop = node.is_loop()
        is_gather = node.is_gather()
        rhs = node.flatten()
        if node.left_recursive:
            if node.leader:
                self.print("@memoize_left_rec")
            else:
                # Non-leader rules in a cycle are not memoized,
                # but they must still be logged.
                self.print("@logger")
        else:
            self.print("@memoize")
        node_type = node.type or "Any"
        if not is_loop:
            node_type = f"Optional[{node_type}]"
        self.print(f"def {node.name}(self) -> {node_type}:")
        with self.indent():
            self.print(f"# {node.name}: {rhs}")
            if node.nullable:
                self.print(f"# nullable={node.nullable}")

            if node.name.endswith("without_invalid"):
                self.print("_prev_call_invalid = self.call_invalid_rules")
                self.print("self.call_invalid_rules = False")
                self.cleanup_statements.append(
                    "self.call_invalid_rules = _prev_call_invalid"
                )

            self.print("mark = self._mark()")
            if self.alts_uses_locations(node.rhs.alts):
                self.print("tok = self._tokenizer.peek()")
                self.print("start_lineno, start_col_offset = tok.start")
            if is_loop:
                self.print("children = []")
            self.visit(rhs, is_loop=is_loop, is_gather=is_gather)
            if is_loop:
                self.add_return("children")
            else:
                self.add_return("None")

        if node.name.endswith("without_invalid"):
            self.cleanup_statements.pop()

    def visit_NamedItem(
        self, node: NamedItem, used: Optional[set[str]], unreachable: bool
    ) -> None:
        item_types.add(type(node.item))
        name, call = self.callmakervisitor.visit(node.item)
        if unreachable:
            name = None
        elif node.name:
            name = node.name

        if used is not None and name not in used:
            name = None

        if not name:
            # Parentheses are needed because the trailing comma may appear :>
            self.print(f"({call})")
        else:
            if name != "cut":
                name = self.dedupe(name)
            if node.type:
                call = f"cast({node.type}, {call})"
            self.print(f"({name} := {call})")


def gen_parser(
    generator_cls: type[PythonParserGenerator],
    get_callmaker: Callable[[PythonParserGenerator], GrammarVisitor],
    output_file: Path,
):
    # TODO: action

    # if TYPE_CHECKING:
    # else:
    #     from generated import GeneratedParser as CustomParser

    with open(GRAMMAR_FILE) as file:
        tokenizer = Tokenizer(tokenize.generate_tokens(file.readline))
        # parser = CustomParser(tokenizer)
        parser = GeneratedParser(tokenizer)
        grammar = parser.start()

        if not grammar:
            raise parser.make_syntax_error(str(GRAMMAR_FILE))

    # pegen.grammar.SIMPLE_STR = False

    RemoveRuleVisitor({"_"}).visit(grammar)
    TestVisitor().visit(grammar)

    with open(output_file, "w") as file:
        gen = generator_cls(grammar, file)
        gen.callmakervisitor = get_callmaker(gen)  # type: ignore # pyright: ignore
        gen.generate(str(GRAMMAR_FILE))

    # print(gen.rules)

    # print(item_types)


@app.command("dsl")
def gen_dsl_parser():
    gen_parser(DSLParserGenerator, CustomPythonCallMakerVisitor, DSL_PARSER_FILE)


# @app.command("testcase")
# def gen_testcase_parser():
#     gen_parser(TestcaseMetaGenerator, TestcaseCallMakerVisitor, TESTCASE_GENERATOR_FILE)


if __name__ == "__main__":
    app()
