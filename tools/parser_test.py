# tools/parser_test.py
import os
import unittest
import random
import hashlib
from typing import Any, List, Union, Dict, Tuple
from test_examples_parser import parse_test_cases

# 确保测试目录存在
TEST_DIR = "tools_test"
os.makedirs(TEST_DIR, exist_ok=True)

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

def value_to_str(v: Any) -> str:
    """将值转为多行字符串表示（模拟LeetCode格式）"""
    s = repr(v)
    if isinstance(v, (list, tuple, dict, set)) and len(s) > 50:
        # 美化长结构
        import json
        try:
            if isinstance(v, set):
                v_list = list(v)
                s = json.dumps(v_list, indent=2, ensure_ascii=False)
                s = "set(" + s + ")"
            else:
                s = json.dumps(v, indent=2, ensure_ascii=False)
        except:
            pass
    return s

def write_tuple_style_file(data: List[Tuple], filename: str):
    """写入无参数名格式"""
    with open(filename, 'w', encoding='utf-8') as f:
        for case in data:
            for item in case:
                f.write(value_to_str(item) + '\n')
            f.write('\n')

def write_dict_style_file(data: List[Dict], filename: str):
    """写入带参数名格式"""
    with open(filename, 'w', encoding='utf-8') as f:
        for case in data:
            f.write("输入\n")
            for k, v in case['input'].items():
                f.write(f"{k} =\n")
                f.write(value_to_str(v) + '\n')
            if 'output' in case:
                f.write("输出\n")
                f.write(value_to_str(case['output']) + '\n')
            if 'expected' in case:
                f.write("预期结果\n")
                f.write(value_to_str(case['expected']) + '\n')
            f.write('\n')

class TestTestExamplesParser(unittest.TestCase):
    
    def test_parse_basic_cases(self):
        test_content = """[1,2,3]
4

[1,1,2]
5
"""
        test_file = os.path.join(TEST_DIR, "base_case.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        cases = parse_test_cases(test_file)
        expected = [([1,2,3], 4), ([1,1,2], 5)]
        self.assertEqual(cases, expected)

    def test_parse_dict_style(self):
        test_content = """输入
nums =
[1,2,3]
k =
4
输出
0
预期结果
0

输入
nums =
[1,1,2]
k =
5
输出
1
"""
        test_file = os.path.join(TEST_DIR, "dict_case.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        cases = parse_test_cases(test_file)
        expected = [
            {
                'input': {'nums': [1,2,3], 'k': 4},
                'output': 0,
                'expected': 0
            },
            {
                'input': {'nums': [1,1,2], 'k': 5},
                'output': 1
            }
        ]
        self.assertEqual(cases, expected)

    def test_parse_random_cases(self):
        """测试1000次随机生成的嵌套结构"""
        for trial in range(1000):
            # 随机选择格式
            use_dict = random.choice([True, False])
            
            # 生成原始数据
            if use_dict:
                num_cases = random.randint(1, 5)
                original_data = []
                for _ in range(num_cases):
                    num_inputs = random.randint(1, 3)
                    inputs = {f"arg{i}": generate_random_value(max_depth=random.randint(1,3)) 
                             for i in range(num_inputs)}
                    case = {'input': inputs}
                    if random.random() > 0.3:
                        case['output'] = generate_random_value(max_depth=2)
                    if random.random() > 0.5:
                        case['expected'] = generate_random_value(max_depth=2)
                    original_data.append(case)
                
                # 生成唯一文件名
                raw_str = str(original_data).encode()
                fname = hashlib.md5(raw_str).hexdigest()[:8] + ".txt"
                filepath = os.path.join(TEST_DIR, fname)
                write_dict_style_file(original_data, filepath)
                
            else:
                num_cases = random.randint(1, 5)
                original_data = []
                for _ in range(num_cases):
                    num_args = random.randint(1, 4)
                    args = tuple(generate_random_value(max_depth=random.randint(1,3)) 
                                for _ in range(num_args))
                    original_data.append(args)
                
                raw_str = str(original_data).encode()
                fname = hashlib.md5(raw_str).hexdigest()[:8] + ".txt"
                filepath = os.path.join(TEST_DIR, fname)
                write_tuple_style_file(original_data, filepath)
            
            # 解析并比较
            try:
                parsed_data = parse_test_cases(filepath)
                self.assertEqual(original_data, parsed_data, 
                                 f"Mismatch in trial {trial} for file {fname}")
            except Exception as e:
                print(f"Failed at trial {trial}, file {fname}")
                print("Original:", original_data)
                print("Parsed  :", parsed_data)
                raise e

if __name__ == '__main__':
    unittest.main()