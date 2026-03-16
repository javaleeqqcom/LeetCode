import os

print(f"当前工作目录：{os.getcwd()}")
      
# ------------ 三选一进行调用来测试 -------------------
from tools.solution_runner import SolutionRunner, _CASE_TYPE
from typing import List, Union, Tuple, Dict, Any
# 导入 Path 库
from pathlib import Path
import numpy as np

问题目录 = Path("817. Linked List Components")

# 初始化暴力解法运行器
暴力算法 = SolutionRunner(问题目录 / "bt0.py")
# 改进算法 = SolutionRunner(问题目录 /"P3130_故意WRong.py")

测试样例提问_file = 暴力算法.relPath/"测试样例提问.txt"
if not 测试样例提问_file.exists():
    prompt_str = 暴力算法.get_cases_generator(问题目录/"题目说明.txt")
    with open(测试样例提问_file,"w",encoding="utf-8") as fp:
        fp.write(prompt_str)
    print("等待测试样例提问完成！")
    exit(0)

def Linked_List_Components问题的test_cases_generator(random_case_num: int, max_n: int = 10000):
    # random_case_num：生成的随机样例数量
    # max_n：链表最大长度（根据题目约束1 <= n <= 10^4）
    
    import random
    
    # 固定用例（用于覆盖各种可预见的边界情况）
    res = [
        # 示例1：基本连通分量测试
        ([0, 1, 2, 3], [0, 1, 3]),
        
        # 示例2：多个连通分量
        ([0, 1, 2, 3, 4], [0, 3, 1, 4]),
        
        # 边界情况1：链表长度为1
        ([5], [5]),
        
        # 边界情况2：nums包含所有链表节点值（整个链表是一个连通分量）
        ([0, 1, 2, 3, 4], [0, 1, 2, 3, 4]),
        
        # 边界情况3：nums只包含1个元素
        ([1, 2, 3, 4, 5], [3]),
        
        # 边界情况4：nums中所有元素在链表中都不连续（每个都是独立分量）
        ([0, 1, 2, 3, 4, 5], [0, 2, 4]),
        
        # 边界情况5：nums中的元素在链表开头连续
        ([0, 1, 2, 3, 4], [0, 1]),
        
        # 边界情况6：nums中的元素在链表末尾连续
        ([0, 1, 2, 3, 4], [3, 4]),
        
        # 边界情况7：nums中的元素在链表中间连续
        ([0, 1, 2, 3, 4, 5], [2, 3]),
        
        # 边界情况8：多个不连续的连通分量
        ([0, 1, 2, 3, 4, 5, 6, 7], [0, 1, 3, 4, 6, 7]),
        
        # 边界情况9：链表长度为2，nums包含两个连续元素
        ([10, 20], [10, 20]),
        
        # 边界情况10：链表长度为2，nums包含两个不连续元素（实际是连续的，因为只有两个节点）
        ([10, 20], [10]),
        
        # 边界情况11：nums元素分散在链表各处
        ([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [0, 2, 4, 6, 8]),
        
        # 边界情况12：只有一个连通分量但不在开头
        ([0, 1, 2, 3, 4, 5], [3, 4, 5]),
    ]
    
    # 全局状态记录器，用于查重
    generated_signatures = set()
    
    def 单随机样例生成器(n: int, nums_ratio: float):
        """
        生成单个随机测试用例
        n: 链表长度
        nums_ratio: nums长度占链表长度的比例 (0 < ratio <= 1)
        """
        # 生成链表值（0到n-1的唯一值，随机排列）
        link_values = list(range(n))
        random.shuffle(link_values)
        
        # 计算nums长度
        nums_len = max(1, int(n * nums_ratio))
        nums_len = min(nums_len, n)  # 确保不超过链表长度
        
        # 从链表中随机选择nums_len个值作为nums
        nums = random.sample(link_values, nums_len)
        
        return (link_values, nums)
    
    # 生成随机用例
    for i in range(random_case_num):
        # 规模参数随i增大而增大，覆盖不同规模
        # 使用对数增长，确保覆盖小、中、大规模
        if i < random_case_num // 4:
            # 小规模：1-100
            n = random.randint(1, 100)
        elif i < random_case_num // 2:
            # 中等规模：100-1000
            n = random.randint(100, 1000)
        elif i < random_case_num * 3 // 4:
            # 较大规模：1000-5000
            n = random.randint(1000, 5000)
        else:
            # 大规模：5000-max_n
            n = random.randint(5000, min(max_n, 10000))
        
        # nums比例随机变化，覆盖不同密度
        nums_ratio = random.uniform(0.1, 1.0)
        
        # 生成签名用于查重
        signature = (n, int(nums_ratio * 100))
        if signature not in generated_signatures:
            generated_signatures.add(signature)
            res.append(单随机样例生成器(n, nums_ratio))
    
    return res

cases = Linked_List_Components问题的test_cases_generator(random_case_num=100)
expected_results = 暴力算法.run_as_expected(cases,thread=1)

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
