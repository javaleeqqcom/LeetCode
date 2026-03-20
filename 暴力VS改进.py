try:from args_parser import *
except:None
import os,sys
print(f"当前工作目录：{os.getcwd()}")
      
# ------------ 三选一进行调用来测试 -------------------
from tools.solution_runner import SolutionRunner
from typing import List, Union, Tuple, Dict, Any
# 导入 Path 库
from pathlib import Path
import numpy as np

问题目录 = Path(r"特殊the_fun的题目\面试题 02.08. Linked List Cycle LCCI")
sys.path.insert(0, str(问题目录))
from bt0 import Solution

# 初始化暴力解法运行器
暴力算法 = SolutionRunner(问题目录 / "bt0.py")

attached_attentions = [
    "此题适合答案驱动，无需暴力算法求解expected，注意答案为成环节点下标，而非节点value。"
]

测试样例提问_file = 暴力算法.relPath/"测试样例提问.txt"
if not 测试样例提问_file.exists():
    prompt_str = 暴力算法.get_cases_generator("题目说明.txt",attached_attentions = attached_attentions) # 会自动加相对路径
    with open(测试样例提问_file,"w",encoding="utf-8") as fp:
        fp.write(prompt_str)
    print("等待测试样例提问完成！")
    exit(0)

cases_path = 暴力算法.auto_path_cases()
if cases_path.exists():
    print(f"从文件中读取测试用例：{cases_path}")
    expected_results = 暴力算法.read_test_case(cases_path)
elif 暴力算法.try_read_cases_and_exchange_codes():
    cases = 暴力算法.test_cases_generator(random_case_num = 100, max_n = 100)
    if len(cases) == 0:
        raise ValueError("没有生成测试用例！")
    if isinstance(cases[0],dict):
        expected_results = cases
    else:
        expected_results = 暴力算法.run_as_expected(cases,thread=1)
        暴力算法.save_test_cases(expected_results , cases_path)

print("expected_results[0]=", expected_results[0])

改进算法 = SolutionRunner(问题目录 / "bt0.py")

# 多线程
print("=== 多线程 ===")
print(改进算法.try_read_cases_and_exchange_codes())
results_multi = 改进算法.run(expected_results, thread=4, timeout_s=60,summary=True)
