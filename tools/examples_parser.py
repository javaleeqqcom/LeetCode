"""Parse JSON-like and LeetCode-style text test cases.

The parser intentionally uses :func:`ast.literal_eval` instead of ``eval``.
It accepts both Chinese and English section labels and preserves keywords
inside quoted strings while translating JSON's null/true/false literals.
"""

from __future__ import annotations

import ast
import os
import re
from typing import Any, Dict, List, Optional, Tuple


_SECTION_RE = re.compile(
    r"^\s*(input|输入|output|输出|expected|预期结果)\s*[：:]?\s*(.*)$",
    flags=re.IGNORECASE,
)
_INPUT_LABELS = {"input", "输入"}
_OUTPUT_LABELS = {"output", "输出"}
_EXPECTED_LABELS = {"expected", "预期结果"}


def json_keywords_to_python(text: str) -> str:
    """Translate unquoted JSON keywords to Python literal spellings."""

    def replacer(match: re.Match[str]) -> str:
        token = match.group(0)
        if token.startswith(('"', "'")):
            return token
        return {"null": "None", "true": "True", "false": "False"}[token.lower()]

    pattern = r'''"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|\b(?:null|true|false)\b'''
    return re.sub(pattern, replacer, text, flags=re.IGNORECASE)


def _literal(text: str) -> Any:
    text = json_keywords_to_python(text.strip())
    if not text:
        raise ValueError("测试用例的值为空")
    return ast.literal_eval(text)


def _parse_keyword_call(text: str) -> Optional[Dict[str, Any]]:
    """Parse ``a = 1, b = [2, 3]`` without splitting nested commas."""
    source = json_keywords_to_python(text.strip())
    try:
        expr = ast.parse(f"_case_({source})", mode="eval").body
    except SyntaxError:
        return None
    if not isinstance(expr, ast.Call) or expr.args or not expr.keywords:
        return None
    if any(keyword.arg is None for keyword in expr.keywords):
        return None
    try:
        return {
            keyword.arg: ast.literal_eval(keyword.value)
            for keyword in expr.keywords
            if keyword.arg is not None
        }
    except (TypeError, ValueError):
        return None


def _parse_input_text(text: str, params_num: Optional[int]) -> Tuple[Any, ...] | Dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("输入区段为空")

    # Standard LeetCode display: ``nums = [...], target = 0``.
    kwargs = _parse_keyword_call(" ".join(text.splitlines()))
    if kwargs is not None:
        return kwargs

    # One assignment per line, including the legacy two-line ``name =`` form.
    assignments: Dict[str, Any] = {}
    pending_name: Optional[str] = None
    raw_lines: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if pending_name is not None:
            assignments[pending_name] = _literal(line)
            pending_name = None
            continue
        match = re.match(r"^([A-Za-z_]\w*)\s*=\s*(.*)$", line)
        if match:
            name, value_text = match.groups()
            if value_text:
                assignments[name] = _literal(value_text.rstrip(","))
            else:
                pending_name = name
        else:
            raw_lines.append(line)

    if pending_name is not None:
        raise ValueError(f"参数 {pending_name} 缺少值")
    if assignments:
        if raw_lines:
            raise ValueError("输入区段同时包含命名参数和未命名值")
        return assignments

    value = _literal("\n".join(raw_lines))
    if isinstance(value, tuple):
        return value
    if params_num == 1:
        return (value,)
    if isinstance(value, list) and params_num == len(value):
        return tuple(value)
    raise ValueError(
        "无参数名的 Input 无法确定参数边界；"
        "请使用元组、命名参数，或提供正确的 params_num"
    )


def _parse_dict_style_case(lines: List[str], params_num: Optional[int] = None) -> dict:
    """Compatibility wrapper for one labeled case block."""
    cases = _parse_labeled_cases("\n".join(lines), params_num)
    if len(cases) != 1:
        raise ValueError(f"期望 1 个用例，实际解析到 {len(cases)} 个")
    return cases[0]


def _parse_tuple_style_case(lines: List[str], trunk_num: int) -> List[Dict[str, Tuple[Any, ...]]]:
    """Group a plain value stream into fixed-size positional cases."""
    if not isinstance(trunk_num, int) or trunk_num <= 0:
        raise ValueError(f"trunk_num 必须为正整数，当前值: {trunk_num}")
    values = [_literal(line) for line in lines if line.strip()]
    if len(values) % trunk_num:
        raise ValueError(
            f"参数总数({len(values)})不是 trunk_num({trunk_num})的整数倍"
        )
    return [
        {"input": tuple(values[i:i + trunk_num])}
        for i in range(0, len(values), trunk_num)
    ]


def _parse_labeled_cases(content: str, params_num: Optional[int]) -> List[dict]:
    cases: List[dict] = []
    current: Dict[str, List[str]] = {}
    section: Optional[str] = None

    def finish_case() -> None:
        nonlocal current
        if not current:
            return
        if "input" not in current:
            raise ValueError("用例缺少 Input/输入 区段")
        case: dict = {
            "input": _parse_input_text("\n".join(current["input"]), params_num)
        }
        # Official Output is the expected answer. An explicit Expected wins.
        expected_lines = current.get("expected") or current.get("output")
        if expected_lines:
            case["expected"] = _literal("\n".join(expected_lines))
        cases.append(case)
        current = {}

    for raw_line in content.splitlines():
        match = _SECTION_RE.match(raw_line)
        if match:
            label = match.group(1).lower()
            remainder = match.group(2).strip()
            if label in _INPUT_LABELS:
                finish_case()
                section = "input"
            elif label in _OUTPUT_LABELS:
                section = "output"
            elif label in _EXPECTED_LABELS:
                section = "expected"
            current.setdefault(section, [])
            if remainder:
                current[section].append(remainder)
            continue
        if section is not None and raw_line.strip():
            current[section].append(raw_line.strip())

    finish_case()
    return cases


def parse_test_cases(file_path: os.PathLike, params_num: Optional[int] = None) -> List[dict]:
    """Parse a UTF-8 LeetCode text file into normalized case dictionaries."""
    with open(file_path, "r", encoding="utf-8-sig") as handle:
        content = handle.read().strip()
    if not content:
        return []

    if any(_SECTION_RE.match(line) for line in content.splitlines()):
        return _parse_labeled_cases(content, params_num)

    if not isinstance(params_num, int):
        raise ValueError("元组风格测试文件必须提供 params_num")
    return _parse_tuple_style_case(content.splitlines(), params_num)
