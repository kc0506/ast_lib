import time
import tokenize
from io import StringIO
import warnings

from hypothesis import given
from hypothesis.errors import NonInteractiveExampleWarning
from rich import print

from ast_lib import nodes
from ast_lib.pattern import parse_pattern
# from ast_lib.testcase_generator import TestcaseGenerator

# gen = TestcaseGenerator()


# import logging

# logging.getLogger("hypothesis").setLevel(logging.ERROR)
# warnings.filterwarnings("ignore", category=NonInteractiveExampleWarning)

# for _ in range(20):
#     # st = time.perf_counter()
#     print(gen.expr(10).example())
#     # print(time.perf_counter() - st)
#     # print(gen.set_expr(10).example())


# @given(gen.expr(10))
# def test_testcase_gen(tu):
#     # stretagy = gen.constant()

#     pattern, node = tu
#     assert parse_pattern(pattern) == nodes.Expr(node)


# #     pattern, node = stretagy.example()
# #     print(pattern)
# #     print(node)
# #     if (parsed := parse_pattern(pattern)) != node:
# #         print("not equal")
# #         print(parsed)
# #         print(node)


# # if __name__ == "__main__":
# #     test_testcase_gen()
# #     # parse_pattern("-0.99999")

# #     # print(list(tokenize.generate_tokens(StringIO("-0.99999").readline)))
# #     pass
