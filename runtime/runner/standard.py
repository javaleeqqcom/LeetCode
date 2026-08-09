from __future__ import annotations

import ast
import builtins
import math
from pathlib import Path
from typing import Any


ALLOWED_IMPORTS = frozenset(
    {
        "bisect",
        "collections",
        "decimal",
        "fractions",
        "functools",
        "heapq",
        "itertools",
        "math",
        "operator",
        "random",
        "re",
        "statistics",
        "string",
        "typing",
    }
)
BLOCKED_CALLS = frozenset(
    {
        "breakpoint",
        "compile",
        "eval",
        "exec",
        "globals",
        "input",
        "locals",
        "open",
        "vars",
        "__import__",
    }
)


class StandardSourceError(ValueError):
    pass


def validate_standard_source(source: str, method_name: str) -> None:
    """Validate the fast, base-JSON OJ subset.

    This validator reduces accidental capabilities and makes the worker PyPy
    compatible.  It is not a replacement for the native OS sandbox.
    """

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise StandardSourceError(str(exc)) from exc
    solution_classes = [
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Solution"
    ]
    if len(solution_classes) != 1:
        raise StandardSourceError("standard mode requires exactly one Solution class")
    methods = {
        node.name
        for node in solution_classes[0].body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    if method_name not in methods:
        raise StandardSourceError(f"Solution.{method_name} is missing")

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            for name in names:
                root = name.split(".", 1)[0]
                if root not in ALLOWED_IMPORTS:
                    raise StandardSourceError(f"import is not allowed in standard mode: {root}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in BLOCKED_CALLS:
                raise StandardSourceError(f"call is not allowed: {node.func.id}")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise StandardSourceError(f"dunder attribute access is not allowed: {node.attr}")


def _safe_import(
    name: str,
    globals_: dict[str, Any] | None = None,
    locals_: dict[str, Any] | None = None,
    fromlist: tuple[str, ...] = (),
    level: int = 0,
) -> Any:
    if level:
        raise ImportError("relative imports are disabled in standard OJ mode")
    root = name.split(".", 1)[0]
    if root not in ALLOWED_IMPORTS:
        raise ImportError(f"module is not allowed in standard OJ mode: {root}")
    return builtins.__import__(name, globals_, locals_, fromlist, level)


def load_standard_solution(
    source: str, method_name: str, filename: str = "<oj-solution>"
) -> type:
    validate_standard_source(source, method_name)
    safe_builtins = dict(vars(builtins))
    for blocked in BLOCKED_CALLS:
        safe_builtins.pop(blocked, None)
    safe_builtins["__import__"] = _safe_import
    namespace: dict[str, Any] = {
        "__builtins__": safe_builtins,
        "__name__": "oj_submission",
        "math": math,
    }
    exec(compile(source, filename, "exec"), namespace)
    return namespace["Solution"]


def normalize_standard_output(value: Any, _seen: set[int] | None = None) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite float output is not supported")
        return value
    if _seen is None:
        _seen = set()
    value_id = id(value)
    if value_id in _seen:
        raise ValueError("cyclic output is not supported")
    if isinstance(value, (list, tuple)):
        _seen.add(value_id)
        try:
            return [normalize_standard_output(item, _seen) for item in value]
        finally:
            _seen.remove(value_id)
    if isinstance(value, dict):
        _seen.add(value_id)
        try:
            result = {}
            for key, item in value.items():
                if not isinstance(key, (str, int)):
                    raise TypeError("dict output keys must be str or int")
                result[key] = normalize_standard_output(item, _seen)
            return result
        finally:
            _seen.remove(value_id)
    raise TypeError(f"unsupported standard OJ output: {type(value).__name__}")
