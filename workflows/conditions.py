"""Safe expression evaluator for workflow conditions."""

import ast


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

    Available variables:
    - document: the instance's document object
    - context: the instance's context dict
    - instance: the workflow instance itself
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
    namespace["document"] = instance.document
    namespace["context"] = instance.context or {}
    namespace["instance"] = instance

    result = eval(code, {"__builtins__": {}}, namespace)
    return bool(result)
