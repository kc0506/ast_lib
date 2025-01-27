

.PHONY: visitor-pyi
visitor-pyi:
	uv run -m scripts.transform_visitor_pyi reducer
	uv run ruff format ast_lib/visitor/*.pyi
	uv run ruff check ast_lib/visitor/*.pyi --fix

.PHONY: gen-nodes
gen-nodes:
	uv run -m scripts.gen_nodes
	uv run ruff format ast_lib/nodes.py
	uv run ruff check ast_lib/nodes.py --fix

.PHONY: gen-dsl
gen-dsl:
	uv run -m scripts.gen_parsers dsl
# uv run ruff format ast_lib/dsl_parser.py
# uv run ruff check ast_lib/dsl_parser.py --fix

.PHONY: gen-testcase
gen-testcase:
	uv run -m scripts.gen_parsers testcase
	uv run ruff format ast_lib/testcase_generator.py
	uv run ruff check ast_lib/testcase_generator.py --fix

.PHONY: test-types
test-types:
	uv run pyright tests/test_types.py


.PHONY: test
test:
	uv run pytest tests/ --ignore=tests/test_types.py
