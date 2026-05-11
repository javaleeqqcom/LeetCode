# cases_generator.py
from typing import List, Dict, Any
from random import *

# 要对生成规模排序，优先小样例，有利于分析较为简洁的错误
def cases_generator(case_num: int, max_n: int = 10**5) -> List[Dict[str, Any]]:
    """
    生成 Jump Game IX 的测试用例。
    该测试用例要求 nums[j] != nums[i]，才可执行跳跃动作，因此测试样例设计分为两种情况：
    A1. 数组无重复元素，用于高效检验程序的计算能力
    A2. 数组有重复元素，用于检验程序的鲁棒性
    又因为数组元素之间的差值不影响结果，但题目要求 1 <= nums[i] <= 10^9，因此数值大小也分为两种情况：
    B1. 长度为 n 的数组，当 n 较小时，数值仅取 [1,n]，方便DEBUG错误时阅读小数字体验较好
    B2. 数值取 [1,MAX]，用于限制作答者用暴力桶排序等方法通过测试用例
    又因为题目的跳跃规则：
    Jump to index j where j > i is allowed only if nums[j] < nums[i].
    Jump to index j where j < i is allowed only if nums[j] > nums[i].
    由于降序更有利于跳跃，应设计一定比例的元素进行降序排序
    Args:
        case_num: 随机生成的测试用例数量。
        max_n: 数组最大长度（方便调用者根据程序时间复杂度调整）
        （不影响时间复杂度的参数一般不纳入）
    Returns:
        List of _CASE: 包含 input (dict) 的测试用例列表。
    """
    UNIQUE_RATE = 0.9
    SMALL_RATE = 0.8
    MAX = int(10**9)
    
    cases = []
    
    # --- 规模参数生成 (Outside the main loop) ---
    # 采用负指数分布生成 case_num 个规模参数，并排序，确保 n 随 i 增大而增大
    scales = []
    lam = 3.0 / max_n  # 调整 lambda 以适应 max_n 的范围
    
    for _ in range(case_num):
        # 使用负指数分布生成随机数，确保小规模数据多，大规模数据少
        sample = expovariate(lam)
        # 将生成的浮点数限制在有效范围内并转为整数
        # 长度=1的只需生成一次
        n = max(2, min(max_n, int(sample)))
        scales.append(n)
    
    # 关键步骤：在外面生成并排序
    # 这样可以保证测试用例从小规模到大规模排列，避免大用例卡死
    scales.sort()
    
    # --- 随机用例生成 (Random Cases) ---
    for i, n in enumerate(scales):
        # 独特元素的个数
        distinct_num = n if random()<UNIQUE_RATE else randint(1,n)

        # 选择数组数值分布
        if random()<SMALL_RATE:
            nums = list(range(1,distinct_num+1)) # B1
        else: # B2
            nums = set()
            while len(nums)<distinct_num:
                nums.add(randint(1,MAX))
            nums = list(nums)

        # 生成随机数组
        if distinct_num < n: # 无重复
            shuffle(nums) # 打乱
        else: # 有重复
            nums = choices(nums,k=n) # 随机选择
        
        cases.append({
            "input": {"nums": nums},
            "cid": i
        })
    
    return cases
