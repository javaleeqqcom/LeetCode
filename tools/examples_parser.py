# tools/examples_parser.py
import ast
import re
from typing import List, Any, Union
from typing import List, Dict, Any, Union

def parse_test_cases(file_path: str) -> List[Union[Dict, tuple]]:
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
    for raw_case in raw_cases:
        lines = [line.strip() for line in raw_case.split('\n') if line.strip()]
        if any(line == "输入" for line in lines):
            case_dict = _parse_dict_style_case(lines)
            if case_dict:
                test_cases.append(case_dict)
        else:
            # 元组风格（理论上不会出现在这种连续格式中，但保留兼容）
            args = []
            for line in lines:
                processed_line = leetcode_keywords_to_python(line)
                try:
                    args.append(ast.literal_eval(processed_line))
                except (ValueError, SyntaxError):
                    args.append(line)
            if args:
                test_cases.append(tuple(args) if len(args) > 1 else (args[0],))
    return test_cases

# ===== 新增：将 LeetCode 风格的 null/true/false 转为 Python 的 None/True/False =====
def leetcode_keywords_to_python(text: str) -> str:
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

# ===== 原有函数保持不变，仅在解析前调用 leetcode_keywords_to_python =====

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
            processed_line = leetcode_keywords_to_python(line)

            if current_section == "input":
                if line.endswith(' ='):  # 注意：这里仍用原始 line 判断语法结构
                    param_name = line[:-2]
                    if i + 1 < len(lines):
                        i += 1
                        value_line = lines[i]
                        # ===== 对值行也做 null → None 替换 =====
                        processed_value = leetcode_keywords_to_python(value_line)
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

