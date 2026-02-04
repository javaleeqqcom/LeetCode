from tools.solution_runner import SolutionRunner
from typing import List, Union, Tuple, Dict, Any

# 初始化暴力解法运行器
brute = SolutionRunner("P3640_bt0.py")

# 生成测试用例指引文件
# ask_file = None  # 设置为None将使用与brute.py同名的txt文件
# brute.get_ask_for_cases(ask_file) 
# exit(0)

import numpy as np
from typing import List, Union, Optional, Tuple

def cases_generation(
    num_test_cases: int = 12, 
    max_array_length: int = 25, 
    seed: Optional[int] = None
) -> List[Union[Tuple, Dict]]:
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
    
    # === 精心设计的手动用例（按测试优先级排序）===
    # 每个用例均经人工验证Trionic条件及预期行为
    manual_cases = [
        # (描述, nums)
        ("最小有效Trionic: [1,2,1,2] 差分[1,-1,1]", [1, 2, 1, 2]),
        ("长度4无效: 严格递增", [1, 2, 3, 4]),
        ("超短数组: 长度1", [1]),
        ("超短数组: 长度3", [1, 2, 3]),
        ("含负数有效Trionic: [-1,0,-1,0] 差分[1,-1,1]", [-1, 0, -1, 0]),
        ("较长有效Trionic: 全数组满足", [10, 20, 15, 10, 15, 20]),
        ("多有效子数组: break逻辑不漏检最大和", [1, 3, 2, 3, 1, 2]),  # 子数组[1,3,2,3]和=9, [2,3,1,2]和=8
        ("全零数组: 无有效子数组", [0, 0, 0, 0]),
        ("严格递减: 无有效子数组", [5, 4, 3, 2, 1]),
        ("暴露break缺陷: 全数组有效但被提前break跳过", [2, 5, 3, 1, 4, 6]),  # [2,5,3,1]无效导致break，漏检全数组
        ("平台值测试: 含重复值但满足Trionic", [3, 5, 5, 3, 4, 6]),  # 差分[2,0,-2,1,2] → p=1(d[1]=0≤0), 但isTrionic要求严格符号变化，此例实际无效（用于测试边界处理）
        ("混合符号有效: [-5,0,-3,1,4] 差分[5,-3,4,3]", [-5, 0, -3, 1, 4])
    ]
    
    test_cases = []
    # 添加手动用例（按需截断）
    for desc, nums in manual_cases:
        if len(test_cases) >= num_test_cases:
            break
        test_cases.append((nums,))  # 单参数必须用元组格式 (nums,)
    
    # 补充随机用例至目标数量
    while len(test_cases) < num_test_cases:
        # 智能长度分布：30%短数组(<4), 70%有效长度范围
        if max_array_length < 4:
            length = np.random.randint(1, max_array_length + 1)
        else:
            length = np.random.randint(1, 4) if np.random.rand() < 0.3 else np.random.randint(4, max_array_length + 1)
        
        # 生成带符号整数（覆盖负数、零、正数场景）
        nums = np.random.randint(-100, 101, size=length).tolist()
        test_cases.append((nums,))
    
    return test_cases

# 保存测试用例，并自动运行暴力算法生成expected结果
# 方式1: 通过函数生成测试用例
brute.save_cases(cases_generation) #, num_test_cases=100, max_array_length=100)

# 方式2: 直接提供测试用例列表
# custom_cases = [
#     (1, 2),
#     (3, 0),
#     {'input': {'a': 5, 'b': -3}}
# ]
# brute.save_cases(custom_cases)

print("\n🎉 暴力测试用例生成完成！现在可以使用这些用例测试优化算法了。")
print("🔍 下一步: 创建一个新的SolutionRunner实例加载优化算法，然后使用runner.read_test_case()读取生成的JSON测试文件")