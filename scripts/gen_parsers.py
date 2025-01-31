from __future__ import annotations

import token
import tokenize
from pathlib import Path
from typing import IO, Callable, Optional

from pegen.grammar import Alt, Grammar, GrammarVisitor, Group, NamedItem, NameLeaf, Rule
from pegen.grammar_parser import GeneratedParser
from pegen.python_generator import PythonCallMakerVisitor, PythonParserGenerator
from pegen.tokenizer import Tokenizer
from typer import Typer

from .testcase_metagenerator import TestcaseCallMakerVisitor, TestcaseMetaGenerator

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
    def visit_Group(self, node: Group) -> tuple[Optional[str], str]:
        return super().visit_Group(node)


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

    def validate_rule_names(self) -> None:
        pass

    def visit_Rule(self, node: Rule) -> None:
        if node.name == "start":
            self.print("@wrap_start")
        elif node.name == "stmt":
            self.print("@wrap_stmt")
        super().visit_Rule(node)

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
    from .generated_parser import GeneratedParser as CustomParser
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

    # print(item_types)


@app.command("dsl")
def gen_dsl_parser():
    gen_parser(DSLParserGenerator, CustomPythonCallMakerVisitor, DSL_PARSER_FILE)


@app.command("testcase")
def gen_testcase_parser():
    gen_parser(TestcaseMetaGenerator, TestcaseCallMakerVisitor, TESTCASE_GENERATOR_FILE)


if __name__ == "__main__":
    app()
