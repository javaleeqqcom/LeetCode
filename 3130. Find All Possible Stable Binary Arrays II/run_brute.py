import os

print(f"当前工作目录：{os.getcwd()}")
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tools  # 触发 __init__.py
from tools.solution_runner import SolutionRunner, _CASE_TYPE
from typing import List, Union, Tuple, Dict, Any

# 初始化暴力解法运行器
brute = SolutionRunner("3130. Find All Possible Stable Binary Arrays II/P3130_bt.py")

# 生成测试用例指引文件
# ask_file = None  # 设置为None将使用与brute.py同名的txt文件
# brute.get_ask_for_cases(ask_file) 
# exit(0)

import numpy as np
from typing import List, Union, Optional, Tuple

def cases_generation(
    num_test_cases: int = 12, 
    # max_array_length: int = 25, 
    seed: Optional[int] = None
) -> List[Tuple]:
    # 设置随机种子（仅影响后续随机生成部分）
    if seed is not None:
        np.random.seed(seed)
    
    test_cases = []
    # 补充随机用例至目标数量
    while len(test_cases) < num_test_cases:
        bits = np.random.randint(1, 4)
        one = int(round(bits * np.random.random()))
        zero = bits - one
        limit = np.random.randint(1, bits+1)

        test_cases.append((one,zero,limit))
    
    return test_cases

# 保存测试用例，并自动运行暴力算法生成expected结果

cases = cases_generation(num_test_cases= 10,seed=42)

# brute.save_test_cases(cases)
# output = brute.run(cases,only_log_wrong=True)

# 可以用 tuple_to_cases 将 tuple 格式的 test_cases 转换为 list of _CASE_TYPE
fotmat_cases = brute.tuple_to_cases(cases)
# brute.save_test_cases(fotmat_cases)
output = brute.run(fotmat_cases,only_log_wrong=True)

expected_results = brute.get_expected_cases(output)
brute.save_test_cases(expected_results)

print("\n🎉 暴力测试用例生成完成！现在可以使用这些用例测试优化算法了。")
print("🔍 下一步: 创建一个新的SolutionRunner实例加载优化算法，然后使用runner.read_test_case()读取生成的JSON测试文件")

