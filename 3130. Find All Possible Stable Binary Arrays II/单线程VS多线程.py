# ========== 路径设置（勿删）==========
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# ===================================

print(f"当前工作目录：{os.getcwd()}")
      
# ------------ 三选一进行调用来测试 -------------------
# from tools.solution_runner import SolutionRunner, _CASE_TYPE
from tools.solution_runner_err import SolutionRunner, _CASE_TYPE
# from tools.solution_runner_dummy import SolutionRunner, _CASE_TYPE

from tools.custom_init import *
from typing import List, Union, Tuple, Dict, Any
# 导入 Path 库
from pathlib import Path

问题目录 = Path("3130. Find All Possible Stable Binary Arrays II")

# 初始化暴力解法运行器
暴力算法 = SolutionRunner(问题目录 / "P3130_bt.py")
改进算法 = SolutionRunner(问题目录 /"P3130_V1.py")

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

cases = cases_generation(num_test_cases= 100,seed=42)
expected_results = 暴力算法.run_as_expected(cases,thread=1)

暴力算法.save_test_cases(expected_results)

# 单线程
print("=== 单线程 ===")
results_single = 暴力算法.run_as_expected(cases, thread=1, timeout_s=60)

# 多线程
print("=== 多线程 ===")
results_multi = 暴力算法.run_as_expected(cases, thread=4, timeout_s=60)

# 比对
print(f"单线程结果数: {len(results_single)}")
print(f"多线程结果数: {len(results_multi)}")
print(f"结果一致: {len(results_single) == len(results_multi)}")

right = 0
for case in results_single:
    if case['expected'] != case['output']:
        print(f"wrong: {case}")
    else:
        right += 1
print(f"right/total: {right}/{len(results)}")
