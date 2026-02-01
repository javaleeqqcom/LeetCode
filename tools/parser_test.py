# tools/parser_test.py
import unittest
from test_examples_parser import parse_test_cases, safe_eval

class TestTestExamplesParser(unittest.TestCase):
    def test_parse_basic_cases(self):
        test_file = """
        # Test Case 1
        input1 = [1,2,3]
        input2 = 4
        output = [1,2,3]

        # Test Case 2
        input1 = [1,1,2]
        input2 = 5
        output = [1,2]
        """
        # 保存到临时文件
        with open('test_cases.txt', 'w') as f:
            f.write(test_file)
        
        cases = parse_test_cases('test_cases.txt')
        
        # 验证解析结果
        self.assertEqual(len(cases), 2)
        
        # 测试用例1: (input1, input2, output)
        self.assertEqual(cases[0][0], [1,2,3])  # input1
        self.assertEqual(cases[0][1], 4)        # input2
        self.assertEqual(cases[0][2], [1,2,3])  # output
        
        # 测试用例2
        self.assertEqual(cases[1][0], [1,1,2])
        self.assertEqual(cases[1][1], 5)
        self.assertEqual(cases[1][2], [1,2])

    def test_safe_eval(self):
        self.assertEqual(safe_eval("123"), 123)
        self.assertEqual(safe_eval("[1,2,3]"), [1,2,3])
        self.assertEqual(safe_eval("True"), True)
        self.assertEqual(safe_eval("None"), None)  # 保留为字符串
        self.assertEqual(safe_eval("invalid"), "invalid")  # 无法解析

if __name__ == '__main__':
    unittest.main()