# ? custom class e.g. ast_helper.ClassDef, ast_helper.Call, ast_helper.Name, ...
# ? custom tokens e.g. ?,`,~,;,$,{


"""
Supported types:

stmt =  | FunctionDef(identifier name, arguments args,
                    stmt* body, expr* decorator_list, expr? returns,
                    string? type_comment, type_param* type_params)
        | AsyncFunctionDef(identifier name, arguments args,
                            stmt* body, expr* decorator_list, expr? returns,
                            string? type_comment, type_param* type_params)

        | ClassDef(identifier name,
            expr* bases,
            keyword* keywords,
            stmt* body,
            expr* decorator_list,
            type_param* type_params)
        | Return(expr? value)

        | Delete(expr* targets)
        | Assign(expr* targets, expr value, string? type_comment)
        | #-x- TypeAlias(expr name, type_param* type_params, expr value)
        | #-x- AugAssign(expr target, operator op, expr value)
        -- 'simple' indicates that we annotate simple name without parens
        | AnnAssign(expr target, expr annotation, expr? value, int simple)

        -- use 'orelse' because else is a keyword in target languages
        | For(expr target, expr iter, stmt* body, stmt* orelse, string? type_comment)
        | AsyncFor(expr target, expr iter, stmt* body, stmt* orelse, string? type_comment)
        | While(expr test, stmt* body, stmt* orelse)
        | If(expr test, stmt* body, stmt* orelse)
        | With(withitem* items, stmt* body, string? type_comment)
        | AsyncWith(withitem* items, stmt* body, string? type_comment)

        | # TODO Match(expr subject, match_case* cases)

        | Raise(expr? exc, expr? cause)
        | Try(stmt* body, excepthandler* handlers, stmt* orelse, stmt* finalbody)
        | TryStar(stmt* body, excepthandler* handlers, stmt* orelse, stmt* finalbody)
        | Assert(expr test, expr? msg)

        | Import(alias* names)
        | ImportFrom(identifier? module, alias* names, int? level)

        | Global(identifier* names)
        | Nonlocal(identifier* names)
        | Expr(expr value)
        | Pass | Break | Continue

expr =  | #-x- BoolOp(boolop op, expr* values)
        | #-x- NamedExpr(expr target, expr value)
        | #-x- BinOp(expr left, operator op, expr right)
        | #-x- UnaryOp(unaryop op, expr operand)
        | #-x- Lambda(arguments args, expr body)
        | #-x- IfExp(expr test, expr body, expr orelse)
        | Dict(expr* keys, expr* values)
        | Set(expr* elts)
        | #-x- ListComp(expr elt, comprehension* generators)
        | #-x- SetComp(expr elt, comprehension* generators)
        | #-x- DictComp(expr key, expr value, comprehension* generators)
        | #-x- GeneratorExp(expr elt, comprehension* generators)
        -- the grammar constrains where yield expressions can occur
        | Await(expr value)
        | #-x- Yield(expr? value)
        | #-x- YieldFrom(expr value)
        -- need sequences for compare to distinguish between
        -- x < 4 < 3 and (x < 4) < 3
        | #-x- Compare(expr left, cmpop* ops, expr* comparators)
        | Call(expr func, expr* args, keyword* keywords)
        | #-x- FormattedValue(expr value, int conversion, expr? format_spec)
        | #-x- JoinedStr(expr* values)
        | Constant(constant value, string? kind)

        -- the following expression can appear in assignment context
        | Attribute(expr value, identifier attr, expr_context ctx)
        | Subscript(expr value, expr slice, expr_context ctx)
        | #-x- Starred(expr value, expr_context ctx)
        | Name(identifier id, expr_context ctx)
        | List(expr* elts, expr_context ctx)
        | Tuple(expr* elts, expr_context ctx)

        -- can appear only in Subscript
        | #-x- Slice(expr? lower, expr? upper, expr? step)
"""

"""
Convert string to match statement

Examples:
    return *.format(<args>)
    ->
    ast.Return(value=ast.Call(func=ast.Attribute(attr="format"), args=args))
    
    self.<attr>
    -> 
    ast.Attribute(value=ast.Name(id="self"), attr=attr)

    class *(CanvasObject)
    ->
    ast.ClassDef(bases=[ast.Name(id="CanvasObject")])

    property
    ->
    ast.Name(id="property") 

    *.request(*)
    ->
    Call(func=ast.Attribute(attr="request"))

    PaginatedList(*)
    ->
    Call(ast.Name(id="PaginatedList"))

    <target> = await? *.request(*)
    ->
    ast.Await(value=ast.Call(func=ast.Attribute(attr="request")))
       | ast.Call(func=ast.Attribute(attr="request")):

    def f(kwargs<arg() as kwargs>)
    ->
    ast.arguments(kwarg=ast.arg(arg="kwargs") as kwarg)

    <str() as value>
    ->
    ast.Constant(value=str() as value)
"""
