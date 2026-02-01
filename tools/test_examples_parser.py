# tools/test_examples_parser.py
import ast
import re
from typing import List, Any, Union

def parse_test_cases(file_path: str) -> List[Union[tuple, dict]]:
    """
    解析 LeetCode 风格测试用例文件。
    支持两种格式：
    
    格式1（无参数名，纯值）：
        [1,2,3]
        5
        
    格式2（带参数名）：
        输入
        nums =
        [1,2,3]
        k =
        5
        输出
        0
        预期结果
        0
    
    返回：List[Union[tuple, dict]]
        - 若为格式1：返回 [(arg1, arg2, ...), ...]
        - 若为格式2：返回 [{'input': {...}, 'output': ..., 'expected': ...}, ...]
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.rstrip() for line in f]

    # 判断格式类型
    has_input_keyword = any(re.match(r'^输入\s*$', line) for line in lines)
    
    if has_input_keyword:
        return _parse_dict_style(lines)
    else:
        return _parse_tuple_style(lines)

def _parse_tuple_style(lines: List[str]) -> List[tuple]:
    test_cases = []
    current_case = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_case:
                test_cases.append(tuple(current_case))
                current_case = []
            continue
        
        try:
            parsed = safe_eval(stripped)
            current_case.append(parsed)
        except:
            current_case.append(stripped)

    if current_case:
        test_cases.append(tuple(current_case))
    
    return test_cases

def _parse_dict_style(lines: List[str]) -> List[dict]:
    test_cases = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or not re.match(r'^输入\s*$', line):
            i += 1
            continue
        
        # 找到输入块
        i += 1
        inputs = {}
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            if re.match(r'^(输出|预期结果)\s*$', line):
                break
            if '=' in line:
                key, val_expr = line.split('=', 1)
                key = key.strip()
                val_lines = []
                i += 1
                # 收集多行值（如列表）
                while i < len(lines) and not re.match(r'^\w+\s*=?\s*$', lines[i].strip()):
                    if lines[i].strip():
                        val_lines.append(lines[i])
                    i += 1
                val_str = '\n'.join(val_lines) if val_lines else val_expr.strip()
                try:
                    val = safe_eval(val_str)
                except:
                    val = val_str
                inputs[key] = val
                continue
            i += 1
        
        # 找输出
        output_val = None
        expected_val = None
        while i < len(lines):
            line = lines[i].strip()
            if re.match(r'^输出\s*$', line):
                i += 1
                out_lines = []
                while i < len(lines) and not re.match(r'^(输入|预期结果)\s*$', lines[i].strip()):
                    if lines[i].strip():
                        out_lines.append(lines[i])
                    i += 1
                out_str = '\n'.join(out_lines).strip()
                try:
                    output_val = safe_eval(out_str) if out_str else None
                except:
                    output_val = out_str
                continue
            elif re.match(r'^预期结果\s*$', line):
                i += 1
                exp_lines = []
                while i < len(lines) and not re.match(r'^输入\s*$', lines[i].strip()):
                    if lines[i].strip():
                        exp_lines.append(lines[i])
                    i += 1
                exp_str = '\n'.join(exp_lines).strip()
                try:
                    expected_val = safe_eval(exp_str) if exp_str else None
                except:
                    expected_val = exp_str
                continue
            else:
                i += 1
        
        case = {'input': inputs}
        if output_val is not None:
            case['output'] = output_val
        if expected_val is not None:
            case['expected'] = expected_val
        test_cases.append(case)
    
    return test_cases

def safe_eval(s: str) -> Any:
    """安全评估字符串表达式，避免执行任意代码"""
    s_clean = s.strip()
    if not s_clean:
        return s
    try:
        return ast.literal_eval(s_clean)
    except (ValueError, SyntaxError):
        return s