from typing import Dict, Any, List
import numpy as np

# scale 作为指数是严重错误的！致使输入复杂度估计失效
def case_generator(scale: int) -> Dict[str, Any]:
    """
    根据 scale 生成不同类型的测试用例，覆盖：
    - 边界情况（极小规模、全部相同、无配对）
    - 随机情况（小、中、大规模）
    - 极端结构（大范围更新、高频率更新）
    - 退化结构（单元素数组、全等值）
    - 卡复杂度结构（频繁全区间更新 + 查询交替，迫使 O(Q * N log N) 行为）
    """
    rng = np.random.RandomState(42)

    # ---- 大规模 / 特殊结构生成 ----
    MAX_VAL = 100_000
    MAX_TOT = 1_000_000_000
    MAX_N2 = 50_000
    MAX_Q = 50_000

    # 平滑确定 nums2 长度与查询数，服从 scale 的
    def smooth_len(max_len: int, base_exp: float, jitter_ratio: float = 0.2) -> int:
        exp_val = 10 ** (scale / base_exp)
        raw = int(exp_val)
        raw = max(1, min(max_len, raw))
        # 增加少量随机扰动
        delta = max(1, int(raw * jitter_ratio))
        return max(1, min(max_len, raw + rng.randint(-delta, delta + 1)))

    n1 = rng.randint(1, 6)  # 1..5
    n2 = smooth_len(MAX_N2, 6.0)
    q_len = smooth_len(MAX_Q, 5.8)

    # nums1 长度小，直接随机
    nums1 = rng.randint(1, MAX_VAL + 1, size=n1).tolist()

    # nums2 随机初始值
    nums2 = rng.randint(1, MAX_VAL + 1, size=n2).tolist()

    # 查询生成
    queries: List[List[int]] = []
    # 更新操作占比
    p_type1 = 0.5

    # 一般随机生成 queries
    for _ in range(q_len):
        if rng.random() < p_type1:
            x = rng.randint(0, n2)
            y = rng.randint(x, n2)
            # 高 scale 时倾向全区间更新，加剧复杂度
            if scale >= 18 and rng.random() < 0.7:
                x, y = 0, n2 - 1
            val = rng.randint(1, MAX_VAL + 1)
            queries.append([1, int(x), int(y), int(val)])
        else:
            tot = rng.randint(1, MAX_TOT + 1)
            queries.append([2, int(tot)])

    return {"input": (nums1, nums2, queries)}