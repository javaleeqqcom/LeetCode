from typing import Any, Dict, Tuple, Callable ,Union,List ,Optional,Deque,TypedDict,NotRequired,Generic,TypeVar,Iterator
from .args_parser import _CASE
import numpy as np
import math

def build_test_cases(cases_gen_func: Callable[[Any],_CASE],size_list: Union[np.ndarray, List[int]]):
    # 调用函数
    cases = list(map(cases_gen_func,size_list))
    # 增加 cid
    for i,case in enumerate(cases):
        case.update({'cid': i})
    return cases

def sample_lognormal_scales(num:int = 1000 , mean_scale: float = 10 ,second_moment: Optional[float] = None ,variance_ratio:float = 10) -> np.ndarray:
    """
    Sample monotonically increasing computational scales from a log-normal distribution.

    The generated scales are intended to approximate the expected workload
    of test cases rather than raw input length.

    A log-normal distribution is used because:
    - small test cases appear frequently
    - medium cases dominate
    - very large cases appear occasionally

    This distribution is well-suited for stress testing algorithms with
    different asymptotic complexities.

    Args:
        num_cases:
            Number of scales to generate.

        mean_scale:
            Expected first moment E(scale).

        second_moment:
            Expected second moment E(scale^2).
            Must satisfy:
                second_moment > mean_scale^2

            Larger values produce heavier tails and more large cases.

        variance_ratio:
            Used when second_moment is not explicitly provided:
                second_moment = variance_ratio * mean_scale^2

    Returns:
        np.ndarray(dtype=float):
            Sorted floating-point scales.
    """
    if second_moment is None:
        assert variance_ratio>1, "variance_ratio=mean_scale^2/mean_scale 必须＞1"
        second_moment = mean_scale*mean_scale*variance_ratio
    # 根据对数正态分布的性质，计算 mu,sigma 使得 E(sacle)=mean_scale, E(sacle^2)=second_moment
    if mean_scale <= 0 or second_moment <= 0:
        raise ValueError("mean_scale 和 second_moment 必须为正数")
    ex_sq = mean_scale * mean_scale
    if second_moment <= ex_sq:
        raise ValueError("second_moment 必须大于 mean_scale^2，否则方差非正")
    sigma_sq = np.log(second_moment / ex_sq)
    sigma = np.sqrt(sigma_sq)
    mu = np.log(mean_scale) - sigma_sq / 2.0

    # 2. 生成对数正态分布样本 (numpy 的 lognormal 参数为 mean=mu, sigma=sigma)
    size_list = np.random.lognormal(mean=mu, sigma=sigma, size=num)
    # 3. 排序（仅用于后续规模递增需求，对统计量无影响）
    size_list.sort()
    return size_list

def _apply_round_fun(arr: np.ndarray, round_fun):

    try:
        result = round_fun(arr)
        result = np.asarray(result)

        if result.shape == arr.shape:
            return result

    except Exception:
        pass

    return np.fromiter(
        (round_fun(float(x)) for x in arr),
        dtype=float,
        count=arr.size
    )

