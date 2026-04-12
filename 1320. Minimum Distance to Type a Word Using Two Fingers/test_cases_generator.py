# test_cases_generator.py
from typing import List, Dict, Any, Tuple
from random import randint, choice
import string

# 定义测试用例类型
_CASE = Dict[str, Any]

def test_cases_generator(random_case_num: int, max_length: int = 10) -> List[_CASE]:
    """
    生成用于测试 minimumDistance 函数的测试用例。
    
    Args:
        random_case_num: 生成的随机样例数量。
        max_length: 随机字符串的最大长度（受限于暴力算法的性能，不宜过大）。
    
    Returns:
        List[_CASE]: 包含输入和可选期望值的测试用例列表。
    """
    
    # === 1. 固定用例 (Fixed Cases) ===
    # 这些用例覆盖题目给出的示例以及一些明显的边界情况
    # 格式: {"input": (word,), "cid": "描述", "expected": value}
    fixed_cases = [
        # 题目示例 1: "CAKE" -> 3
        {"input": ("CAKE",), "cid": "Example 1", "expected": 3},
        
        # 题目示例 2: "HAPPY" -> 6
        {"input": ("HAPPY",), "cid": "Example 2", "expected": 6},
    ]
    
    # === 2. 随机用例生成 (Random Cases) ===
    # 由于学生的代码是暴力递归 O(2^n)，max_length 必须严格控制
    res = []
    
    for i in range(random_case_num):
        # === 规模参数设计 ===
        # 1. 随机生成长度，使用指数分布或简单随机，确保大部分是小规模
        # 为了防止暴力算法超时，长度限制在 2 到 min(8, max_length) 之间
        # (因为 2^10 = 1024 还行，但 2^15=32768 就开始慢了)
        n = randint(2, min(8, max_length))
        
        # 2. 生成随机字符串
        word = ''.join(choice(string.ascii_uppercase) for _ in range(n))
        
        # 3. 构造输入参数
        # 注意: input 必须是 Tuple (因为题目参数没有命名，是 positional)
        input_params = (word,)
        
        # 4. 创建测试用例
        # 由于暴力算法太慢，且我们无法在这里运行正确的标准答案（系统会并发运行学生代码），
        # 我们不提供 "expected" 字段，仅提供输入，由系统框架运行学生代码并对比不同方法的结果
        # 或者，如果框架允许，我们可以在这里运行一个简化的模拟（但根据文档，不需要我们运行）
        case = {
            "input": input_params,
            "cid": f"Random_{i}_{n}chars"
            # 不包含 "expected"，因为构造答案比较复杂且容易超时
            # 系统框架通常会用一个已知正确的标准答案（如动态规划解法）来对比
            # 但在本生成代码中，我们只负责生成输入
        }
        res.append(case)
    
    # === 3. 返回所有用例 ===
    # 混合固定用例和随机用例
    return fixed_cases + res