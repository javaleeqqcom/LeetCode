# tools/examples_parser.py
import ast
import re,os
from typing import List, Any, Union
from typing import List, Dict, Any, Union, Tuple, Optional
from collections import defaultdict

"""一个标准的测试样例的格式 _CASE_TYPE 可以是：
- 字典: {"input": case [,"output":Any, "expected":Any,"error":str , ...]}
- 其中的 case 可以是：
  - 字典 _PARAMS：其键为被测函数的变量名，其值则为变量值
  - 元组：按被测函数的变量顺序排列的变量值"""

_PARAMS = Dict[str, Any]
_CASE_TYPE = Dict[str, Union[_PARAMS, Tuple, Any]]

# _CASE_TYPE 是单个测试样例附加测试输出、期望输出、错误信息等附加信息的字典

# ===== 新增：将 LeetCode 风格的 null/true/false 转为 Python 的 None/True/False =====
def json_keywords_to_python(text: str) -> str:
    """ 将字符串中所有非字符串字面量的 'null', 'true', 'false' 替换为 Python 对应的 'None', 'True', 'False'。
    示例： '[null, true, "false", false]' → '[None, True, "false", False]'
    '{"valid": true, "msg": "null"}' → '{"valid": True, "msg": "null"}' """
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
            return token

    # 正则说明：
    # - 匹配双引号字符串（支持转义）
    # - 匹配单引号字符串（支持转义）
    # - 匹配单词边界上的 null / true / false（避免匹配到部分单词如 "trueness"）
    pattern = r''' "(?:[^"\\]|\\.)*" # 双引号字符串
                 |'(?:[^'\\]|\\.)*' # 单引号字符串
                 |\b(?:null|true|false)\b # 关键字（单词边界） '''
    return re.sub(pattern, replacer, text, flags=re.VERBOSE)

def _parse_dict_style_case(lines: List[str]) -> Dict[str,Union[_PARAMS ,Any]]:
    """
    解析以字典风格表示的测试用例（该函数经过人工修订，并严格测试）
    """
    _CASE_DICT = { "输入":"input", "输出":"output", "预期结果":"expected"}
    case = defaultdict(dict)
    current_section,param_name = None,None
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # 精致的状态机分支代码
        if line in _CASE_DICT.keys():
            current_section = _CASE_DICT[line]
        elif line.endswith('='):
            # 注意：这里仍用原始 line 判断语法结构
            param_name = line[:-1].strip()
        else:
            assert current_section is not None, "current_section should not be None, line: \n{}".format(line)
            line = lines[i].strip()
            # ===== 对值行做 json → python 替换 =====
            processed_value = ast.literal_eval(json_keywords_to_python(line))
            # 用 ast 将字符串转换为 Python 数据结构（如果失败则自然抛出错误，由上级捕获异常）
            if param_name is None: # 无变量名的情况
                case[current_section] = processed_value
            else: # 有变量名的情况
                case[current_section][param_name] = processed_value
                param_name = None # 情况状态值
        i += 1
    assert "" not in case
    return case

def _parse_tuple_style_case(lines: List[str], trunk_num: int) -> List[Dict[str, Tuple]]:
    """将连续参数行按 trunk_num 分组，每组生成一个测试用例
    
    :param lines: 非空行列表（每行是一个参数值）
    :param trunk_num: 每个测试用例的参数数量
    :return: 测试用例字典列表 [{"input": (p1, p2, ...)}, ...]
    """
    if trunk_num is None or trunk_num <= 0:
        raise ValueError(f"trunk_num 必须为正整数，当前值: {trunk_num}")
    
    case_params = []
    for line in filter(len, map(str.strip, lines)):
        processed_value = ast.literal_eval(json_keywords_to_python(line.strip()))
        case_params.append(processed_value)
    
    # 严格分组：总参数数必须是 trunk_num 的整数倍
    if len(case_params) % trunk_num != 0:
        raise ValueError(
            f"参数总数({len(case_params)})不是 trunk_num({trunk_num})的整数倍，"
            f"无法完整分组。请检查测试文件格式或 params_num 参数。"
        )
    
    # 每 trunk_num 个参数组成一个测试用例
    return [
        {"input": tuple(case_params[i:i + trunk_num])}
        for i in range(0, len(case_params), trunk_num)
    ]

def parse_test_cases(file_path: os.PathLike, params_num: Optional[int] = None) -> List[_CASE_TYPE]:
    """
    解析测试样例文件
    :param file_path: 测试样例文件路径
    :param params_num: 元组风格时每个测试用例的参数数量（必须提供）
    :return: 测试用例列表
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        if not content:
            return []
    
    # 判断是否为字典风格（含"输入"关键词）
    has_input_keyword = "输入" in content
    
    if has_input_keyword:
        # 字典风格：按"输入"分割多个测试块
        import re
        raw_blocks = re.split(r'(?=输入(?=\s*[^a-zA-Z0-9_]|$))', content)
        raw_cases = [block.strip() for block in raw_blocks if block.strip().startswith("输入")]
    else:
        # 元组风格：整个文件视为连续参数流
        raw_cases = [content]
    
    test_cases = []
    for raw_case in raw_cases:
        lines = [line.strip() for line in raw_case.split('\n') if line.strip()]
        # 检测是否为字典风格（含"参数名="结构）
        if any(line.endswith('=') for line in lines):
            case_dict = _parse_dict_style_case(lines)
            if case_dict:
                test_cases.append(case_dict)
        else:
            # 元组风格：必须提供 params_num
            assert isinstance(params_num, int), "When using _parse_tuple_style_case, the 'params_num' parameter (specifying the number of parameters per test case) must be an integer but actually got {}.".format(type(params_num).__name__)
            case_tuples = _parse_tuple_style_case(lines, params_num)
            test_cases.extend(case_tuples)
    
    return test_cases
