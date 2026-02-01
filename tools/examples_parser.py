# tools/examples_parser.py

import ast
import re
from typing import List, Any, Union
from typing import List, Dict, Any, Union

def parse_test_cases(file_path: str) -> List[Union[Dict, tuple]]:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    raw_cases = [case.strip() for case in content.split('\n\n') if case.strip()]
    test_cases = []
    for raw_case in raw_cases:
        lines = [line.strip() for line in raw_case.split('\n') if line.strip()]
        if any(line == "输入" for line in lines):
            case_dict = _parse_dict_style_case(lines)
            if case_dict:
                test_cases.append(case_dict)
        else:
            args = []
            for line in lines:
                # ===== 元组格式也需处理 null =====
                processed_line = replace_null_with_none(line)
                try:
                    args.append(ast.literal_eval(processed_line))
                except (ValueError, SyntaxError):
                    args.append(line)
            if args:
                if len(args) > 1:
                    test_cases.append(tuple(args))
                else:
                    test_cases.append((args[0],))
    return test_cases

# ===== 新增：安全替换 null -> None（避开字符串） =====
def replace_null_with_none(text: str) -> str:
    """
    将字符串中所有非字符串字面量的 'null' 替换为 'None'。
    例如：
        '[null, "null", {"x": null}]' → '[None, "null", {"x": None}]'
    """
    def replacer(match):
        s = match.group(0)
        if s.startswith('"') or s.startswith("'"):
            # 是字符串字面量，原样返回
            return s
        elif s == 'null':
            return 'None'
        else:
            return s

    # 匹配：字符串字面量 或 单词边界上的 null
    pattern = r'("(?:[^"\\]|\\.)*")|(\'(?:[^\'\\]|\\.)*\')|\bnull\b'
    return re.sub(pattern, replacer, text)

# ===== 原有函数保持不变，仅在解析前调用 replace_null_with_none =====

def _parse_dict_style_case(lines: List[str]) -> Dict[str, Any]:
    case = {'input': {}}
    current_section = None
    i = 0
    while i < len(lines):
        line = lines[i]
        if line == "输入":
            current_section = "input"
        elif line == "输出":
            current_section = "output"
        elif line == "预期结果":
            current_section = "expected"
        else:
            # ===== 关键修改：预处理 line =====
            processed_line = replace_null_with_none(line)

            if current_section == "input":
                if line.endswith(' ='):  # 注意：这里仍用原始 line 判断语法结构
                    param_name = line[:-2]
                    if i + 1 < len(lines):
                        i += 1
                        value_line = lines[i]
                        # ===== 对值行也做 null → None 替换 =====
                        processed_value = replace_null_with_none(value_line)
                        try:
                            case['input'][param_name] = ast.literal_eval(processed_value)
                        except (ValueError, SyntaxError):
                            case['input'][param_name] = value_line  # 保留原始（失败时）
                    else:
                        case['input'][param_name] = None
                else:
                    # 孤立值行（不推荐，但兼容）
                    try:
                        case['input'] = ast.literal_eval(processed_line)
                    except:
                        pass
            elif current_section in ["output", "expected"]:
                try:
                    case[current_section] = ast.literal_eval(processed_line)
                except (ValueError, SyntaxError):
                    case[current_section] = line
        i += 1
    return case

