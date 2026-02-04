# tools/examples_parser.py
import ast
import re,os
from typing import List, Any, Union
from typing import List, Dict, Any, Union, Tuple
from collections import defaultdict
"""
一个标准的测试样例的格式 _CASE_TYPE 可以是：
    - 字典: {"input": case [,"output":Any, "expected":Any,"error":str , ...]}
    - 其中的 case 可以是：
        - 字典 _PARAMS：其键为被测函数的变量名，其值则为变量值
        - 元组：按被测函数的变量顺序排列的变量值
"""
_PARAMS = Dict[str, Any]
_CASE_TYPE = Dict[str, Union[_PARAMS, Tuple, Any]]
# _CASE_TYPE 是单个测试样例附加测试输出、期望输出、错误信息等附加信息的字典

# ===== 新增：将 LeetCode 风格的 null/true/false 转为 Python 的 None/True/False =====
def json_keywords_to_python(text: str) -> str:
    """
    将字符串中所有非字符串字面量的 'null', 'true', 'false'
    替换为 Python 对应的 'None', 'True', 'False'。
    
    示例：
        '[null, true, "false", false]' 
        → '[None, True, "false", False]'
        
        '{"valid": true, "msg": "null"}'
        → '{"valid": True, "msg": "null"}'
    """
    def replacer(match):
        token = match.group(0)
        # 如果是字符串字面量（以引号开头），原样返回
        if token.startswith('"') or token.startswith("'"):
            return token
        # 否则，按关键字转换
        if token == 'null':
            return 'None'
        elif token == 'true':
            return 'True'
        elif token == 'false':
            return 'False'
        else:
            return token  # 理论上不会发生

    # 正则说明：
    # - 匹配双引号字符串（支持转义）
    # - 匹配单引号字符串（支持转义）
    # - 匹配单词边界上的 null / true / false（避免匹配到部分单词如 "trueness"）
    pattern = r'''
        "(?:[^"\\]|\\.)*"          # 双引号字符串
        |'(?:[^'\\]|\\.)*'         # 单引号字符串
        |\b(?:null|true|false)\b   # 关键字（单词边界）
    '''
    return re.sub(pattern, replacer, text, flags=re.VERBOSE)

_CASE_DICT = {
    "输入":"input",
    "输出":"output",
    "预期结果":"expected"
}
def _parse_dict_style_case(lines: List[str]) -> Dict[str,Union[_PARAMS ,Any]]:
    case = defaultdict(dict)
    current_section,param_name = "",""
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line in _CASE_DICT.keys():
            current_section = _CASE_DICT[line]
        elif line.endswith('='):  # 注意：这里仍用原始 line 判断语法结构
            param_name = line[:-1].strip()
            i += 1
            if i < len(lines):
                line = lines[i].strip()
                # ===== 对值行做 json → python 替换 =====
                processed_value = json_keywords_to_python(line)
                # 用 ast 将字符串转换为 Python 数据结构（如果失败则自然抛出错误，由上级捕获异常）
                case[current_section][param_name] = ast.literal_eval(processed_value)
    return case

def _parse_tuple_style_case(lines: List[str]) -> Dict[str,Tuple]:
    case_input = []
    for line in filter(len,map(str.strip,lines)):
        # ===== 对值行做 json → python 替换 =====
        processed_value = json_keywords_to_python(line.strip())
        # 用 ast 将字符串转换为 Python 数据结构（如果失败则自然抛出错误，由上级捕获异常）
        case_input.append( ast.literal_eval(processed_value))
    return {"input":tuple(case_input)}

def parse_test_cases(file_path: os.PathLike , params_num = None) -> List[_CASE_TYPE]:
    """
    parse_test_cases 的 Docstring
    
    :param file_path: 包含测试样例数据的纯文本文件
    :type file_path: str
    :return: 返回 _PARAMS_CASES 或 _TUPLE_CASES 这两种之一类型的测试样例列表
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()

    if not content:
        return []

    # ===== 关键改进：按 "输入" 分割，但保留分隔符 =====
    # 使用正向 lookahead 拆分，保留 "输入" 开头的部分
    import re
    raw_blocks = re.split(r'(?=输入(?=\s*[^a-zA-Z0-9_]|$))', content)
    # 过滤掉空块和不以"输入"开头的块
    raw_cases = [block.strip() for block in raw_blocks if block.strip().startswith("输入")]

    test_cases = []
    if len(raw_cases) >0:
        for raw_case in raw_cases:
            lines = [line.strip() for line in raw_case.split('\n') if line.strip()]
            if any(line.endswith('=') in  for line in lines):
                case_dict = _parse_dict_style_case(lines)
                if case_dict:
                    test_cases.append(case_dict)
            else: # 元组风格（此种风格仅支持输入）
                case_tuple = _parse_tuple_style_case(lines 去掉 “输入”)
                test_cases.append(case_tuple)
    elif params_num is not None:
        # 只能是元组风格
        # 每 params_num 个非空行视为一个测试样例
        case_tuple = _parse_tuple_style_case(lines)
        test_cases.append(case_tuple)
    else:
        ERR
    return test_cases

