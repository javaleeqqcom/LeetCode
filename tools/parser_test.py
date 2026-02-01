# tools/parser_test.py
import os
import random
import unittest
import hashlib
from typing import Any, Dict, List, Tuple, Union
from examples_parser import parse_test_cases
import json
import re
import string

def gen_hashable_elem():
    """生成一个可哈希的基础元素（用于 dict key 或 list 元素）"""
    choice = random.randint(0, 4)
    if choice == 0:
        return random.randint(-10, 10)
    elif choice == 1:
        return round(random.uniform(-5.0, 5.0), 3)
    elif choice == 2:
        return random.choice([True, False, None])
    elif choice == 3:
        # 随机短字符串，避免特殊字符干扰 repr/ast
        length = random.randint(1, 5)
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    else:  # choice == 4
        return ()  # 空 tuple 是 hashable 的

def generate_random_value(current_depth: int, max_depth: int):
    """生成随机值，支持嵌套 list/tuple/dict，包含 None/bool/int/str"""
    if current_depth >= max_depth:
        # 到达最大深度，只生成基础类型
        choice = random.choice(['int', 'str', 'bool', 'none'])
    else:
        # 允许嵌套
        choice = random.choice(['int', 'str', 'bool', 'none', 'list', 'tuple', 'dict'])

    if choice == 'int':
        return random.randint(-100, 100)
    elif choice == 'str':
        length = random.randint(0, 10)
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    elif choice == 'bool':
        return random.choice([True, False])
    elif choice == 'none':
        return None
    elif choice == 'list':
        size = random.randint(0, 5)
        return [generate_random_value(current_depth + 1, max_depth) for _ in range(size)]
    elif choice == 'tuple':
        size = random.randint(0, 5)
        return tuple(generate_random_value(current_depth + 1, max_depth) for _ in range(size))
    elif choice == 'dict':
        size = random.randint(0, 4)
        return {
            f"key_{i}": generate_random_value(current_depth + 1, max_depth)
            for i in range(size)
        }
    else:
        return 0  # fallback
    

def save_parsed_result(parsed_cases: List, original_filename: str):
    """将解析结果保存为JSON文件用于调试"""
    json_file = os.path.splitext(original_filename)[0] + '.json'
    # 转换不可序列化的对象为字符串
    serializable_cases = []
    for case in parsed_cases:
        if isinstance(case, dict):
            serializable_case = {}
            for k, v in case.items():
                if k == 'input':
                    serializable_case[k] = {}
                    for ik, iv in v.items():
                        try:
                            json.dumps(iv)
                            serializable_case[k][ik] = iv
                        except (TypeError, ValueError):
                            serializable_case[k][ik] = repr(iv)
                else:
                    try:
                        json.dumps(v)
                        serializable_case[k] = v
                    except (TypeError, ValueError):
                        serializable_case[k] = repr(v)
            serializable_cases.append(serializable_case)
        else:  # tuple or other
            try:
                json.dumps(case)
                serializable_cases.append(case)
            except (TypeError, ValueError):
                serializable_cases.append(repr(case))
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(serializable_cases, f, indent=2, ensure_ascii=False)

def _to_leetcode_repr(obj) -> str:
    """将 Python 对象转为 LeetCode 风格字符串（None→null, True→true, False→false）"""
    s = repr(obj)
    # 先处理布尔和 None，注意顺序避免干扰
    s = re.sub(r'\bTrue\b', 'true', s)
    s = re.sub(r'\bFalse\b', 'false', s)
    s = re.sub(r'\bNone\b', 'null', s)
    return s

