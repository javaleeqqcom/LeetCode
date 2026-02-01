# tools/test_examples_parser.py
import ast
import re
from typing import List, Any, Union
# tools/test_examples_parser.py
import ast
from typing import List, Dict, Any, Union

def parse_test_cases(file_path: str) -> List[Union[Dict, tuple]]:
    """
    解析测试用例文件，支持两种格式：
    1. LeetCode 字典格式（包含"输入"/"输出"[/"预期结果"]）
    2. 简单元组格式（每行一个参数）
    
    返回:
    - 字典格式: {'input': {param_name: value}, 'output': value, 'expected': value (optional)}
    - 元组格式: (arg1, arg2, ..., output)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 按空行分割测试用例
    raw_cases = [case.strip() for case in content.split('\n\n') if case.strip()]
    test_cases = []
    
    for raw_case in raw_cases:
        lines = [line.strip() for line in raw_case.split('\n') if line.strip()]
        
        # 检测是否为字典格式（包含"输入"、"输出"等关键词）
        if any(line == "输入" for line in lines):
            case_dict = _parse_dict_style_case(lines)
            if case_dict:
                test_cases.append(case_dict)
        else:
            # 简单元组格式
            args = []
            for line in lines:
                try:
                    args.append(ast.literal_eval(line))
                except (ValueError, SyntaxError):
                    args.append(line)  # 保留原始字符串
            if args:
                # 最后一个元素是输出，前面是输入参数
                if len(args) > 1:
                    test_cases.append(tuple(args))
                else:
                    test_cases.append((args[0],))
    
    return test_cases

def _parse_dict_style_case(lines: List[str]) -> Dict[str, Any]:
    """解析字典风格的测试用例"""
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
            # 处理参数行或值行
            if current_section == "input":
                if ' = ' in line:
                    # 参数声明行: "param ="
                    param_name = line.split(' = ')[0]
                    # 下一行是值
                    if i + 1 < len(lines) and not lines[i + 1].startswith(("输入", "输出", "预期结果")):
                        i += 1
                        value_line = lines[i]
                        try:
                            case['input'][param_name] = ast.literal_eval(value_line)
                        except (ValueError, SyntaxError):
                            case['input'][param_name] = value_line
                    else:
                        case['input'][param_name] = None
                # 如果没有' = '，可能是值行（但这种情况不应该出现）
            elif current_section in ["output", "expected"]:
                try:
                    case[current_section] = ast.literal_eval(line)
                except (ValueError, SyntaxError):
                    case[current_section] = line
        
        i += 1
    
    return case