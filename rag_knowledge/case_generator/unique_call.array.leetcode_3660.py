# @EXAMPLE_BEGIN: 3660.Jump Game IX
# @EXAMPLE_TAG: unique_call, array, leetcode

from typing import Dict, Any
import random as rd
import numpy as np

# @RAG_BEGIN: case_generator_function
# @RAG_EXPORT: no

# 要对生成规模排序，优先小样例，有利于分析较为简洁的错误
def case_generator(scale:int) -> Dict[str, Any]:
    """
    Args:
        scale: 测试用例规模，在本题中对应数组长度。
    Returns:
        _CASE: 包含 input (dict) 的测试用例列表。
    """

# @RAG_END

    # @RAG_BEGIN: scale2n
    # @RAG_EXPORT: depend

    MIN_N: int = 1 # 题目给定的最小规模
    MAX_N: int = 10**5 # 题目给定的最大规模
    
    n = np.clip(int(round(scale)),MIN_N,MAX_N)
    
    # @RAG_END

    # @RAG_BEGIN: distinct_strategy
    # @RAG_EXPORT: depend
    # @RAG_MODULE_SETTING: 设 n = len(nums)

    # 该测试用例要求 nums[j] != nums[i]，才可执行跳跃动作，因此测试样例设计分为两种情况：
    # A1. 数组无重复元素，用于高效检验程序的计算能力
    # A2. 数组有重复元素，用于检验程序的鲁棒性
    UNIQUE_RATE = 0.9
    distinct = n if rd.random()<UNIQUE_RATE else rd.randint(1,n) # choose A1,A2

    # @RAG_BEGIN: nums_range_strategy
    # @RAG_EXPORT: yes
    # @RAG_MODULE_SETTING: 设 distinct 为预期 len(set(nums))

    # 又因为数组元素之间的差值不影响结果，但题目要求 1 <= nums[i] <= 10^9，因此数值大小也分为两种情况：
    # B1. 长度为 n 的数组，数值仅取 [1,n]，方便DEBUG错误时阅读小数字体验较好
    # B2. 数值取 [1,MAX]，用于限制作答者用暴力桶排序等方法通过测试用例
    SMALL_RATE = 0.8
    MAX = int(10**9)
    if rd.random()<SMALL_RATE:
        nums = np.arange(1,distinct+1)
    else:
        nums = np.random.randint(1,MAX+1,size=distinct)

    # @RAG_END

    # @RAG_BEGIN: nums_shuffle_strategy
    # @RAG_DEP: nums_range_strategy
    # @RAG_EXPORT: yes

    # 最后应当根据 distinct 策略进行打乱或随机选择
    # 生成随机数组
    if distinct == n: # 无重复
        np.random.shuffle(nums) # 打乱
    else: # 有重复
        nums = np.random.choice(nums,size=n,replace=True) # 随机选择 n 次，允许重复

    # @RAG_END

    # @RAG_BEGIN: sorted_partial
    # @RAG_EXPORT: yes
    # @RAG_MODULE_SETTING: 设 nums 为随机乱序数组
    # @RAG_MODULE_SETTING: 设 n = len(nums)

    # 因为题目的跳跃规则：
    #     Jump to index j where j > i is allowed only if nums[j] < nums[i].
    #     Jump to index j where j < i is allowed only if nums[j] > nums[i].
    #     降序更有利于跳跃，应设计降序排序和打乱各占一部分
    sorted_rate = np.random.random() # 可考虑改为其他分布如 Beta 
    sorted_mask = np.random.random(size=n) <= sorted_rate # 随机选择一部分进行排序
    nums[sorted_mask] = np.sort(nums[sorted_mask])[::-1] # 对选择的部分进行降序排序
    
    # @RAG_END

    # @RAG_BEGIN: return_nums
    # @RAG_EXPORT: no

    return {
        "input": (
            nums.tolist(),  # 若 nums 为 numpy 数组，需要转换为 list 类型，确保所有参数可 JSON 序列化
            ), # 优先用元组参数列表，除非参数容易混淆。
        # 本题无法根据构造过程简单求出 expected，因此不提供
    }

    # @RAG_END

# @EXAMPLE_END