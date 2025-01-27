from __future__ import annotations

# TODO: body
# TODO: unparse
# TODO: arguments.empty()
# TODO: decorator_list empty?
import ast
import copy
import operator
from pathlib import Path
from typing import IO, Any, cast

from ast_lib.utils import expand_union, parse_as_expr, parse_as_stmt
from ast_lib.visitor import (
    BaseNodeVisitor,
    SkipNode,
    node_context,
    nodelist_collector,
    nodemap_collector,
    pure_visit,
)
from ast_lib.visitor.exception import SkipVisit
from ast_lib.visitor.presets import ParentMap

INPUT = Path(__file__).parent / "data" / "ast.pyi"
OUTPUT = Path() / "ast_lib" / "nodes.py"


CUSTOM_BASES = ("arguments",)


def wrap_leaf_type(
    node: ast.AST, wrapper: str, abort_subscript_ids: tuple[str, ...] = ()
) -> ast.expr:
    """
    Write the leaf type of the node by `wrapper`
    """
    match node:
        case ast.Module(body=[ast.Expr(expr)]):
            pass
        case ast.stmt(body=[ast.Expr(expr)]):
            pass
        case ast.expr():
            expr = node
        case _:
            raise ValueError(f"Unsupported node:\n{ast.dump(node)}")

    def wrap_expr(node: ast.expr) -> ast.expr:
        def recur[T](node: T, is_first: bool) -> tuple[T | ast.expr, bool]:
            if not isinstance(node, ast.expr):
                return node, False

            expand_classes = (ast.List, ast.Tuple, ast.Subscript)
            has_changed = False
            match node:
                case ast.Subscript(value=ast.Name(id)):
                    abort = id in abort_subscript_ids
                case _:
                    abort = False

            should_propagate = isinstance(node, expand_classes) and not abort

            for field, old_value in ast.iter_fields(node):
                if abort:
                    continue

                if isinstance(node, ast.Subscript) and field == "value":
                    continue

                if isinstance(old_value, list):
                    new_values = []
                    for value in old_value:
                        value, child_has_changed = recur(value, should_propagate)
                        new_values.append(value)

                        has_changed |= child_has_changed

                    old_value[:] = new_values
                elif isinstance(old_value, ast.AST):
                    new_node, child_has_changed = recur(old_value, should_propagate)
                    setattr(node, field, new_node)

                    has_changed |= child_has_changed

            # if should_propagate:
            #     breakpoint()
            #     assert has_changed

            if not should_propagate and is_first and not has_changed:
                new_node = ast.Subscript(
                    value=ast.Name(id=wrapper), slice=node, ctx=ast.Load()
                )
                return new_node, True

            return node, False

        # breakpoint()
        return recur(node, True)[0]

    return wrap_expr(expr)


def test_wrap_expr():
    test_cases = {
        "a[b]": "a[Wrapper[b]]",
        "a[b, c]": "a[Wrapper[b], Wrapper[c]]",
        "a[[b, c], d]": "a[[Wrapper[b], Wrapper[c]], Wrapper[d]]",
        "a[b.c]": "a[Wrapper[b.c]]",
        "a[c()]": "a[Wrapper[c()]]",
        "a[b.c(d)]": "a[Wrapper[b.c(d)]]",
        "a[b[c]]": "a[b[Wrapper[c]]]",
        "a[b.c()[[d], [e]]]": "a[b.c()[[Wrapper[d]], [Wrapper[e]]]]",
        #
        "Literal[a]": "Wrapper[Literal[a]]",
        "Literal[True,False]": "Wrapper[Literal[True, False]]",
    }

    for case, expected in test_cases.items():
        node = ast.parse(case)
        got = ast.unparse(wrap_leaf_type(node, "Wrapper", ("Literal",)))
        if got != expected:
            print(case)
            print("Expected:", expected)
            print("Actual:", got)
            print()
            # break


# test_wrap_expr()
# exit()


# class Transformer(ast.NodeTransformer, BaseNodeVisitor):


