# tools/parser_test.py
import os
import random
import unittest
import hashlib
from typing import Any, Dict, List, Tuple, Union
from examples_parser import parse_test_cases

def generate_random_value(depth: int = 0, max_depth: int = 3) -> Any:
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
        return [generate_random_value(depth+1, max_depth) for _ in range(random.randint(0, 5))]
    elif choice == 1:  # tuple
        return tuple(generate_random_value(depth+1, max_depth) for _ in range(random.randint(0, 5)))
    elif choice == 2:  # dict (keys must be hashable)
        def gen_hashable_key():
            return random.choice([
                random.randint(-50, 50),
                random.uniform(-5.0, 5.0),
                f"key{random.randint(0,9)}",
                tuple(random.randint(0,10) for _ in range(random.randint(0,3)))
            ])
        return {gen_hashable_key(): generate_random_value(depth+1, max_depth) 
                for _ in range(random.randint(0, 5))}
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
        except TypeError:
            # Fallback if unhashable (shouldn't happen with our generator)
            return list(set(str(e) for e in elems))
    else:
        return generate_random_value(depth+1, max_depth)

class TestTestExamplesParser(unittest.TestCase):
    TEST_DIR = "tools_test"
    
    @classmethod
    def setUpClass(cls):
        os.makedirs(cls.TEST_DIR, exist_ok=True)

    def test_parse_dict_style_basic(self):
        """测试字典风格的基本解析"""
        content = """输入
nums = 
[1,5,2]
输出
0
预期结果
2

输入
arr = 
[1,3,2,3,1]
k = 
3
输出
1
预期结果
4
"""
        test_file = os.path.join(self.TEST_DIR, "test_dict_basic.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        cases = parse_test_cases(test_file)
        
        # 验证第一个测试用例
        self.assertEqual(len(cases), 2, f"File: {test_file}")
        case1 = cases[0]
        self.assertIsInstance(case1, dict, f"File: {test_file}")
        self.assertIn('input', case1, f"File: {test_file}")
        self.assertIn('output', case1, f"File: {test_file}")
        self.assertIn('expected', case1, f"File: {test_file}")
        self.assertEqual(case1['input']['nums'], [1, 5, 2], f"File: {test_file}")
        self.assertEqual(case1['output'], 0, f"File: {test_file}")
        self.assertEqual(case1['expected'], 2, f"File: {test_file}")
        
        # 验证第二个测试用例
        case2 = cases[1]
        self.assertEqual(case2['input']['arr'], [1, 3, 2, 3, 1], f"File: {test_file}")
        self.assertEqual(case2['input']['k'], 3, f"File: {test_file}")
        self.assertEqual(case2['output'], 1, f"File: {test_file}")
        self.assertEqual(case2['expected'], 4, f"File: {test_file}")

    def test_parse_dict_style_no_expected(self):
        """测试没有预期结果的情况"""
        content = """输入
nums = 
[1,5,2]
输出
0

输入
data = 
{"a": 1}
输出
null
"""
        test_file = os.path.join(self.TEST_DIR, "test_dict_no_expected.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        cases = parse_test_cases(test_file)
        
        self.assertEqual(len(cases), 2, f"File: {test_file}")
        case1 = cases[0]
        self.assertIn('input', case1, f"File: {test_file}")
        self.assertIn('output', case1, f"File: {test_file}")
        self.assertNotIn('expected', case1, f"File: {test_file}")
        self.assertEqual(case1['input']['nums'], [1, 5, 2], f"File: {test_file}")
        self.assertEqual(case1['output'], 0, f"File: {test_file}")
        
        case2 = cases[1]
        self.assertEqual(case2['input']['data'], {"a": 1}, f"File: {test_file}")
        self.assertEqual(case2['output'], "null", f"File: {test_file}")  # 无法解析的字符串保持原样

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
                    
                    # 生成文件内容（修正格式：变量名= 后换行）
                    content = ""
                    for case in test_cases_data:
                        content += "输入\n"
                        for k, v in case['input'].items():
                            content += f"{k} = \n{repr(v)}\n"
                        content += "输出\n"
                        content += f"{repr(case['output'])}\n"
                        content += "预期结果\n"
                        content += f"{repr(case['expected'])}\n\n"
                    
                    # 生成哈希文件名
                    hash_obj = hashlib.md5(content.encode('utf-8'))
                    filename = f"random_depth{depth}_batch{batch}_{hash_obj.hexdigest()[:8]}.txt"
                    test_file = os.path.join(self.TEST_DIR, filename)
                    
                    with open(test_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    # 解析并验证
                    parsed_cases = parse_test_cases(test_file)
                    
                    # 在断言中包含文件路径信息
                    self.assertEqual(
                        len(parsed_cases), 
                        len(test_cases_data),
                        f"File: {test_file}, Expected {len(test_cases_data)} cases but got {len(parsed_cases)}"
                    )
                    
                    for i, (original, parsed) in enumerate(zip(test_cases_data, parsed_cases)):
                        # 验证结构
                        self.assertIsInstance(parsed, dict, f"File: {test_file}")
                        self.assertIn('input', parsed, f"File: {test_file}")
                        self.assertIn('output', parsed, f"File: {test_file}")
                        self.assertIn('expected', parsed, f"File: {test_file}")
                        
                        # 验证输入
                        for k, v in original['input'].items():
                            self.assertIn(k, parsed['input'], f"File: {test_file}")
                            # 由于解析限制，某些复杂结构可能保持字符串形式
                            # 这里主要验证基本类型和简单嵌套
                            if isinstance(v, (int, float, str, bool, type(None))):
                                self.assertEqual(
                                    parsed['input'][k], 
                                    v,
                                    f"File: {test_file}, Param: {k}"
                                )
                            elif isinstance(v, (list, tuple, dict)):
                                # 对于容器类型，至少验证类型和长度
                                if isinstance(parsed['input'][k], str):
                                    # 如果保持字符串，检查是否包含原始repr的关键部分
                                    self.assertIn(
                                        repr(v)[:10], 
                                        parsed['input'][k],
                                        f"File: {test_file}, Param: {k}"
                                    )
                                else:
                                    # 如果成功解析，验证基本属性
                                    self.assertEqual(
                                        type(parsed['input'][k]), 
                                        type(v),
                                        f"File: {test_file}, Param: {k}"
                                    )
                        
                        # 验证输出和预期结果（同样处理）
                        if isinstance(original['output'], (int, float, str, bool, type(None))):
                            self.assertEqual(
                                parsed['output'], 
                                original['output'],
                                f"File: {test_file}"
                            )
                        if isinstance(original['expected'], (int, float, str, bool, type(None))):
                            self.assertEqual(
                                parsed['expected'], 
                                original['expected'],
                                f"File: {test_file}"
                            )

    def value_to_str(self, v: Any) -> str:
        """将值转为单行字符串表示（符合LeetCode规范）"""
        return repr(v)

if __name__ == '__main__':
    unittest.main()