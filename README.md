# `ast_lib`

**🚧 This library is currently under development.**

A Python library for pattern matching and traversing AST nodes with a simple DSL syntax and powerful visitor framework.

## Pattern Matching DSL

Traditional AST matching often requires verbose nested type checks:

```python
# Traditional approach
def is_method_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Attribute):
        return False
    if not isinstance(node.func.value, ast.Name):
        return False
    if node.func.value.id != "self":
        return False
    return True

# Check if node is a "self.method()" call
if is_method_call(node):
    method_name = node.func.attr
    # Handle method call...
```

Python 3.10 introduced pattern matching which helps reduce some verbosity:

```python
def is_method_call(node: ast.AST) -> bool:
    match node:
        case ast.Call(
            func=ast.Attribute(
                value=ast.Name(id="self"),
                attr=_
            )
        ):
            return True
        case _:
            return False

# Still verbose and requires knowledge of AST structure
if is_method_call(node):
    match node:
        case ast.Call(func=ast.Attribute(attr=method_name)):
            # Handle method call...
            pass
```

However, both approaches have drawbacks:

1. Require deep knowledge of AST node structure
2. Need constant reference to AST documentation
3. Code intent is obscured by implementation details
4. Pattern matching becomes unwieldy for complex structures

This library provides a simpler DSL that matches AST patterns using familiar Python syntax:

```python
from ast_lib.pattern import parse_pattern

# Match method calls with a simple pattern
pattern = parse_pattern("self.method()")
if (match := pattern.match(node)):
    # Handle matched method call...
    pass

# Use wildcards to match any expression
pattern = parse_pattern("~.method()")  # Matches: obj.method(), a.b.method(), x[0].method()

# Capture parts of the pattern
pattern = parse_pattern("$obj.$method($arg)")
if (match := pattern.match(node)):
    obj = match.kw_groups["obj"]       # The receiver expression
    method = match.kw_groups["method"] # The method name
    arg = match.kw_groups["arg"]      # The argument
```

We add a custom **wildcard** symbol to match against roughly _anything that fits in the position_.

> 🚧 The wildcard is `~` for now, which clashes with Python's bitwise inversion operator. This will be changed in a future version.

### Node Classes

The `parse_pattern` function returns pattern nodes that mirror the structure of Python's AST:

```python
# Pattern nodes correspond to ast nodes
pattern = parse_pattern("self.method()")
assert isinstance(pattern, ast_lib.Call)
assert isinstance(pattern.func, ast_lib.Attribute)
print(ast_lib.dump(pattern, indent=2))
'''
Expr(
  value=Call(
    func=Attribute(
      value=Name(id='self', ctx=Wildcard()),
      attr='method',
      ctx=Wildcard()),
    args=[],
    keywords=Wildcard()))
'''

# Access pattern structure
print(pattern.fields)        # Get node fields
print(pattern.ast_class)     # Get corresponding ast class

# Create modified patterns
new_pattern = pattern.replace(func=ast_lib.Name("other_method"))
```

By default, most fields not specified will be `Wildcard()`. You can use `replace` to narrow the matching by substituting specific fields (e.g., `Call.ctx`).

### Match Utilities

The library provides utilities for working with matched patterns:

```python
from ast_lib.pattern import MatchTypeHint, match_first, match_all
from typing import TypedDict

class MethodCall(TypedDict):
    obj: ast.expr
    method: str
    args: list[ast.expr]

# Type-safe pattern matching
hint = MatchTypeHint[MethodCall]()
if (match := pattern.match(node, match_type_hint=hint)):
    obj = match.kw_groups["obj"]      # Type: ast.expr
    method = match.kw_groups["method"] # Type: str
    args = match.kw_groups["args"]    # Type: list[ast.expr]

# Find first/all matches in a tree
matches = match_all(pattern, tree.body)
if (match := match_first(pattern, tree.body)):
    # Handle first match...
```

The type hint is only for static type-checking and does not affect runtime behavior.

## Visitor Framework

When processing AST trees, we often need to:

1. Track contextual information (e.g., current class/function)
2. Compute node relationships (e.g., parent nodes)
3. Collect nodes matching certain patterns
4. Apply transformations based on patterns

The library provides a visitor framework based on hooks that makes these tasks easier. All hooks are subclasses of `HookProvider`, which you can extend to create custom hooks:

```python
from ast_lib import BaseNodeVisitor, node_context, ParentMap

class MyVisitor(BaseNodeVisitor):
    # Track parent nodes
    parent_map = ParentMap()

    # Track context during traversal
    @node_context(ast.FunctionDef)
    def current_function(self, node: ast.FunctionDef) -> str:
        return node.name

    # Collect nodes
    @nodelist_collector(ast.FunctionDef)
    def function_names(self, node: ast.FunctionDef) -> str:
        return node.name

    # Match patterns
    @node_context(ast.Call, pattern="$obj.method($arg)")
    def handle_method_call(self, node: ast.Call, match_result: MatchResult) -> None:
        obj = match_result.kw_groups["obj"]
        arg = match_result.kw_groups["arg"]
        # Handle matched method call
```

Hooks can be controlled using different modes:

-   `before`: Run before visiting children
-   `after`: Run after visiting children
-   `wrap`: Wrap the visit of children (useful for context managers)

```python
class MyVisitor(BaseNodeVisitor):
    @node_context(ast.FunctionDef, mode="wrap")
    def track_function(self, node: ast.FunctionDef) -> ContextManager:
        return some_context_manager()

    @node_context(ast.Call, mode="before", pattern="$obj.method()")
    def handle_method(self, node: ast.Call) -> None:
        # Handle method before visiting children
        pass
```

Here's a real-world example that collects all class names and their base classes from a module:

```python
import ast
from ast_lib import BaseNodeVisitor, node_context, nodemap_collector

class ClassHierarchyVisitor(BaseNodeVisitor):
    """Collect class inheritance information from a module"""

    # Track the current class's qualified name
    @node_context(ast.ClassDef, default_factory=lambda: [])
    def class_namespace(self, node: ast.ClassDef) -> list[str]:
        return self.class_namespace + [node.name]

    @property
    def current_class_name(self) -> str:
        return ".".join(self.class_namespace)

    # Collect class definitions with their base classes

    def get_qualname(self, node: ast.ClassDef) -> str:
        return self.current_class_name

    @nodemap_collector(ast.ClassDef, get_key=get_qualname)
    def class_hierarchy(self, node: ast.ClassDef) -> list[str]:
        # Extract base class names
        base_names = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_names.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_names.append(base.attr)
        return base_names


# Usage:
source = """
class Animal:
    pass

class Mammal(Animal):
    class Dog(Animal):  # Nested class
        pass

    class Cat(Animal):
        pass

class Bird(Animal):
    pass
"""

visitor = ClassHierarchyVisitor()
tree = ast.parse(source)
visitor.visit(tree)

# Results:
print(visitor.class_hierarchy)
"""
{
    'Animal': [],
    'Mammal': ['Animal'],
    'Mammal.Dog': ['Animal'],
    'Mammal.Cat': ['Animal'],
    'Bird': ['Animal']
}
"""
```

This example demonstrates several key features:

1. Context tracking with `class_namespace` to handle nested classes
2. Node collection with `nodemap_collector` to build the hierarchy map
3. Automatic state management - no need to manually track the current class
4. Clean separation of concerns between collection and traversal logic
