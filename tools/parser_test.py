# tools/parser_test.py
import unittest
import os
import tempfile
import random
import string
from test_examples_parser import parse_test_cases, safe_eval

# 确保测试目录存在
TEST_DIR = "tools_test"
os.makedirs(TEST_DIR, exist_ok=True)

def generate_random_value(depth=0, max_depth=3):
    """生成随机嵌套的基础 Python 值"""
    if depth >= max_depth:
        # 叶子节点：基础类型
        choice = random.choice(['int', 'float', 'str', 'bool', 'none'])
        if choice == 'int':
            return random.randint(-100, 100)
        elif choice == 'float':
            return round(random.uniform(-100.0, 100.0), 2)
        elif choice == 'str':
            length = random.randint(1, 10)
            return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        elif choice == 'bool':
            return random.choice([True, False])
        else:  # none
            return None
    
    # 非叶子节点：容器类型
    container_type = random.choice(['list', 'tuple', 'dict'])
    size = random.randint(0, 5)
    
    if container_type == 'list':
        return [generate_random_value(depth+1, max_depth) for _ in range(size)]
    elif container_type == 'tuple':
        return tuple(generate_random_value(depth+1, max_depth) for _ in range(size))
    else:  # dict
        d = {}
        for _ in range(size):
            key = ''.join(random.choices(string.ascii_letters, k=random.randint(1, 5)))
            d[key] = generate_random_value(depth+1, max_depth)
        return d

def write_test_file(inputs, output, filename):
    """将测试用例写入文件"""
    with open(filename, 'w') as f:
        for i, inp in enumerate(inputs, 1):
            f.write(f"input{i} = {repr(inp)}\n")
        f.write(f"output = {repr(output)}\n")

class TestTestExamplesParser(unittest.TestCase):
    def test_parse_basic_cases(self):
        test_file_content = """
# Test Case 1
input1 = [1,2,3]
input2 = 4
output = [1,2,3]

# Test Case 2
input1 = [1,1,2]
input2 = 5
output = [1,2]
        """
        test_file_path = os.path.join(TEST_DIR, "base_case.txt")
        with open(test_file_path, 'w') as f:
            f.write(test_file_content)
        
        cases = parse_test_cases(test_file_path)
        
        self.assertEqual(len(cases), 2)
        self.assertEqual(cases[0][0], [1,2,3])
        self.assertEqual(cases[0][1], 4)
        self.assertEqual(cases[0][2], [1,2,3])
        self.assertEqual(cases[1][0], [1,1,2])
        self.assertEqual(cases[1][1], 5)
        self.assertEqual(cases[1][2], [1,2])

    def test_safe_eval(self):
        self.assertEqual(safe_eval("123"), 123)
        self.assertEqual(safe_eval("[1,2,3]"), [1,2,3])
        self.assertEqual(safe_eval("True"), True)
        self.assertEqual(safe_eval("None"), None)
        self.assertEqual(safe_eval("{'a': 1}"), {'a': 1})
        self.assertEqual(safe_eval("(1, 2)"), (1, 2))
        self.assertEqual(safe_eval("{1, 2, 3}"), {1, 2, 3})
        self.assertEqual(safe_eval("invalid"), "invalid")

    def test_parse_random_cases(self):
        """测试多批次随机生成的复杂嵌套结构"""
        random.seed(42)  # 固定种子确保可重现
        
        for depth in range(1, 4):  # 测试嵌套深度 1~3
            for batch in range(5):  # 每个深度5个批次
                # 生成随机输入和输出
                num_inputs = random.randint(1, 3)
                inputs = [
                    generate_random_value(max_depth=depth) 
                    for _ in range(num_inputs)
                ]
                output = generate_random_value(max_depth=depth)
                
                # 生成唯一文件名
                filename = os.path.join(
                    TEST_DIR, 
                    f"random_depth{depth}_batch{batch}_{hash(str(inputs)+str(output)) % 10000}.txt"
                )
                
                # 写入测试文件
                write_test_file(inputs, output, filename)
                
                # 解析并验证
                cases = parse_test_cases(filename)
                self.assertEqual(len(cases), 1)
                
                parsed_inputs = cases[0][:-1]
                parsed_output = cases[0][-1]
                
                # 验证所有值都正确解析
                for i, (orig, parsed) in enumerate(zip(inputs, parsed_inputs)):
                    self.assertEqual(parsed, orig, 
                                   f"Depth {depth}, batch {batch}, input {i} mismatch")
                self.assertEqual(parsed_output, output,
                               f"Depth {depth}, batch {batch}, output mismatch")
                
if __name__ == '__main__':
    unittest.main()