class CollectASTClasses(BaseNodeVisitor):
    EXTRA_CLASSES = ("_Slice",)

    parent_map = ParentMap()

    @nodemap_collector(ast.ClassDef, mode="before", get_key=lambda node: node.name)
    def class_bases_map(self, node: ast.ClassDef) -> list[str]:
        return [base.id for base in node.bases if isinstance(base, ast.Name)]

    def all_ancestors(self, cls_name: str) -> list[str]:
        ancestors: set[str] = {cls_name}
        for base_name in self.class_bases_map.get(cls_name, []):
            ancestors.update(self.all_ancestors(base_name))
        return list(ancestors)

    @nodelist_collector(ast.ClassDef, mode="before")
    def ast_classes(self, node: ast.ClassDef) -> str:
        def recur(cls_name: str) -> bool:
            if cls_name == "AST":
                return True
            for base_name in self.class_bases_map.get(cls_name, []):
                if recur(base_name):
                    return True
            return False

        if recur(node.name):
            return node.name

        raise SkipNode(node)


class Visitor(BaseNodeVisitor):
    EXCLUDE_TRANSFORM_BASES = {"mod"}

    EMPTY_FIELD_CLASSES = (
        "AST",
        "mod",
        "stmt",
        "expr",
        "type_param",
    )

    EXCLUDE_FIELDS = (
        "body",
        "orelse",
        "type_comment",
        "type_params",
        "ctx",
    )

    VERSION = (3, 12)

    def __init__(self, file: IO[str], ast_classes: set[str]):
        super().__init__()
        self.file = file
        self.ast_classes = ast_classes

    def print(self, *args, **kwargs):
        print(*args, **kwargs, file=self.file)

    debug = set()

    @nodemap_collector(ast.ClassDef, mode="before", get_key=lambda node: node.name)
    def class_bases_map(self, node: ast.ClassDef) -> list[str]:
        return [base.id for base in node.bases if isinstance(base, ast.Name)]

    @nodemap_collector(ast.ClassDef, mode="before", get_key=lambda node: node.name)
    def class_name_to_node(self, node: ast.ClassDef) -> ast.ClassDef:
        return node

    def all_ancestors(self, cls_name: str) -> list[str]:
        ancestors: set[str] = {cls_name}
        for base_name in self.class_bases_map.get(cls_name, []):
            ancestors.update(self.all_ancestors(base_name))
        return list(ancestors)

    # @nodelist_collector(ast.ClassDef, mode="before")
    # def ast_classes(self, node: ast.ClassDef) -> str | None:
    #     def recur(cls_name: str) -> bool:
    #         if cls_name == "AST":
    #             return True
    #         for base_name in self.class_bases_map.get(cls_name, []):
    #             if recur(base_name):
    #                 return True
    #         return False

    #     if recur(node.name):
    #         # print(node.name)
    #         # breakpoint()
    #         return node.name

    #     return None

    @node_context(ast.ClassDef)
    def current_ast_class(self, node: ast.ClassDef) -> str:
        if node.name in self.ast_classes:
            return node.name
        raise SkipNode(node)

    def handle_class(self, node: ast.ClassDef) -> bool:
        excludes = ("AST", "stmt", "expr")
        return (
            node.name in self.ast_classes
            and not node.decorator_list
            and node.name not in excludes
        )

    @pure_visit(ast.If)
    def visit_if(self, node: ast.If):
        if not self.current_ast_class:
            return

        match node.test:
            case ast.Compare(
                left,
                ops=[op_node],
                comparators=[ast.Tuple([ast.Constant(major), ast.Constant(minor)])],
            ):
                pass
            case _:
                raise ValueError(f"Unexpected test: {ast.dump(node.test)}")
        assert ast.unparse(left) == "sys.version_info"

        op_map = {
            ast.Lt: operator.lt,
            ast.LtE: operator.le,
            ast.Gt: operator.gt,
            ast.GtE: operator.ge,
        }

        branch_version = (major, minor)
        op = op_map[cast(Any, type(op_node))]

        if op(branch_version, self.VERSION):
            body = node.body
        else:
            body = node.orelse

        for child in body:
            self.visit(child)

        raise SkipVisit(node)

    @node_context(ast.ClassDef)
    def class_init(self, node: ast.ClassDef) -> list[ast.FunctionDef]:
        if self.handle_class(node):
            return []
        raise SkipNode(node)

    @pure_visit(ast.FunctionDef)
    def visit_func(self, node: ast.FunctionDef):
        if self.class_init is None:
            return

        if node.name != "__init__":
            return

        arg_names = [x.arg for x in node.args.args]
        assert set(self.field_names) >= set(arg_names) - {"self"}

        self.class_init.append(node)

    @node_context(ast.ClassDef)
    def ast_fields(self, node: ast.ClassDef) -> list[ast.AnnAssign]:
        if self.handle_class(node):
            return []
        raise SkipNode(node)

    @property
    def field_names(self) -> list[str]:
        assert self.ast_fields is not None
        names = [x.target.id for x in self.ast_fields if isinstance(x.target, ast.Name)]
        assert len(names) == len(self.ast_fields), (names, self.ast_fields)
        return names

    @node_context(ast.ClassDef)
    def child_fields(self, node: ast.ClassDef) -> list[str]:
        if self.handle_class(node):
            return []
        raise SkipNode(node)

    def is_child_field(self, node: ast.AST) -> bool:
        match node:
            case ast.Name(id):
                return id in self.ast_classes
            case ast.BinOp():
                for union_type in expand_union(node):
                    if self.is_child_field(union_type):
                        return True
                return False
            case ast.Subscript(value=ast.Name("list"), slice=ast.Name(id)):
                # print(ast.unparse(node))
                # breakpoint()
                return id in self.ast_classes
            case _:
                return False

    @pure_visit(ast.AnnAssign, mode="before")
    def append_field(self, node: ast.AnnAssign):
        # * Do we handle current class?
        if self.ast_fields is None:
            return

        if self.current_ast_class in self.EMPTY_FIELD_CLASSES:
            return

        match node.target:
            case ast.Name(field_id):
                pass
            case _:
                raise ValueError(f"Unexpected target: {ast.dump(node.target)}")

        # * Do we handle this field?
        # if id in self.EXCLUDE_FIELDS:
        #     return

        # * Process annotation
        original_annotation = node.annotation
        match original_annotation:
            case ast.Name("_Identifier"):
                is_id = True
            case _:
                is_id = False

        is_subscript = isinstance(node.annotation, ast.Subscript)
        original_annotation = copy.deepcopy(node.annotation)

        assert self.child_fields is not None
        if self.is_child_field(node.annotation):
            self.child_fields.append(field_id)

        node.annotation = wrap_leaf_type(node.annotation, "ASTPattern", ("Literal",))
        if is_id:
            node.annotation = ast.BinOp(
                left=node.annotation,
                op=ast.BitOr(),
                right=ast.Name("WildcardId", ast.Load()),
            )
        if is_subscript:
            # TODO? ASTPattern[ASTPattern[list[T]]]
            # list[T] -> list[ASTPattern[T]] | ASTPattern[list[T]]
            node.annotation = ast.BinOp(
                left=node.annotation,
                op=ast.BitOr(),
                right=ast.Subscript(parse_as_expr("ASTPattern"), original_annotation),
            )

        # * Add default factory
        try:
            assert node.value is None
        except Exception:
            # print(
            #     ast.unparse(self.class_name_to_node[self.current_ast_class]),
            # )
            breakpoint()
        if is_id:
            node.value = parse_as_expr("Field(default_factory=WildcardId)")
        else:
            node.value = parse_as_expr("Field(default_factory=Wildcard)")

        self.ast_fields.append(node)

    @nodelist_collector(
        ast.ClassDef, mode="after", before=("ast_fields", "child_fields", "class_init")
    )
    def transformed_classes(self, node: ast.ClassDef):
        if not self.handle_class(node):
            return
        assert self.ast_fields is not None
        assert self.child_fields is not None

        ancestors = self.all_ancestors(node.name)
        if self.EXCLUDE_TRANSFORM_BASES & set(ancestors):
            return

        node.decorator_list = [parse_as_expr("dataclass(frozen=True)")]
        node.body = cast(list[ast.stmt], self.ast_fields.copy())
        if node.name in CUSTOM_BASES:
            node.bases.append(parse_as_expr(f"_{node.name}"))

        assert node.name in ast.__dict__
        fields = ast.__dict__[node.name]._fields
        ast_field_names = {ast.unparse(f.target) for f in self.ast_fields}
        assert set(fields) <= ast_field_names | set(self.EXCLUDE_FIELDS), (
            f"{node.name}: fields {fields} not in {ast_field_names}"
        )
        fields_ann = parse_as_stmt(
            f"_field_names: ClassVar[tuple[str, ...]]={repr(fields)}"
        )
        node.body.append(fields_ann)

        node.body.append(
            parse_as_stmt(
                f"_child_fields: ClassVar[tuple[str, ...]]={repr(tuple(self.child_fields))}"
            )
        )

        args_typeddict_name = f"{node.name}Args"
        args_typeddict: ast.ClassDef = parse_as_stmt(
            f"class {args_typeddict_name}(TypedDict, total=False): ...", ast.ClassDef
        )
        args_typeddict.body = []
        for field in self.ast_fields:
            field = copy.deepcopy(field)
            field.value = None
            args_typeddict.body.append(field)
        if not args_typeddict.body:
            args_typeddict.body.append(parse_as_stmt("pass"))
        node.body.append(args_typeddict)

        replace_args = ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg="self")],
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            # kwarg=ast.arg(arg="kwargs", annotation=parse_as_expr("Never")),
            kwarg=ast.arg(
                arg="kwargs", annotation=parse_as_expr(f"Unpack[{args_typeddict_name}]")
            ),
            defaults=[],
        )
        replace_fn = ast.FunctionDef(
            name="replace",
            args=replace_args,
            body=[parse_as_stmt("return super().replace(**kwargs)")],
            decorator_list=[],
            # decorator_list=[parse_as_expr("overload")],
            returns=ast.Name("Self"),
            type_params=[],
        )

        node.body.append(ast.fix_missing_locations(replace_fn))

        self.print(ast.unparse(node))

        return node