class TestTestExamplesParser(unittest.TestCase):
    TEST_DIR = "tools_test"
    
    @classmethod
    def setUpClass(cls):
        os.makedirs(cls.TEST_DIR, exist_ok=True)

    def write_test_file(self, test_cases_data: List[Dict], filename: str) -> str:
        test_file = os.path.join(self.TEST_DIR, filename)
        content = ""
        for case in test_cases_data:
            content += "输入\n"
            for k, v in case['input'].items():
                content += f"{k} =\n{_to_leetcode_repr(v)}\n"
            content += "输出\n"
            content += f"{_to_leetcode_repr(case['output'])}\n"
            if 'expected' in case:
                content += "预期结果\n"
                content += f"{_to_leetcode_repr(case['expected'])}\n"
            content += "\n"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return test_file

    def test_parse_boolean_and_null(self):
        """测试 LeetCode 风格的 true/false/null 被正确转换"""
        test_cases_data = [
            {
                'input': {
                    'n': 7,
                    'edges': [[0,1],[0,2],[1,4],[1,5],[2,3],[2,6]],
                    'hasApple': [False, False, True, False, True, True, False]
                },
                'output': 8,
                'expected': None
            },
            {
                'input': {'flag': True, 'value': None},
                'output': False,
                'expected': True
            }
        ]
        test_file = self.write_test_file(test_cases_data, "test_bool_null.txt")
        cases = parse_test_cases(test_file)

        # 保存解析结果用于调试
        save_parsed_result(cases, test_file)
        
        # 验证解析结果
        case0 = cases[0]
        self.assertEqual(case0['input']['n'], 7)
        self.assertEqual(case0['input']['hasApple'], [False, False, True, False, True, True, False])
        self.assertEqual(case0['output'], 8)
        self.assertIsNone(case0['expected'])

        case1 = cases[1]
        self.assertTrue(case1['input']['flag'])
        self.assertIsNone(case1['input']['value'])
        self.assertFalse(case1['output'])
        self.assertTrue(case1['expected'])

    def test_parse_dict_style_basic(self):
        """测试字典风格的基本解析"""
        # 原始测试数据
        test_cases_data = [
            {
                'input': {'nums': [1, 5, 2]},
                'output': 0,
                'expected': 2
            },
            {
                'input': {'arr': [1, 3, 2, 3, 1], 'k': 3},
                'output': 1,
                'expected': 4
            }
        ]
        
        test_file = self.write_test_file(test_cases_data, "test_dict_basic.txt")
        cases = parse_test_cases(test_file)
        
        # 保存解析结果用于调试
        save_parsed_result(cases, test_file)
        
        # 验证解析结果
        self.assertEqual(len(cases), len(test_cases_data), f"File: {test_file}")
        for i, (original, parsed) in enumerate(zip(test_cases_data, cases)):
            with self.subTest(case=i, file=test_file):
                self.assertIsInstance(parsed, dict)
                self.assertEqual(parsed['input'], original['input'])
                self.assertEqual(parsed['output'], original['output'])
                self.assertEqual(parsed['expected'], original['expected'])

    def test_parse_dict_style_no_expected(self):
        """测试没有预期结果的情况"""
        test_cases_data = [
            {
                'input': {'nums': [1, 5, 2]},
                'output': 0
            },
            {
                'input': {'data': {"a": 1}},
                'output': None  # 注意：null 在 Python 中是 None
            }
        ]
        
        test_file = self.write_test_file(test_cases_data, "test_dict_no_expected.txt")
        cases = parse_test_cases(test_file)
        
        # 保存解析结果用于调试
        save_parsed_result(cases, test_file)
        
        self.assertEqual(len(cases), len(test_cases_data), f"File: {test_file}")
        for i, (original, parsed) in enumerate(zip(test_cases_data, cases)):
            with self.subTest(case=i, file=test_file):
                self.assertIsInstance(parsed, dict)
                self.assertEqual(parsed['input'], original['input'])
                self.assertEqual(parsed['output'], original['output'])
                self.assertNotIn('expected', parsed)


    def test_parse_random_cases(self):
        """测试随机大批量基础类型"""
        # 测试不同嵌套深度
        for depth in [1, 2, 3]:
            with self.subTest(depth=depth):
                # 生成多个测试文件
                for batch in range(3):  # 3个批次
                    # 创建测试用例数据
                    test_cases_data = []
                    for _ in range(5):  # 每个文件5个测试用例
                        # 随机生成输入参数（1-3个）
                        num_inputs = random.randint(1, 3)
                        inputs = {}
                        for i in range(num_inputs):
                            param_name = f"param{i+1}"
                            inputs[param_name] = generate_random_value(0, depth)
                        # 随机生成输出和预期结果
                        output_val = generate_random_value(0, depth)
                        expected_val = generate_random_value(0, depth)
                        test_cases_data.append({
                            'input': inputs,
                            'output': output_val,
                            'expected': expected_val
                        })
                    
                    # 生成哈希文件名
                    content_for_hash = str(test_cases_data).encode('utf-8')
                    hash_obj = hashlib.md5(content_for_hash)
                    filename = f"random_depth{depth}_batch{batch}_{hash_obj.hexdigest()[:8]}.txt"
                    
                    # 写入文件并解析
                    test_file = self.write_test_file(test_cases_data, filename)
                    parsed_cases = parse_test_cases(test_file)
                    
                    # 保存解析结果用于调试
                    save_parsed_result(parsed_cases, test_file)
                    
                    # 验证解析结果
                    self.assertEqual(
                        len(parsed_cases), 
                        len(test_cases_data),
                        f"File: {test_file}, Expected {len(test_cases_data)} cases but got {len(parsed_cases)}"
                    )
                    
                    for i, (original, parsed) in enumerate(zip(test_cases_data, parsed_cases)):
                        with self.subTest(case=i, file=test_file, depth=depth, batch=batch):
                            self.assertIsInstance(parsed, dict)
                            # 验证输入字典
                            self.assertEqual(set(parsed['input'].keys()), set(original['input'].keys()))
                            for k in original['input'].keys():
                                # 对于可安全解析的类型直接比较，否则比较 repr 字符串
                                orig_val = original['input'][k]
                                parsed_val = parsed['input'][k]
                                
                                if isinstance(orig_val, (int, float, str, bool, type(None))):
                                    self.assertEqual(parsed_val, orig_val)
                                elif isinstance(orig_val, (list, tuple, dict)):
                                    if isinstance(parsed_val, str):
                                        # 如果解析失败保持字符串，比较 repr
                                        self.assertEqual(parsed_val, repr(orig_val))
                                    else:
                                        # 如果成功解析，直接比较
                                        self.assertEqual(parsed_val, orig_val)
                                else:
                                    # 其他类型（如 set）可能无法完美解析，比较 repr
                                    if isinstance(parsed_val, str):
                                        self.assertEqual(parsed_val, repr(orig_val))
                            
                            # 验证输出 (直接比较对象)
                            self.assertEqual(parsed['output'], original['output'])
                            # 验证预期结果 (直接比较对象)
                            self.assertEqual(parsed['expected'], original['expected'])

if __name__ == '__main__':
    unittest.main()