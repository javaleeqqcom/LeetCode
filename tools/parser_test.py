# tools/parser_test.py
import os
import random
import unittest
import hashlib
from typing import Any, Dict, List, Tuple, Union, Optional
from examples_parser import parse_test_cases,_CASE_TYPE
from compacted_json import _test_CompactedJson
import re
import string
import json
from pathlib import Path

def _to_leetcode_repr(obj) -> str:
    """将 Python 对象转为 LeetCode 风格字符串（None→null, True→true, False→false）"""
    s = repr(obj)
    # 先处理布尔和 None，注意顺序避免干扰
    s = re.sub(r'\bTrue\b', 'true', s)
    s = re.sub(r'\bFalse\b', 'false', s)
    s = re.sub(r'\bNone\b', 'null', s)
    return s

class _test_Parser(_test_CompactedJson):
    """测试解析器功能"""
    def __init__(self, hex_len: int = 8, load_factor_threshold=0.7, alias_prefix: str = "@") -> None:
        super().__init__(hex_len, load_factor_threshold, alias_prefix ,has_trap= False) # 禁用陷阱字符串，因为目的不是测试 CompactedJson

# 暂时写作全局变量，以后需要改为双继承
cjson = _test_CompactedJson(
    hex_len= 8 ,
    has_trap= False , # 禁用陷阱字符串，因为目的不是测试 CompactedJson
    leaf_list_same_type= True, # 确保叶子列表的元素都是同类型，符合测试样例规范
    )

