
if __name__ == "__main__":
    # todo: S-type, L-type

    class A(ast.NodeVisitor):
        class_name = NodeContextVar(
            ast.ClassDef,
            lambda node: node.name,
            default="",
        )

        @node_context(ast.ClassDef)
        def class_name2(self, node: ast.ClassDef) -> str:
            return node.name

        parent_map: NodeReducer[A, ast.AST, dict[ast.AST, ast.AST | None]] = (
            NodeReducer(
                ast.AST,
                lambda: dict(),
                lambda instance, acc, node: acc | {node: instance.current_node},
            )
        )

        @nodevar_collector(
            ast.AST, initial_value=lambda: dict[ast.AST, ast.AST | None]()
        )
        def parent_map2(self, prev, node: ast.AST) -> dict[ast.AST, ast.AST | None]:
            return self.parent_map

        current_node = NodeContextVar(ast.AST, lambda node: node)

        @node_context(ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        def qualname(
            self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ) -> str:
            return ".".join(self.qualname_namespace + [node.name])

        @node_context(
            ast.ClassDef,
            ast.FunctionDef,
            ast.AsyncFunctionDef,
            default_factory=lambda: [],
        )
        def qualname_namespace(
            self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ) -> list[str]:
            ns = self.qualname_namespace + [node.name]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                ns = ns + ["<locals>"]
            return ns

        @pure_visit(ast.FunctionDef, ast.AsyncFunctionDef)
        def visit_functions(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
            # type check
            assert_type(self.class_name, str)
            assert_type(self.current_node, ast.AST | None)
            assert_type(self.parent_map, dict[ast.AST, ast.AST | None])
            assert_type(self.parent_map2, dict[ast.AST, ast.AST | None])

            # print(self.class_name2, "->", node.name)
            # print(self.class_name, "->", node.name)

            def f():
                def g(): ...

            # if node.name == "g":
            #     print(self.qualname)

        @pure_visit(ast.ClassDef)
        def visit_class(self, node: ast.ClassDef):
            if node.name == "B":
                print(self.qualname)

    mod = ast.parse(open(__file__).read())
    # breakpoint()

    # print(A.__visit_hooks__)

    # A().visit(mod)

    ParentMap = dict[ast.AST, ast.AST | None]

    class Example(ast.NodeVisitor):
        @node_context(ast.ClassDef)
        def class_name(self, node: ast.ClassDef) -> str:
            return node.name

        @nodevar_collector(ast.AST, initial_value=lambda: dict(), return_type=ParentMap)
        def parent_map(self, prev: ParentMap, node: ast.AST) -> ParentMap:
            return prev | {node: self.current_node}

        current_node = NodeContextVar(ast.AST, lambda node: node)

        @pure_visit(ast.FunctionDef, ast.AsyncFunctionDef)
        def visit_functions(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
            # static type check

            # assert_type(self.current_node, ast.AST | None)
            # assert_type(self.parent_map, ParentMap)

            # print(self.class_name, "->", node.name)
            ...