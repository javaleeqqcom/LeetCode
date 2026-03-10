# ========== 路径设置（勿删）==========
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# ===================================

print(f"当前工作目录：{os.getcwd()}")
      
from tools.solution_runner import SolutionRunner, _CASE_TYPE
from tools.custom_init import *
from typing import List, Union, Tuple, Dict, Any
# 导入 Path 库
from pathlib import Path

问题目录 = Path("3129. Find All Possible Stable Binary Arrays I")

# 初始化暴力解法运行器
暴力算法 = SolutionRunner(问题目录 / "P3129_bt0.py")
改进算法 = SolutionRunner(问题目录 /"P3129_V5（千问改的 错误！）.py")

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
expected_results = 暴力算法.run_as_expected(cases)
暴力算法.save_test_cases(expected_results)

results = 改进算法.run(expected_results,  log_suffix= "" , summary= True) 
