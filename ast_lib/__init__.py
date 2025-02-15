from ast_lib.pattern import nodes

from . import pattern
from .visitor import (
    # Core visitor
    BaseNodeVisitor,
    Hook,
    HookMode,
    NodeContextVar,
    NodeListCollector,
    NodeMapCollector,
    NodeReducer,
    NodeSetCollector,
    ParentMap,
    PureNodeVisitHook,
    SkipNode,
    node_context,
    node_reducer,
    nodelist_collector,
    nodemap_collector,
    nodeset_collector,
    pure_visit,
)


def dump(
    node: nodes.AST,
    annotate_fields=True,
    *,
    indent: int | str | None = None,
) -> str:
    """
    Return a formatted dump of the tree in node.  This is mainly useful for
    debugging purposes.  If annotate_fields is true (by default),
    the returned string will show the names and the values for fields.
    If annotate_fields is false, the result string will be more compact by
    omitting unambiguous field names.  Attributes such as line
    numbers and column offsets are not dumped by default.  If this is wanted,
    include_attributes can be set to true.  If indent is a non-negative
    integer or string, then the tree will be pretty-printed with that indent
    level. None (the default) selects the single line representation.
    """

    def _format(node, level=0):
        if isinstance(indent, str):
            level += 1
            prefix = "\n" + indent * level
            sep = ",\n" + indent * level
        else:
            prefix = ""
            sep = ", "
        if isinstance(node, nodes.AST):
            cls = type(node)
            args = []
            allsimple = True
            keywords = annotate_fields
            for name in node._fields:
                try:
                    value = getattr(node, name)
                except AttributeError:
                    keywords = True
                    continue
                if value is None and getattr(cls, name, ...) is None:
                    keywords = True
                    continue
                value, simple = _format(value, level)
                allsimple = allsimple and simple
                if keywords:
                    args.append("%s=%s" % (name, value))
                else:
                    args.append(value)
            if allsimple and len(args) <= 3:
                return "%s(%s)" % (node.__class__.__name__, ", ".join(args)), not args
            return "%s(%s%s)" % (node.__class__.__name__, prefix, sep.join(args)), False
        elif isinstance(node, list):
            if not node:
                return "[]", True
            return "[%s%s]" % (
                prefix,
                sep.join(_format(x, level)[0] for x in node),
            ), False
        return repr(node), True

    if indent is not None and not isinstance(indent, str):
        indent = " " * indent
    return _format(node)[0]


__all__ = (
    # Visitor
    # Core visitor
    "BaseNodeVisitor",
    "Hook",
    "HookMode",
    # Exception
    "SkipNode",
    # Context
    "NodeContextVar",
    "node_context",
    # Presets
    "ParentMap",
    "PureNodeVisitHook",
    "pure_visit",
    # Reducers and collectors
    "NodeReducer",
    "NodeListCollector",
    "NodeMapCollector",
    "NodeSetCollector",
    "node_reducer",
    "nodelist_collector",
    "nodemap_collector",
    "nodeset_collector",
    "dump",
)

# __all__ += nodes.__all__
__all__ += pattern.__all__
