from tools.solution_runner import SolutionRunner, _CASE_TYPE
from typing import List, Union, Tuple, Dict, Any

# 初始化暴力解法运行器
brute = SolutionRunner("1545_V0_bt.py")

# 生成测试用例指引文件
# ask_file = None  # 设置为None将使用与brute.py同名的txt文件
# brute.get_ask_for_cases(ask_file) 
# exit(0)

import numpy as np
from typing import List, Union, Optional, Tuple

def cases_generation(
    num_test_cases: int = 12, 
    max_n: int = 20, 
    seed: Optional[int] = None
) -> List[Tuple]:
    """
    生成测试用例用于测试 Solution.maxSumTrionic 方法。
    
    设计原则：
    1. 优先包含精心设计的手动用例（覆盖边界、有效/无效Trionic结构、负数、全零等）
    2. 补充随机用例增强鲁棒性测试（含短数组、长数组、随机值）
    3. 严格遵循输入格式：单参数使用元组 (nums,)
    4. 显式处理随机种子保证可复现性
    
    Trionic条件关键点（用于设计验证）：
    - 子数组长度 ≥4
    - 差分序列需满足：[正...] → [负...] → [正...]（三段均非空）
    - isTrionic 内部含 break 逻辑，用例需覆盖其潜在影响
    
    参数:
        num_test_cases: 生成的测试用例总数
        max_array_length: 随机数组的最大长度（手动用例长度固定）
        seed: 随机种子（None 表示不固定）
    
    返回:
        List[Union[Tuple, Dict]]: 每个元素为 (nums,) 元组（单参数场景）
    """
    # 设置随机种子（仅影响后续随机生成部分）
    if seed is not None:
        np.random.seed(seed)
    
    test_cases = []
    # 补充随机用例至目标数量
    while len(test_cases) < num_test_cases:
        n = np.random.randint(1,max_n)
        k = np.random.randint(1,(2**n))

        test_cases.append((n,k))
    
    return test_cases

# 保存测试用例，并自动运行暴力算法生成expected结果

cases = cases_generation(num_test_cases= 100,max_n=20,seed=42)

# brute.save_test_cases(cases)
# output = brute.run(cases,only_log_wrong=True)

# 可以用 tuple_to_cases 将 tuple 格式的 test_cases 转换为 list of _CASE_TYPE
fotmat_cases = brute.tuple_to_cases(cases)
brute.save_test_cases(fotmat_cases)
output = brute.run(fotmat_cases,only_log_wrong=True)

expected_results = brute.get_expected_cases(output)
brute.save_test_cases(expected_results)

print("\n🎉 暴力测试用例生成完成！现在可以使用这些用例测试优化算法了。")
print("🔍 下一步: 创建一个新的SolutionRunner实例加载优化算法，然后使用runner.read_test_case()读取生成的JSON测试文件")