class TestExamplesParser(unittest.TestCase):
    TEST_DIR = "tools_test"
    
    @classmethod
    def setUpClass(cls):
        os.makedirs(cls.TEST_DIR, exist_ok=True)

    def write_test_file(self, test_cases_data: List[_CASE_TYPE], filename: str, include_input: bool = True, params_num: Optional[int] = None) -> os.PathLike:
        """写入测试文件，支持字典格式和元组格式
        :param include_input: 是否包含"输入"关键词（字典格式）
        :param params_num: 元组格式的参数数量
        """
        content = ""
        for case in test_cases_data:
            if include_input:
                assert isinstance(case['input'],dict)
                # 字典格式
                content += "输入\n"
                for k, v in case['input'].items():
                    content += f"{k} =\n{_to_leetcode_repr(v)}\n"
                content += "输出\n"
                content += f"{_to_leetcode_repr(case['output'])}\n"
                if 'expected' in case:
                    content += "预期结果\n"
                    content += f"{_to_leetcode_repr(case['expected'])}\n"
                content += "\n"
            else:
                # 元组格式
                # 将输入参数转换为多行格式
                for param in case['input']:
                    content += f"{_to_leetcode_repr(param)}\n"
                content += "\n"  # 每个测试用例之间用空行分隔
        
        # 添加随机空行，确保测试用例间有空行
        lines = content.split('\n')
        # 移除空行
        non_empty_lines = [line for line in lines if line.strip() != '']
        # 在测试用例间添加随机空行
        new_lines = []
        for i, line in enumerate(non_empty_lines):
            new_lines.append(line)
            # 在每个测试用例后添加随机空行
            if i < len(non_empty_lines) - 1 and random.random() > 0.5:
                new_lines.append('')
        content = '\n'.join(new_lines)
        
        test_file = os.path.join(self.TEST_DIR, filename)
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return Path(test_file)

    def save_parsed_result(self , filename: os.PathLike, test_cases: List[_CASE_TYPE]) -> Optional[Path]:
        """保存解析后的测试用例到文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(cjson.dumps(test_cases ,indent = 2, ensure_ascii=False))
            return Path(filename)
        except IOError as e:
            print(f"Error! Can not write to file: {filename}, error: {e}")
            return None
        except Exception as e:
            print(f"Unknown Error: {e}")
            return None

    def basic_test(self):
        """测试字典风格的基本解析"""
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
            },
            {
                'input': {
                    'n': 7,
                    'edges': [[0, 1], [0, 2], [1, 4], [1, 5], [2, 3], [2, 6]],
                    'hasApple': [False, False, True, False, True, True, False]
                },
                'output': 8,
                'expected': None
            },
            {
                'input': {'flag': True, 'value': None},
                'output': False,
                'expected': True
            },
            {
                'input': {'nums': [1, 5, 2]},
                'output': 0
            },
            {
                'input': {'data': {"a": 1}},
                'output': None  # 注意：null 在 Python 中是 None
            }
        ]
        
        test_file = self.write_test_file(test_cases_data, "test_dict_basic.txt")
        cases = parse_test_cases(test_file)
        
        # 保存解析结果用于调试
        self.save_parsed_result(test_file ,cases)
        
        # 验证解析结果
        self.assertEqual(len(cases), len(test_cases_data))
        
        for i, (original, parsed) in enumerate(zip(test_cases_data, cases)):
            with self.subTest(case=i, file=test_file):
                self.assertIsInstance(parsed, dict)
                self.assertEqual(parsed['input'], original['input'])
                self.assertEqual(parsed['output'], original['output'])
                self.assertEqual(parsed['expected'], original['expected'])

    def generate_random_test_cases(self, num_cases: int, depth: int, include_input: bool = True) -> List[_CASE_TYPE]:
        """生成随机测试用例数据
        
        :param num_cases: 生成的测试用例数量
        :param depth: 嵌套深度
        :param include_input: 是否包含"输入"关键词（字典格式）
        :return: 生成的测试用例数据列表
        """
        test_cases_data = []
        num_inputs = random.randint(1, 5)
        # 随机生成输入参数
        if include_input:
            for _ in range(num_cases):
                # 字典格式：生成参数名和值
                inputs_key = cjson._keys_random(num_inputs)
                inputs_val,_ = cjson.generate_list(depth,cjson._max_hash_num,num_inputs)
                # 仅在字典格式中生成 'output' 和 'expected'
                test_cases_data.append({
                    'input': dict(zip(inputs_key, inputs_val)),
                    'output': cjson.generate_obj(0,cjson._max_hash_num),
                    'expected': cjson.generate_obj(0,cjson._max_hash_num)
                })
        else:
            for _ in range(num_cases):
                # 元组格式：生成参数列表
                inputs,_ = cjson.generate_list(depth,cjson._max_hash_num,num_inputs)
                # 元组格式不包含 'output' 和 'expected'
                test_cases_data.append({
                    'input': tuple(inputs),
                    # 元组格式不包含 output 和 expected
                })
            
        return test_cases_data

    def random_test(self):
        """随机大批量基础类型，包含字典格式和元组格式"""
        def single_test()

    def test_parse_random_cases_with_format(self):
        """测试随机大批量基础类型，包含字典格式和元组格式"""
        # 测试不同嵌套深度
        for depth in [1, 2, 3]:
            with self.subTest(depth=depth):
                # 生成多个测试文件
                for batch in range(3):  # 3个批次
                    # 生成字典格式测试用例
                    dict_cases_data = self.generate_random_test_cases(
                        num_cases=5, depth=depth, include_input=True
                    )
                    dict_filename = f"random_dict_depth{depth}_batch{batch}.txt"
                    dict_test_file = self.write_test_file(
                        dict_cases_data, dict_filename, include_input=True
                    )
                    
                    # 修正1：正确计算 params_num（参数数量，即字典的长度）
                    params_num = len(dict_cases_data[0]['input']) if dict_cases_data else 1
                    
                    # 生成元组格式测试用例（指定参数数量）
                    tuple_cases_data = self.generate_random_test_cases(
                        num_cases=5, depth=depth, include_input=False, params_num=params_num
                    )
                    tuple_filename = f"random_tuple_depth{depth}_batch{batch}.txt"
                    tuple_test_file = self.write_test_file(
                        tuple_cases_data, tuple_filename, include_input=False, params_num=params_num
                    )
                    
                    # 解析字典格式测试文件
                    dict_cases = parse_test_cases(dict_test_file)
                    # 保存解析结果用于调试
                    self.save_parsed_result(dict_test_file,dict_cases)
                    # 验证字典格式解析结果
                    self.assertEqual(
                        len(dict_cases), len(dict_cases_data),
                        f"字典格式: File: {dict_test_file}, Expected {len(dict_cases_data)} cases but got {len(dict_cases)}"
                    )
                    for i, (original, parsed) in enumerate(zip(dict_cases_data, dict_cases)):
                        with self.subTest(case=i, file=dict_test_file, depth=depth, batch=batch, format="dict"):
                            self.assertIsInstance(parsed, dict)
                            self.assertEqual(parsed['input'], original['input'])
                            self.assertEqual(parsed['output'], original['output'])
                            self.assertEqual(parsed['expected'], original['expected'])
                    
                    # 解析元组格式测试文件
                    tuple_cases = parse_test_cases(tuple_test_file, params_num=params_num)
                    # 保存解析结果用于调试
                    self.save_parsed_result(tuple_test_file, tuple_cases)
                    # 验证元组格式解析结果
                    self.assertEqual(
                        len(tuple_cases), len(tuple_cases_data),
                        f"元组格式: File: {tuple_test_file}, Expected {len(tuple_cases_data)} cases but got {len(tuple_cases)}"
                    )
                    for i, (original, parsed) in enumerate(zip(tuple_cases_data, tuple_cases)):
                        with self.subTest(case=i, file=tuple_test_file, depth=depth, batch=batch, format="tuple"):
                            self.assertIsInstance(parsed, dict)
                            # 修正2：直接比较元组，不需要转换为字典
                            self.assertEqual(parsed['input'], original['input'])
                            # 元组格式不包含 output 和 expected，所以不验证

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
                    self.save_parsed_result(test_file, parsed_cases)
                    
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