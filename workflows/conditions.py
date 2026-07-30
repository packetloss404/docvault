"""Safe expression evaluator for workflow conditions."""

import ast
from datetime import date, datetime
from decimal import Decimal


class SafeExpressionObject:
    """Attribute-access wrapper around primitive expression data."""

    def __init__(self, data):
        self._data = data

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(name)

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()


# Whitelisted AST node types for safe evaluation
SAFE_NODES = (
    ast.Expression,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.Is,
    ast.IsNot,
    ast.In,
    ast.NotIn,
    ast.BinOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.FloorDiv,
    ast.UnaryOp,
    ast.Not,
    ast.USub,
    ast.UAdd,
    ast.IfExp,
    ast.Attribute,
    ast.Subscript,
    ast.Index,  # Python 3.8 compat
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Tuple,
    ast.List,
    ast.Call,
    ast.keyword,
    ast.Starred,
)

# Allowed built-in names
SAFE_NAMES = {
    "True": True,
    "False": False,
    "None": None,
    "len": len,
}

# Names that can be called as functions
SAFE_CALLABLE_NAMES = {"len"}

# Methods that can be called on objects
SAFE_METHODS = {"get", "keys", "values", "items", "startswith", "endswith",
                "lower", "upper", "strip", "count"}


class UnsafeExpressionError(Exception):
    """Raised when an expression contains unsafe AST nodes."""
    pass


def _validate_ast(node):
    """Recursively validate that all AST nodes are in the whitelist."""
    if not isinstance(node, SAFE_NODES):
        raise UnsafeExpressionError(
            f"Unsafe expression: {type(node).__name__} is not allowed."
        )

    # Block dunder attribute access
    if isinstance(node, ast.Attribute):
        if node.attr.startswith("__") and node.attr.endswith("__"):
            raise UnsafeExpressionError(
                f"Unsafe expression: access to '{node.attr}' is not allowed."
            )

    # Validate Call nodes - only allow safe callables
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name):
            # Direct function call like len()
            if func.id not in SAFE_CALLABLE_NAMES:
                raise UnsafeExpressionError(
                    f"Unsafe expression: calling '{func.id}' is not allowed."
                )
        elif isinstance(func, ast.Attribute):
            # Method call like context.get()
            if func.attr not in SAFE_METHODS:
                raise UnsafeExpressionError(
                    f"Unsafe expression: calling method '{func.attr}' is not allowed."
                )
        else:
            raise UnsafeExpressionError(
                "Unsafe expression: indirect function calls are not allowed."
            )

    for child in ast.iter_child_nodes(node):
        _validate_ast(child)


def evaluate_condition(expression, instance):
    """
    Safely evaluate a condition expression in the context of a workflow instance.

    Available variables are primitive snapshots, not live Django model objects:
    - document: selected document fields
    - context: workflow context dict
    - instance: selected workflow instance fields
    - True, False, None, len

    Returns the boolean result of the expression.
    Raises UnsafeExpressionError if the expression contains disallowed constructs.
    """
    if not expression or not expression.strip():
        return True

    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as e:
        raise UnsafeExpressionError(f"Invalid expression syntax: {e}")

    _validate_ast(tree)

    code = compile(tree, "<condition>", "eval")

    namespace = dict(SAFE_NAMES)
    namespace["document"] = _build_document_context(instance.document)
    namespace["context"] = _to_safe_value(instance.context or {})
    namespace["instance"] = _build_instance_context(instance)

    result = eval(code, {"__builtins__": {}}, namespace)
    return bool(result)


def _to_safe_value(value, depth=0):
    """Convert values exposed to condition expressions into primitives."""
    if depth > 5:
        return None
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return SafeExpressionObject({
            str(key): _to_safe_value(item, depth + 1)
            for key, item in value.items()
        })
    if isinstance(value, (list, tuple, set)):
        return [_to_safe_value(item, depth + 1) for item in value]
    return str(value)


def _safe_attr(obj, name, default=None):
    """Read a simple attribute without exposing the object itself."""
    try:
        return _to_safe_value(getattr(obj, name, default))
    except Exception:
        return default


def _safe_related(obj, name, fields):
    """Return primitive fields from a related object if present."""
    try:
        related = getattr(obj, name, None)
    except Exception:
        return None
    if related is None:
        return None
    return SafeExpressionObject({
        field: _safe_attr(related, field)
        for field in fields
    })


def _build_document_context(document):
    """Build the document snapshot available to workflow conditions."""
    return SafeExpressionObject({
        "id": _safe_attr(document, "id"),
        "title": _safe_attr(document, "title"),
        "original_filename": _safe_attr(document, "original_filename"),
        "filename": _safe_attr(document, "filename"),
        "content": _safe_attr(document, "content"),
        "mime_type": _safe_attr(document, "mime_type"),
        "language": _safe_attr(document, "language"),
        "checksum": _safe_attr(document, "checksum"),
        "archive_serial_number": _safe_attr(document, "archive_serial_number"),
        "page_count": _safe_attr(document, "page_count"),
        "created": _safe_attr(document, "created"),
        "modified": _safe_attr(document, "modified"),
        "added": _safe_attr(document, "added"),
        "is_held": _safe_attr(document, "is_held"),
        "owner_id": _safe_attr(document, "owner_id"),
        "document_type_id": _safe_attr(document, "document_type_id"),
        "correspondent_id": _safe_attr(document, "correspondent_id"),
        "cabinet_id": _safe_attr(document, "cabinet_id"),
        "storage_path_id": _safe_attr(document, "storage_path_id"),
        "document_type": _safe_related(document, "document_type", ("id", "name")),
        "correspondent": _safe_related(document, "correspondent", ("id", "name")),
        "cabinet": _safe_related(document, "cabinet", ("id", "name")),
        "storage_path": _safe_related(document, "storage_path", ("id", "name", "path")),
    })


def _build_instance_context(instance):
    """Build the workflow instance snapshot available to conditions."""
    return SafeExpressionObject({
        "id": _safe_attr(instance, "id"),
        "context": _to_safe_value(getattr(instance, "context", {}) or {}),
        "launched_at": _safe_attr(instance, "launched_at"),
        "state_changed_at": _safe_attr(instance, "state_changed_at"),
        "is_complete": _safe_attr(instance, "is_complete", False),
        "workflow": _safe_related(
            instance,
            "workflow",
            ("id", "label", "internal_name", "auto_launch"),
        ),
        "current_state": _safe_related(
            instance,
            "current_state",
            ("id", "label", "initial", "final", "order"),
        ),
    })
