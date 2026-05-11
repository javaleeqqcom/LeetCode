from typing import Any, Dict, Tuple, Callable ,Union,List ,Optional,Deque,TypedDict,NotRequired,Generic,TypeVar,Iterator
from .args_parser import _CASE
import numpy as np

def cases_generator_lognorm(cases_gen_func: Callable[[int],_CASE], cases_num:int = 1000 , EX: float = 10 ,EX2: Optional[float] = None ,EX2_rate:float = 10) -> List[_CASE]:
    """
    生成规模服从对数正态分布的测试用例集
    Args:
        cases_gen_func: 随机生成的测试用例函数，接受一个参数 scale 表示问题规模。函数内部可能对 scale 进行额外的范围限制，本调度器的期望计算不对此进行考虑。
        cases_num: 测试用例数量
        EX: 规模 scale 的一阶矩（假设解答程序复杂度为O(scale)的计算量期望）
        EX2: 规模 scale 的二阶矩，必须＞EX^2（假设解答程序复杂度为O(scale^2)的计算量期望，若改进算法复杂度低于O(scale^2)可以设置大一些）
        EX2_rate: 若 EX2 未提供，则根据 EX2=EX2_rate·EX^2 计算 EX2
    Returns:
        List of _CASE: 包含 input (dict) 的测试用例列表。
    """
    if EX2 is None:
        assert EX2_rate>1, "EX2_rate=EX^2/EX 必须＞1"
        EX2 = EX*EX*EX2_rate
    # 根据对数正态分布的性质，计算 mu,sigma 使得 E(sacle)=EX, E(sacle^2)=EX2
    if EX <= 0 or EX2 <= 0:
        raise ValueError("EX 和 EX2 必须为正数")
    ex_sq = EX * EX
    if EX2 <= ex_sq:
        raise ValueError("EX2 必须大于 EX^2，否则方差非正")
    sigma_sq = np.log(EX2 / ex_sq)
    sigma = np.sqrt(sigma_sq)
    mu = np.log(EX) - sigma_sq / 2.0

    # 2. 生成对数正态分布样本 (numpy 的 lognormal 参数为 mean=mu, sigma=sigma)
    scales_list = np.random.lognormal(mean=mu, sigma=sigma, size=cases_num)
    # 3. 排序（仅用于后续规模递增需求，对统计量无影响）
    scales_list.sort()
    # 调用函数
    cases = list(map(cases_gen_func,scales_list))
    # 增加 cid
    for i,case in enumerate(cases):
        case.update({'cid': i})
    return cases

需要限制小规模的重复数量，默认以 n! 为上限 n=round(scale)
def cases_generator_lognorm_(cases_gen_func: Callable[[int],_CASE], cases_num:int = 1000 , EX: float = 10 ,EX2: Optional[float] = None ,EX2_rate:float = 10) -> List[_CASE]:
    """
    生成规模服从对数正态分布的测试用例集
    Args:
        cases_gen_func: 随机生成的测试用例函数，接受一个参数 scale 表示问题规模。函数内部可能对 scale 进行额外的范围限制，本调度器的期望计算不对此进行考虑。
        cases_num: 测试用例数量
        EX: 规模 scale 的一阶矩（假设解答程序复杂度为O(scale)的计算量期望）
        EX2: 规模 scale 的二阶矩，必须＞EX^2（假设解答程序复杂度为O(scale^2)的计算量期望，若改进算法复杂度低于O(scale^2)可以设置大一些）
        EX2_rate: 若 EX2 未提供，则根据 EX2=EX2_rate·EX^2 计算 EX2
    Returns:
        List of _CASE: 包含 input (dict) 的测试用例列表。
    """
    if EX2 is None:
        assert EX2_rate>1, "EX2_rate=EX^2/EX 必须＞1"
        EX2 = EX*EX*EX2_rate
    # 根据对数正态分布的性质，计算 mu,sigma 使得 E(sacle)=EX, E(sacle^2)=EX2
    if EX <= 0 or EX2 <= 0:
        raise ValueError("EX 和 EX2 必须为正数")
    ex_sq = EX * EX
    if EX2 <= ex_sq:
        raise ValueError("EX2 必须大于 EX^2，否则方差非正")
    sigma_sq = np.log(EX2 / ex_sq)
    sigma = np.sqrt(sigma_sq)
    mu = np.log(EX) - sigma_sq / 2.0

    # 2. 生成对数正态分布样本 (numpy 的 lognormal 参数为 mean=mu, sigma=sigma)
    scales_list = np.random.lognormal(mean=mu, sigma=sigma, size=cases_num)
    # 3. 排序（仅用于后续规模递增需求，对统计量无影响）
    scales_list.sort()
    # 调用函数
    cases = list(map(cases_gen_func,scales_list))
    # 增加 cid
    for i,case in enumerate(cases):
        case.update({'cid': i})
    return cases