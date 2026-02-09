import random
import string
import re
from typing import Any, List, Tuple, Union, Optional, Callable
from fractions import Fraction
from compacted_json import _alias

# 定义基础类型生成函数
def _none(*args, **kwargs) -> None:
    return None

def _int(*args, **kwargs) -> int:
    return random.randint(-100, 100)

def _float(*args, **kwargs) -> float:
    return random.uniform(-10.0, 10.0)

def _bool(*args, **kwargs) -> bool:
    return random.choice([True, False])

# 判断是否为叶子序列
def _is_leaf_sequence(obj: Any) -> bool:
    """判断是否为叶子序列（list/tuple + 元素全为基础类型）"""
    if not isinstance(obj, (list, tuple)):
        return False
    return all(isinstance(x, (int, float, str, bool, type(None))) for x in obj)

class _alias_str_generator(_alias):
    def __init__(self, hex_len: int = 32, alias_prefix: str = "@" ):
        super().__init__(hex_len, alias_prefix)
        self.CHARSET = tuple(set('"' + "'" + "{}[]" + self._alias_prefix + string.digits + string.ascii_letters))

    # 易错点！ 必须采用兼容的输入参数 *args ,**kwargs，否则无法正确调用
    def _generate_trap_string(self, *args ,**kwargs) -> str:
        """生成精确匹配_alias_pattern的陷阱字符串（格式: @{uuid4的hex_len位十六进制}）"""
        hex_part = ''.join(random.choices('0123456789abcdef', k=self._hex_len))
        return self._alias_prefix + hex_part  # 与CompactedJson默认alias_prefix一致

    def _generate_safe_string(self, *args ,**kwargs) -> str:
        """生成不匹配 _alias_pattern 的随机字符串"""
        length = random.randint(1, self._hex_len+3)
        while True:
            s = ''.join(random.choices(self.CHARSET, k=length))
            if re.match(self._alias_pattern, s) is None:
                return s

# 定义元组类型
FuncWC = Tuple[Callable, Union[int, float], Optional[Union[int, float]]]

# 定义 _meta_random 类
class _meta_random:
    """根据 func_weight_cost 元组中的：（可调用方法，权重，花费）依据各项的权重随机抽取一个可调用方法，返回其结果和花费。
    若cost为 None 则该方法为可变花费，要求方法返回一个元组（结果，花费）。
    """
    def __init__(self, fun_w_c_list: List[FuncWC]):
        self.size = len(fun_w_c_list)
        self.funcs = tuple(fwc[0] for fwc in fun_w_c_list)
        self.weights = tuple(max(0, fwc[1]) for fwc in fun_w_c_list)
        self.cost = tuple(fwc[2] for fwc in fun_w_c_list)

    def leaf_filter(self) -> FuncWC ?:
        for fwc in zip(self.funcs, self.weights, self.cost):
            if fwc[2] is not None: # 通过 cost 为非 None 判断作为叶子对象的依据
                yield fwc

    def __len__(self):
        return self.size

    def __call__(self, *args, **kwargs) -> Tuple[Any, Union[int, float]]:
        """返回（随机对象，实际花费）"""
        idx = random.choices(range(self.size), self.weights)[0]
        if self.cost[idx] is not None:
            return self.funcs[idx](*args, **kwargs), self.cost[idx]
        else:
            return self.funcs[idx](*args, **kwargs)
      
# 定义 _meta_random 类对象都加法(self, A,B):
#     return _meta_random(A的fun_w_c + B的fun_w_c)

import random
import math
from typing import Any

