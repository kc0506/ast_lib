

VISITOR_TARGETS = reducer presets context
VISITOR_PYI_FULL_PATHS = $(addprefix ast_lib/visitor/,$(addsuffix .pyi,$(VISITOR_TARGETS)))

.PHONY: visitor-pyi
visitor-pyi:
	uv run -m scripts.transform_visitor_pyi $(VISITOR_TARGETS)
	uv run ruff format $(VISITOR_PYI_FULL_PATHS)
	uv run ruff check $(VISITOR_PYI_FULL_PATHS) --fix
	uv run pyright $(VISITOR_PYI_FULL_PATHS) tests/test_types.py


SYNC_VISITOR_FULL_PATHS = $(addprefix ast_lib/visitor/,$(addsuffix .py,$(VISITOR_TARGETS)))

# TODO: undo
.PHONY: sync-visitor
sync-visitor:
	uv run -m scripts.sync_visitor_with_pyi $(VISITOR_TARGETS)
	uv run ruff format $(SYNC_VISITOR_FULL_PATHS)
	uv run ruff check $(SYNC_VISITOR_FULL_PATHS) --fix
	uv run pyright $(SYNC_VISITOR_FULL_PATHS)


.PHONY: gen-nodes
gen-nodes:
	uv run -m scripts.gen_nodes
	uv run ruff format ast_lib/pattern/nodes.py
	uv run ruff check ast_lib/pattern/nodes.py --fix


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


.PHONY: typecheck
typecheck:
	uv run pyright ast_lib/


.PHONY: test-types
test-types:
	uv run pyright tests/test_types.py


.PHONY: test
test:
	uv run pytest tests/ --ignore=tests/test_types.py


.PHONY: test-visitor
test-visitor:
	uv run pytest tests/visitor/

.PHONY: test-patterns
test-patterns:
	uv run -m pytest tests/test_patterns.py -x

.PHONY: test-match
test-match:
	uv run -m pytest ./tests/test_match_pattern.py -x