def quantize_scales(scale_list: Union[np.ndarray,List],
               min_scale: int = 0,
               max_scale: int = 10**5,
               max_repeat_array:np.ndarray|None = None,
               max_repeat_fn = math.factorial,
               max_repeat_domain = 10,
               round_fun=np.round,
               ) -> np.ndarray:
    """
    Convert continuous computational scales into discrete integer scales.

    This function:
    1. rounds floating-point scales into integers
    2. applies optional repetition constraints
    3. preserves monotonic ordering

    The repetition constraint prevents excessive duplication of very small
    test cases, which commonly occur in skewed distributions.

    For each integer n:

        count(n) <= max_repeat_fn(n)

    within the configured constraint domain.

    Args:
        scale_list:
            Floating-point computational scales.

        min_scale:
            Minimum allowed integer scale.

        max_scale:
            Maximum allowed integer scale.

        max_repeat_array:
            Optional explicit repetition limits indexed by scale value.

        max_repeat_fn:
            Function defining repetition limits for small scales.

        max_repeat_domain:
            Repetition constraints are applied only for:
                0 <= n < max_repeat_domain

        round_fun:
            Integer quantization function.

            Used to transform continuous scales into discrete values.

            This can be used to enforce special constraints such as:
            - odd numbers only
            - powers of two
            - aligned block sizes
            - bucketed scales

            Both scalar functions and NumPy-style vectorized functions are supported.

    Returns:
        np.ndarray(dtype=int64):
            Sorted integer scales.
    """
    # 1. 变换为整数并裁切
    nums = _apply_round_fun(np.asarray(scale_list),round_fun).astype(int).clip(min_scale, max_scale)

    # 2. 构建限制数组
    if max_repeat_array is None:
        max_repeat_array = np.array([max_repeat_fn(i) for i in range(max_repeat_domain)], dtype=int)

    # 3. 统计每个整数的出现次数
    values, counts = np.unique(nums, return_counts=True)

    # 4. 计算每个值允许的最大数量 (Vectorized)
    # 找出哪些值在 restriction_array 的定义域内
    mask = values < len(max_repeat_array)
    # 对于在定义域内的值，取 min(实际数量, 限制数量)
    counts[mask] = np.minimum(counts[mask], max_repeat_array[values[mask]])
    
    # 5. 生成结果
    # 这里我们不需要重新排序，因为 np.unique 返回的 values 是有序的
    # 使用 np.repeat 将值按允许的次数重复
    return np.repeat(values, counts)

def quantize_size_2D(
    size_list: Union[np.ndarray,List],
    bound=((1, -1), (1, -1)),
    beta=(5, 5),
    round_fun=np.round,
) -> np.ndarray:
    """
    Project one-dimensional computational scales into two-dimensional shapes.

    For each scale S, generate:

        n1 * n2 ≈ S

    The aspect ratio is controlled using a Beta distribution.

    This is useful for generating:
    - matrices
    - grids
    - bipartite structures
    - 2D dynamic programming inputs

    Args:
        scale_list:
            One-dimensional computational scales.

        bound:
            Bounds for:
                ((n1_min, n1_max),
                (n2_min, n2_max))

            Use -1 for unbounded maximum.

        beta:
            Beta distribution parameters controlling aspect ratios.

            Examples:
                (5,5): near-square shapes
                (1,1): highly variable ratios
                (1,5): thin rectangular shapes

        round_fun:
            Integer quantization function.

            Used to transform continuous scales into discrete values.

            This can be used to enforce special constraints such as:
            - odd numbers only
            - powers of two
            - aligned block sizes
            - bucketed scales

            Both scalar functions and NumPy-style vectorized functions are supported.

    Returns:
        ndarray(shape=(N,2)):
            Integer shape pairs.
    """

    size_list = np.asarray(size_list, dtype=float)

    if np.any(size_list <= 0):
        raise ValueError("size 必须 > 0")

    # -------------------------
    # 1. Beta ratio
    # -------------------------

    r = np.random.beta(*beta, size=len(size_list))

    # 避免除零
    eps = 1e-12
    r = np.clip(r, eps, 1 - eps)

    # k = n1/n2
    k = r / (1.0 - r)

    # -------------------------
    # 2. complexity projection
    # -------------------------

    n1 = np.sqrt(size_list * k)
    n2 = np.sqrt(size_list / k)

    # -------------------------
    # 3. integer quantization
    # -------------------------

    n1 = _apply_round_fun(np.asarray(n1),round_fun).astype(int)
    n2 = _apply_round_fun(np.asarray(n2),round_fun).astype(int)

    # -------------------------
    # 4. apply bounds
    # -------------------------

    (n1_min, n1_max), (n2_min, n2_max) = bound

    n1 = np.maximum(n1, n1_min)
    n2 = np.maximum(n2, n2_min)

    if n1_max != -1:
        n1 = np.minimum(n1, n1_max)

    if n2_max != -1:
        n2 = np.minimum(n2, n2_max)

    return np.stack([n1, n2], axis=1)