class CustomExportPrinter(BaseNodeVisitor):
    def __init__(self, file: IO[str]):
        super().__init__()
        self.file = file

    def print(self, *args, **kwargs):
        print(*args, **kwargs, file=self.file)

    @pure_visit(ast.ClassDef, ast.TypeAlias, mode="before")
    def visit_class_or_type(self, node: ast.ClassDef | ast.TypeAlias):
        match node:
            case ast.ClassDef(name):
                pass
            case ast.TypeAlias(ast.Name(id=name)):
                pass
            case _:  # pyright: ignore
                raise ValueError(f"Unexpected node: {ast.dump(node)}")

        if name in CUSTOM_BASES:
            return
        self.print(f"{repr(name)},")


if __name__ == "__main__":
    with open(INPUT) as f:
        ast_typeshed = f.read()

    mod = ast.parse(ast_typeshed)
    with open(OUTPUT, "r+") as f:
        content = f.read()

        suf_idx = content.index("### End\n")
        suffix = content[suf_idx:]

        start_idx = content.index("### Start\n") + len("### Start\n")
        header = content[:start_idx]

        # print(header)

        f.seek(0)
        f.truncate()
        f.write(header)
        f.write("\n")

        try:
            collector = CollectASTClasses()
            collector.visit(mod)
            ast_classes = set(collector.ast_classes) | set(collector.EXTRA_CLASSES)

            transformer = Visitor(f, ast_classes)
            transformer.visit(mod)

            print("--debug--")
            print(transformer.debug)
            print("--debug--")
            # print(transformer.tmp)

            transformer.print("__all__ = (")
            for cls in dict.fromkeys(transformer.transformed_classes):
                if cls is not None:
                    # print(cls.name)
                    # breakpoint()
                    transformer.print(f"{repr(cls.name)},")

            printer = CustomExportPrinter(f)
            printer.visit(ast.parse(header))
            printer.visit(ast.parse(suffix))
            transformer.print(")")

        except Exception:
            f.seek(0)
            f.write(content)
            raise

        f.write("\n")
        f.write(suffix)
