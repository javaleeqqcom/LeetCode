# test_cases_generator.py
from typing import List, Dict, Any
import random
import math

# 要对生成规模排序，优先小样例，有利于分析较为简洁的错误
def test_cases_generator(random_case_num: int, max_n: int = 10**5) -> List[Dict[str, Any]]:
    """
    生成 Jump Game IX 的测试用例。
    
    Args:
        random_case_num: 随机生成的测试用例数量。
        max_n: 数组最大长度（默认10^5，符合题目约束）。
    
    Returns:
        List of _CASE: 包含 input (dict) 的测试用例列表。
    """
    
    cases = []
    
    # --- 规模参数生成 (Outside the main loop) ---
    # 采用负指数分布生成规模，并排序，确保 n 随 i 增大而增大
    # 生成 random_case_num 个规模参数
    scales = []
    lam = 3.0 / max_n  # 调整 lambda 以适应 max_n 的范围
    
    for _ in range(random_case_num):
        # 使用负指数分布生成随机数，确保小规模数据多，大规模数据少
        sample = random.expovariate(lam)
        # 将生成的浮点数限制在有效范围内并转为整数
        # 长度=1的只需生成一次
        n = max(2, min(max_n, int(sample)))
        scales.append(n)
    
    # 关键步骤：在外面生成并排序
    # 这样可以保证测试用例从小规模到大规模排列，避免大用例卡死
    scales.sort()
    
    # --- 随机用例生成 (Random Cases) ---
    for i, n in enumerate(scales):
        # 生成随机数组
        nums = list(range(1,n+1))
        random.shuffle(nums)
        
        cases.append({
            "input": {"nums": nums},
            "cid": i
        })
    
    return cases
