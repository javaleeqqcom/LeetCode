import os

# ------------ 三选一进行调用来测试 -------------------
from tools.solution_runner import SolutionRunner, _CASE_TYPE
from typing import List, Union, Tuple, Dict, Any
# 导入 Path 库
from pathlib import Path
import numpy as np

问题目录 = Path("817. Linked List Components")

# 初始化暴力解法运行器
暴力算法 = SolutionRunner(问题目录 / "bt0.py")
改进算法 = SolutionRunner(问题目录 / "V1.py")

测试样例提问_file = 暴力算法.relPath/"测试样例提问.txt"
if not 测试样例提问_file.exists():
    prompt_str = 暴力算法.get_cases_generator(问题目录/"题目说明.txt")
    with open(测试样例提问_file,"w",encoding="utf-8") as fp:
        fp.write(prompt_str)
    print("等待测试样例提问完成！")
    exit(0)

def test_cases_generator(random_case_num: int, max_n: int = 10000):
    """
    生成 LeetCode 817 题“Linked List Components”的测试用例。
    返回列表，每个元素为 (head_list, nums_list) 元组。
    head_list 将自动转换为 ListNode，nums_list 保持为列表。
    """
    import random

    # ---------- 固定边界用例 ----------
    fixed = [
        # 最小规模，单节点包含
        ([0], [0]),
        # 两个节点，一个在 nums 中
        ([0, 1], [0]),
        # 两个节点，都在 nums 中且连续
        ([0, 1], [0, 1]),
        # 三个节点，两个不连续
        ([0, 1, 2], [0, 2]),
        # 示例 1
        ([0, 1, 2, 3], [0, 1, 3]),
        # 示例 2
        ([0, 1, 2, 3, 4], [0, 3, 1, 4]),
        # 全部包含，应为一个组件
        ([0, 1, 2, 3], [0, 1, 2, 3]),
        # 多个不连续节点
        ([0, 1, 2, 3, 4], [0, 2, 4]),
        # nums 顺序无关测试
        ([0, 1, 2], [1, 0, 2]),
        # 稍大一点的固定用例
        (list(range(10)), [0, 9]),
    ]

    # ---------- 随机用例生成 ----------
    random_cases = []
    for _ in range(random_case_num):
        # 随机确定链表长度（1 ~ max_n）
        n = random.randint(1, max_n)
        # 生成一个 0 ~ n-1 的随机排列作为链表顺序
        values = random.sample(range(n), n)  # 保证唯一且值域正确
        # 随机选择 nums 的大小（1 ~ n）
        k = random.randint(1, n)
        nums = random.sample(values, k)
        # 打乱 nums 顺序（题目不要求有序）
        random.shuffle(nums)

        random_cases.append((values, nums))

    # 合并固定用例与随机用例
    return fixed + random_cases

cases = test_cases_generator(random_case_num=10,max_n = 10)
expected_results = 暴力算法.run_as_expected(cases,thread=1)

print("expected_results[0]=", expected_results[0])

暴力算法.save_test_cases(expected_results)

print("======== 暴力算法比较 ============")

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

print("======== 改进算法比较 ============")

# 单线程
print("=== 单线程 ===")
results_single = 改进算法.run(expected_results,thread=1)

# 多线程
print("=== 多线程 ===")
results_multi = 改进算法.run(expected_results, thread=4, timeout_s=60)

# 比对
print(f"单线程结果数: {len(results_single)}")
print(f"多线程结果数: {len(results_multi)}")
print(f"结果一致: {len(results_single) == len(results_multi)}")
