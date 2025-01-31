from __future__ import annotations

import tokenize
from io import StringIO

from pegen.tokenizer import Tokenizer

from . import nodes
from .dsl_parser import DSLParser


def parse_pattern(pattern: str) -> nodes.AST:
    if not pattern.endswith("\n"):
        pattern += "\n"
    tokengen = tokenize.generate_tokens(StringIO(pattern).readline)
    tokenizer = Tokenizer(tokengen)
    parser = DSLParser(tokenizer)
    tree: list[nodes.stmt] | None = parser.start()

    if tree is None:
        err = parser.make_syntax_error("pattern")
        raise err

    assert len(tree) == 1
    return tree[0]


def from_string(pattern: str) -> DSLParser:
    if not pattern.endswith("\n"):
        pattern += "\n"
    tokengen = tokenize.generate_tokens(StringIO(pattern).readline)
    tokenizer = Tokenizer(tokengen)
    parser = DSLParser(tokenizer)
    return parser
