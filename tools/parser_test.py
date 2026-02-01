# tools/parser_test.py
import os
import random
import unittest
import hashlib
from typing import Any, Dict, List, Tuple, Union
from examples_parser import parse_test_cases
import json
import os
import random

class TestTestExamplesParser(unittest.TestCase):
    TEST_DIR = "tools_test"
    
    @classmethod
    def setUpClass(cls):
        os.makedirs(cls.TEST_DIR, exist_ok=True)

    def write_test_file(self, test_cases_data: List[Dict], filename: str) -> str:
        """将测试数据写入符合LeetCode格式的文件"""
        test_file = os.path.join(self.TEST_DIR, filename)
        content = ""
        for case in test_cases_data:
            # 写入"输入"部分
            content += "输入\n"
            for k, v in case['input'].items():
                content += f"{k} =\n{repr(v)}\n"
            # 写入"输出"部分
            content += "输出\n"
            content += f"{repr(case['output'])}\n"
            # 写入"预期结果"部分（如果存在）
            if 'expected' in case:
                content += "预期结果\n"
                content += f"{repr(case['expected'])}\n"
            content += "\n"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return test_file

    def save_parsed_result(self, parsed_cases: List, original_filename: str):
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
        self.save_parsed_result(cases, test_file)
        
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
        self.save_parsed_result(cases, test_file)
        
        self.assertEqual(len(cases), len(test_cases_data), f"File: {test_file}")
        for i, (original, parsed) in enumerate(zip(test_cases_data, cases)):
            with self.subTest(case=i, file=test_file):
                self.assertIsInstance(parsed, dict)
                self.assertEqual(parsed['input'], original['input'])
                self.assertEqual(parsed['output'], original['output'])
                self.assertNotIn('expected', parsed)

    def generate_random_value(self, depth: int = 0, max_depth: int = 3) -> Any:
        """生成随机嵌套基础类型值"""
        if depth >= max_depth:
            choices = [
                random.randint(-100, 100),
                random.uniform(-10.0, 10.0),
                random.choice([True, False, None]),
                f"str{random.randint(0,9)}"
            ]
            return random.choice(choices)
        choice = random.randint(0, 4)
        if choice == 0:  # list
            return [self.generate_random_value(depth+1, max_depth) for _ in range(random.randint(0, 5))]
        elif choice == 1:  # tuple
            return tuple(self.generate_random_value(depth+1, max_depth) for _ in range(random.randint(0, 5)))
        elif choice == 2:  # dict (keys must be hashable)
            def gen_hashable_key():
                return random.choice([
                    random.randint(-50, 50),
                    random.uniform(-5.0, 5.0),
                    f"key{random.randint(0,9)}",
                    tuple(random.randint(0,10) for _ in range(random.randint(0,3)))
                ])
            return {gen_hashable_key(): self.generate_random_value(depth+1, max_depth) for _ in range(random.randint(0, 5))}
        elif choice == 3:  # set (only hashable elements)
            def gen_hashable_elem():
                return random.choice([
                    random.randint(-50, 50),
                    random.uniform(-5.0, 5.0),
                    f"elem{random.randint(0,9)}",
                    tuple(random.randint(0,10) for _ in range(random.randint(0,2)))
                ])
            elems = [gen_hashable_elem() for _ in range(random.randint(0, 5))]
            try:
                return set(elems)
            except TypeError:  # Fallback if unhashable (shouldn't happen with our generator)
                return list(set(str(e) for e in elems))
        else:
            return self.generate_random_value(depth+1, max_depth)

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
                            inputs[param_name] = self.generate_random_value(0, depth)
                        # 随机生成输出和预期结果
                        output_val = self.generate_random_value(0, depth)
                        expected_val = self.generate_random_value(0, depth)
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
                    self.save_parsed_result(parsed_cases, test_file)
                    
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
                            
                            # 验证输出
                            if isinstance(original['output'], (int, float, str, bool, type(None), list, tuple, dict)):
                                if isinstance(parsed['output'], str):
                                    self.assertEqual(parsed['output'], repr(original['output']))
                                else:
                                    self.assertEqual(parsed['output'], original['output'])
                            
                            # 验证预期结果
                            if isinstance(original['expected'], (int, float, str, bool, type(None), list, tuple, dict)):
                                if isinstance(parsed['expected'], str):
                                    self.assertEqual(parsed['expected'], repr(original['expected']))
                                else:
                                    self.assertEqual(parsed['expected'], original['expected'])

if __name__ == '__main__':
    unittest.main()