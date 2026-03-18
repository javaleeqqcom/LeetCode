try:from tools.custom_init import *
except:None

import os

print(f"当前工作目录：{os.getcwd()}")
      
# ------------ 三选一进行调用来测试 -------------------
from tools.solution_runner import SolutionRunner, _CASE_TYPE
from typing import List, Union, Tuple, Dict, Any
# 导入 Path 库
from pathlib import Path
import numpy as np

问题目录 = Path("1727. Largest Submatrix With Rearrangements")

# 初始化暴力解法运行器
暴力算法 = SolutionRunner(问题目录 / "bt0.py")

测试样例提问_file = 暴力算法.relPath/"测试样例提问.txt"
if not 测试样例提问_file.exists():
    prompt_str = 暴力算法.get_cases_generator(问题目录/"题目说明.txt")
    with open(测试样例提问_file,"w",encoding="utf-8") as fp:
        fp.write(prompt_str)
    print("等待测试样例提问完成！")
    exit(0)

# with open(暴力算法.relPath/"生成器.py","r",encoding="utf-8") as fp:
#     exec(fp.read(), globals())
#     test_cases_generator = globals()["test_cases_generator"]

import random
import math
from typing import List, Tuple

def test_cases_generator(random_case_num: int, max_product = 10**5 ) -> List[Tuple[List[List[int]]]]:
    """
    生成用于测试 LeetCode 1727. Largest Submatrix With Rearrangements 的测试用例。
    每个测试用例是一个二元矩阵，输出格式为 (matrix, ) 的元组，与题目输入要求一致。
    """
    # ========== 固定边界用例 ==========
    fixed_cases = [
        # 示例
        ([[0,0,1],[1,1,1],[1,0,1]],),      # 示例1，预期4
        ([[1,0,1,0,1]],),                  # 示例2，预期3
        ([[1,1,0],[1,0,1]],),               # 示例3，预期2
        # 极端单元素
        ([[0]],),                            # 只有0
        ([[1]],),                            # 只有1
        # 全相同
        ([[1,1],[1,1]],),                    # 全1 2x2，预期4
        ([[0,0],[0,0]],),                    # 全0 2x2，预期0
        # 单行/单列
        ([[1,1,1,1,1,1,1]],),                # 单行全1，预期7
        ([[1],[1],[1],[1],[1]],),             # 单列全1，预期5
        # 混合形状
        ([[1,0,0,1],[1,0,0,1],[1,1,1,1]],), # 部分列连续1
        ([[1,0],[1,0],[0,1]],),              # 两列交替
        ([[1,0,1,0,1,0,1],[0,1,0,1,0,1,0]],), # 棋盘格，预期1
        ([[1,1,1],[1,1,1],[1,1,0]],),         # 缺一角，预期6？
    ]

    # ========== 随机用例生成 ==========
    res = list(fixed_cases)

    for _ in range(random_case_num):
        # 随机生成满足 m*n ≤ max_product 的矩阵尺寸
        # 先随机 m，再根据剩余上限确定 n
        # 为避免死循环，限制尝试次数
        while True:
            # m 取值范围 [1, max_product]，但为了防止 n 过小，可以适当限制 m 上限为 1000，
            # 不过题目允许 m 接近 max_product 而 n=1，所以也可以保留。
            m = random.randint(1, max_product)
            max_n = max_product // m
            if max_n >= 1:
                n = random.randint(1, max_n)
                break

        # 生成随机 0/1 矩阵
        matrix = [[random.randint(0, 1) for _ in range(n)] for _ in range(m)]
        res.append((matrix,))

    return res

cases_path = 暴力算法.auto_path_cases()
if cases_path.exists():
    print(f"从文件中读取测试用例：{cases_path}")
    expected_results = 暴力算法.read_test_case(cases_path)
else:
    cases = test_cases_generator(random_case_num=1000,max_product = 100)
    expected_results = 暴力算法.run_as_expected(cases,thread=1)
    暴力算法.save_test_cases(expected_results , cases_path)

print("expected_results[0]=", expected_results[0])

改进算法 = SolutionRunner(问题目录 / "V2.py")

# 多线程
print("=== 多线程 ===")
results_multi = 改进算法.run(expected_results, thread=4, timeout_s=60,summary=True)
