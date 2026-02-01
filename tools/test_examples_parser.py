# tools/test_examples_parser.py
import ast
from typing import List, Tuple, Any

def parse_test_cases(file_path: str) -> List[Tuple]:
    """
    解析测试用例文件，返回元组列表。
    每个元组格式：(input1, input2, ..., output)
    
    文件格式示例：
    # 测试用例1
    input1 = [1,2,3]
    input2 = 4
    output = [1,2,3]
    
    # 测试用例2
    input1 = [1,1,2]
    input2 = 5
    output = [1,2]
    """
    test_cases = []
    current_case = {}
    in_case = False

    with open(file_path, 'r') as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                if in_case and 'output' in current_case:
                    # 提取输入参数 (input1, input2, ...)
                    inputs = []
                    i = 1
                    while True:
                        key = f"input{i}"
                        if key in current_case:
                            inputs.append(current_case[key])
                            i += 1
                        else:
                            break
                    test_cases.append(tuple(inputs) + (current_case['output'],))
                    current_case = {}
                    in_case = False
                continue

            if '=' in stripped:
                var, val = stripped.split('=', 1)
                var = var.strip()
                val_str = val.strip()
                
                current_case[var] = safe_eval(val_str)  # 存储已解析的对象
                in_case = True

    # 处理最后一个测试用例
    if in_case and 'output' in current_case:
        inputs = []
        i = 1
        while True:
            key = f"input{i}"
            if key in current_case:
                inputs.append(current_case[key])
                i += 1
            else:
                break
        test_cases.append(tuple(inputs) + (current_case['output'],))
    
    return test_cases

def safe_eval(s: str) -> Any:
    """安全评估字符串表达式，避免执行任意代码"""
    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError):
        return s