class _size_random:
    """根据非负分布函数生成随机整数，并提供理论期望与方差（连续分布）"""
    
    # 用户友好别名映射 -> 标准前缀（用于拼接 *variate）
    _ALIAS_MAP = {
        'exp': 'expo', 'exponential': 'expo',
        'gamma': 'gamma',
        'weibull': 'weibull',
        'lognorm': 'lognorm', 'lognormal': 'lognorm',
        'pareto': 'pareto',
        'beta': 'beta'
    }
    
    # 支持的非负分布标准前缀
    _SUPPORTED = {'expo', 'gamma', 'weibull', 'lognorm', 'pareto', 'beta'}
    
    # 理论矩计算与参数校验（标准前缀 -> (参数校验, 期望, 二阶矩)）
    _MOMENT_SPECS = {
        'expo': (
            lambda kw: kw.get('lambd', 0) > 0,
            lambda kw: 1.0 / kw['lambd'],
            lambda kw: 2.0 / (kw['lambd'] ** 2)
        ),
        'gamma': (
            lambda kw: kw.get('alpha', 0) > 0 and kw.get('beta', 0) > 0,
            lambda kw: kw['alpha'] * kw['beta'],
            lambda kw: kw['alpha'] * (kw['alpha'] + 1) * (kw['beta'] ** 2)
        ),
        'weibull': (
            lambda kw: kw.get('alpha', 0) > 0 and kw.get('beta', 0) > 0,
            lambda kw: kw['alpha'] * math.gamma(1 + 1 / kw['beta']),
            lambda kw: (kw['alpha'] ** 2) * math.gamma(1 + 2 / kw['beta'])
        ),
        'lognorm': (
            lambda kw: 'mu' in kw and kw.get('sigma', 0) > 0,
            lambda kw: math.exp(kw['mu'] + kw['sigma'] ** 2 / 2),
            lambda kw: math.exp(2 * kw['mu'] + 2 * (kw['sigma'] ** 2))
        ),
        'pareto': (
            # 要求 alpha > 2 以保证期望和二阶矩均存在
            lambda kw: kw.get('alpha', 0) > 2,
            lambda kw: kw['alpha'] / (kw['alpha'] - 1),
            lambda kw: kw['alpha'] / (kw['alpha'] - 2)
        ),
        'beta': (
            lambda kw: kw.get('alpha', 0) > 0 and kw.get('beta', 0) > 0,
            lambda kw: kw['alpha'] / (kw['alpha'] + kw['beta']),
            lambda kw: (kw['alpha'] * (kw['alpha'] + 1)) / 
                       ((kw['alpha'] + kw['beta']) * (kw['alpha'] + kw['beta'] + 1))
        )
    }

    def __init__(self, distribution: str, **kwargs):
        # 1. 标准化分布名称
        norm_dist = self._ALIAS_MAP.get(distribution.lower(), distribution.lower())
        if norm_dist not in self._SUPPORTED:
            raise ValueError(
                f"不支持的分布 '{distribution}'。支持的非负分布: "
                "exp/exponential, gamma, weibull, lognorm/lognormal, pareto, beta"
            )
        self._dist_key = norm_dist  # 内部使用标准前缀
        
        # 2. 获取 random 分布函数
        func_name = f"{norm_dist}variate"
        if not hasattr(random, func_name):
            raise RuntimeError(f"random 模块缺少函数: {func_name}")
        self._random_method = getattr(random, func_name)
        self.kwargs = kwargs.copy()
        
        # 3. 参数校验 + 理论矩计算
        validator, mean_func, second_func = self._MOMENT_SPECS[norm_dist]
        if not validator(kwargs):
            req = {
                'expo': "lambd > 0",
                'gamma': "alpha > 0, beta > 0",
                'weibull': "alpha > 0, beta > 0",
                'lognorm': "mu (任意), sigma > 0",
                'pareto': "alpha > 2 (确保期望和方差存在)",
                'beta': "alpha > 0, beta > 0"
            }[norm_dist]
            raise ValueError(f"分布 '{distribution}' 参数无效。要求: {req}, 当前: {kwargs}")
        
        try:
            self._theoretical_mean = mean_func(kwargs)
            self._theoretical_second_moment = second_func(kwargs)
        except Exception as e:
            raise ValueError(f"计算分布 '{distribution}' 理论矩失败: {e}") from e

    def __call__(self, *args: Any, **kwds: Any) -> int:
        """
        生成随机数，确保结果 >= 0:
        1. 调用分布函数生成浮点值
        2. 防御性修正：若因浮点误差出现负值，强制置0
        3. 四舍五入取整
        """
        val = self._random_method(**self.kwargs)
        return int(round(val if val >= 0 else 0.0))  # 理论非负分布极少触发修正，但保障安全

    def expectations(self) -> float:
        """返回原始连续分布的理论期望（非取整后）"""
        return self._theoretical_mean

    def variance(self) -> float:
        """返回原始连续分布的理论方差（非取整后）"""
        return self._theoretical_second_moment - self._theoretical_mean ** 2

# 定义 _LLcost1 函数
def _LLcost1(depth: int, size: int) -> int:
    """仅叶子列表（层级为1）花费1点"""
    return 1 if depth == 1 else 0

class _list_random:
    def __init__(self,size_random: _size_random, list_cost_fun: Union[int, float, Callable]) -> None:
        self.sizeRandom = size_random
        self.sub_random = self._bind_error # 在构造对象后，再进行绑定
        self.leaf_method_index = []
        self.list_cost = list_cost_fun

    def _bind_error(self):
        raise ValueError(请先执行 bind_method，方可使用 __call__)

    def bind_method(self, sub_random: _meta_random) -> None:
        self.sub_random = sub_random
        # 不再通过 leaf_random 来额外区分叶子节点的调用函数，而是通过 cost 为非 None 这一叶子对象特征作为依据。
        self.leaf_random = _meta_random(list(sub_random.leaf_filter()))
        self.method_size = len(sub_random)

    def __call__(self, depth: int, remain: int) -> Tuple[Any, float]:
        """生成列表
        
        Args:
            depth: 当前深度
            remain: 剩余花费
        """
        # 生成列表大小
        size = self.sizeRandom()
        
        # 计算列表花费
        if callable(self.list_cost):
            remain_after = remain - self.list_cost(depth, size)
        else:
            remain_after = remain - self.list_cost
        
        # 如果无法支付列表花费，返回叶子节点
        if depth == 0 or remain_after < 0:
            return self.leaf_random(depth, remain)
        
        # 列表至少为1层
        res = [None]*size
        for i in range(size):
            # 递归调用
            res[i],c = self.sub_random(depth = depth-1 ,remain = remain_after)
            remain_after -= c
            if remain_after < 0: # 放弃第 i 项，提前结束
                return res[:i] , remain - (remain_after + c)
        
        return res, remain - remain_after

# 用于测试的示例
if __name__ == "__main__":
    # 创建别名生成器
    alias = _alias_str_generator(8)
    # 创建基础随机生成器
    leaf_base = _meta_random([
        (_int, 2, 0),
        (_float, 2, 0),
        (_bool, 1, 0),
        (_none, 1, 0),
        (alias._generate_safe_string, 2, 0),
        (alias._generate_trap_string, 2, 1),
    ])
    
    # 创建列表大小随机生成器（均匀分布，0-100）
    size_random = _size_random('uniform', min=0, max=100)
    
    # 创建递归列表随机生成器
    listRandom = _list_random(size_random, _LLcost1)

    # 将列表随机生成器与基础随机生成器结合，作为最终的随机对象生成器
    merge_random = leaf_base + listRandom # 需实现加法重载

    # 易错！必须绑定 _list_random 对象的 sub_random 方法
    listRandom.bind_method(merge_random)
    
    # 生成一个随机对象
    obj, cost = merge_random(depth=100, remain=1000)
    print(f"生成的随机对象: {obj}")
    print(f"花费: {cost}")