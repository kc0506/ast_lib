import tokenize
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
from pegen.grammar import Alt, Grammar, GrammarVisitor, Group, NamedItem, NameLeaf, Rule
from pegen.grammar_parser import GeneratedParser
from pegen.python_generator import PythonCallMakerVisitor, PythonParserGenerator
from pegen.tokenizer import Tokenizer
from typer import Typer
from pyvis.network import Network


GRAMMAR_FILE = Path(__file__).parent / "data" / "python.gram"


class CollectNames(GrammarVisitor):
    def __init__(self):
        self.names: set[str] = set()

    def visit_NameLeaf(self, node: NameLeaf):
        self.names.add(node.value)


def visualize_grammar(grammar: Grammar, root: str):
    assert root in grammar.rules

    graph: dict[str, list[str]] = {}

    visited: set[str] = set()
    queue: list[str] = [root]

    while queue:
        rule = queue.pop(0)
        if rule in visited:
            continue

        graph.setdefault(rule, [])
        visited.add(rule)

        for alt in grammar.rules[rule].rhs.alts:
            visitor = CollectNames()
            visitor.visit(alt)
            for name in visitor.names:
                if name == rule:
                    continue
                if name.startswith('invalid'):
                    continue
                if name not in grammar.rules:
                    continue

                graph[rule].append(name)
                queue.append(name)

    # print(graph)
    visualize_graph_networkx(graph)


def visualize_graph_networkx(graph: dict[str, list[str]]):
    G = nx.DiGraph()
    G.add_nodes_from(graph.keys())
    for rule, children in graph.items():
        for child in children:
            G.add_edge(rule, child)
    # nx.draw(G, with_labels=True)
    # plt.show()
# Plot with pyvis

    net = Network(
        directed = True,
        select_menu = True, # Show part 1 in the plot (optional)
        filter_menu = True, # Show part 2 in the plot (optional)
    )
    net.show_buttons() # Show part 3 in the plot (optional)
    net.from_nx(G) # Create directly from nx graph
    # net.show('example.html')
    net.write_html('gram.html')


def main():
    with open(GRAMMAR_FILE) as file:
        tokenizer = Tokenizer(tokenize.generate_tokens(file.readline))
        parser = GeneratedParser(tokenizer)
        grammar = parser.start()

    assert grammar is not None
    visualize_grammar(grammar, "expressions")


if __name__ == "__main__":
    main()
