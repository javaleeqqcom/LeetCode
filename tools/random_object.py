import random
import string
import re
import math
import sys
from typing import Any, List, Tuple, Union, Optional, Callable
from fractions import Fraction
from compacted_json import _alias

# 定义基础类型生成函数
def _none(*args, **kwargs) -> None: return None
def _int(*args, **kwargs) -> int: return random.randint(-100, 100)
def _float(*args, **kwargs) -> float: return random.uniform(-10.0, 10.0)
def _bool(*args, **kwargs) -> bool: return random.choice([True, False])

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
    def _generate_trap_string(self, *args, **kwargs) -> str:
        """生成精确匹配_alias_pattern的陷阱字符串（格式: @{uuid4的hex_len位十六进制}）"""
        hex_part = ''.join(random.choices('0123456789abcdef', k=self._hex_len))
        return self._alias_prefix + hex_part
    
    # 与CompactedJson默认alias_prefix一致
    def _generate_safe_string(self, *args, **kwargs) -> str:
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
    
    def leaf_filter(self) -> List[FuncWC]:
        """过滤叶子节点（cost 不为 None 的方法）"""
        return [fwc for fwc in zip(self.funcs, self.weights, self.cost) if fwc[2] is not None]
    
    def expectations(self) -> float:
        """计算期望花费"""
        total = 0
        for i in range(self.size):
            if self.cost[i] is not None:
                total += self.weights[i] * self.cost[i]
        return total / sum(self.weights)
    
    def __len__(self):
        return self.size
    
    def __call__(self, *args, **kwargs) -> Tuple[Any, Union[int, float]]:
        """返回（随机对象，实际花费）"""
        idx = random.choices(range(self.size), self.weights)[0]
        if self.cost[idx] is not None:
            return self.funcs[idx](*args, **kwargs), self.cost[idx]
        else:
            return self.funcs[idx](*args, **kwargs)

    def __add__(self, other: Union['_meta_random' , FuncWC]) -> '_meta_random':
        """ 智能合并生成器：
        1. 若 other 是 _meta_random -> 合并内部函数列表
        2. 若 other 是 (callable, weight, cost) 元组 -> 直接添加
        """
        new_list = list(zip(self.funcs, self.weights, self.cost))
        # 情况1: other 是 _meta_random
        if isinstance(other, _meta_random):
            new_list.extend(zip(other.funcs, other.weights, other.cost))
        # 情况2: other 是 (func, weight, cost) 元组
        elif isinstance(other, tuple) and len(other) == 3 and callable(other[0]):
            new_list.append(other)
        else:
            raise TypeError(
                f"不支持的加法操作数类型: {type(other)}。\n"
                "请确保 other 是:\n"
                " • _meta_random 实例\n"
                " • (callable, weight, cost) 元组"
            )
        return _meta_random(new_list)

class _size_random:
    """根据非负分布函数生成随机整数，并提供理论期望与方差（连续分布）"""
    # 用户友好别名映射 -> 标准前缀（用于拼接 *variate）
    _ALIAS_MAP = {
        'exp': 'expo', 'exponential': 'expo', 'gamma': 'gamma', 'weibull': 'weibull',
        'lognorm': 'lognorm', 'lognormal': 'lognorm', 'pareto': 'pareto', 'beta': 'beta',
        'uniform': 'uniform', 'uni': 'uniform'
    }
    # 支持的非负分布标准前缀
    _SUPPORTED = {'expo', 'gamma', 'weibull', 'lognorm', 'pareto', 'beta', 'uniform'}

    def __init__(self, distribution: str, **kwargs):
        # 1. 标准化分布名称
        norm_dist = self._ALIAS_MAP.get(distribution.lower(), distribution.lower())
        if norm_dist not in self._SUPPORTED:
            raise ValueError(
                f"不支持的分布 '{distribution}'。支持的非负分布: "
                "exp/exponential, gamma, weibull, lognorm/lognormal, pareto, beta, uniform"
            )
        self._dist_key = norm_dist

        # 2. 按分布类型初始化：参数校验 + 设置随机方法 + 计算理论矩
        if norm_dist == 'uniform':
            # ===== 均匀分布：严格校验整数参数与非负区间 =====
            a = kwargs.get('a')
            b = kwargs.get('b')
            if not (isinstance(a, int) and isinstance(b, int)):
                raise ValueError(f"均匀分布参数 a 和 b 必须为整数类型，当前: a={type(a)}, b={type(b)}")
            if not (0 <= a <= b):
                raise ValueError(f"均匀分布参数需满足 0 <= a <= b，当前: a={a}, b={b}")
            self._random_method = random.randint  # 模块级函数，pickle 安全
            self.kwargs = kwargs.copy()
            self._theoretical_mean = (a + b) / 2.0
            self._theoretical_second_moment = (a * a + a * b + b * b) / 3.0

        elif norm_dist == 'expo':
            lambd = kwargs.get('lambd')
            if not (isinstance(lambd, (int, float)) and lambd > 0):
                raise ValueError(f"指数分布参数 lambd 必须 > 0，当前: lambd={lambd}")
            self._random_method = random.expovariate
            self.kwargs = kwargs.copy()
            self._theoretical_mean = 1.0 / lambd
            self._theoretical_second_moment = 2.0 / (lambd ** 2)

        elif norm_dist == 'gamma':
            alpha = kwargs.get('alpha')
            beta = kwargs.get('beta')
            if not (isinstance(alpha, (int, float)) and isinstance(beta, (int, float)) and alpha > 0 and beta > 0):
                raise ValueError(f"Gamma 分布参数需满足 alpha > 0, beta > 0，当前: alpha={alpha}, beta={beta}")
            self._random_method = random.gammavariate
            self.kwargs = kwargs.copy()
            self._theoretical_mean = alpha * beta
            self._theoretical_second_moment = alpha * (alpha + 1) * (beta ** 2)

        elif norm_dist == 'weibull':
            alpha = kwargs.get('alpha')
            beta = kwargs.get('beta')
            if not (isinstance(alpha, (int, float)) and isinstance(beta, (int, float)) and alpha > 0 and beta > 0):
                raise ValueError(f"Weibull 分布参数需满足 alpha > 0, beta > 0，当前: alpha={alpha}, beta={beta}")
            self._random_method = random.weibullvariate
            self.kwargs = kwargs.copy()
            self._theoretical_mean = alpha * math.gamma(1.0 + 1.0 / beta)
            self._theoretical_second_moment = (alpha ** 2) * math.gamma(1.0 + 2.0 / beta)

        elif norm_dist == 'lognorm':
            mu = kwargs.get('mu')
            sigma = kwargs.get('sigma')
            if mu is None or not (isinstance(sigma, (int, float)) and sigma > 0):
                raise ValueError(f"对数正态分布参数需满足 mu 任意, sigma > 0，当前: mu={mu}, sigma={sigma}")
            self._random_method = random.lognormvariate
            self.kwargs = kwargs.copy()
            self._theoretical_mean = math.exp(mu + sigma ** 2 / 2.0)
            self._theoretical_second_moment = math.exp(2.0 * mu + 2.0 * (sigma ** 2))

        elif norm_dist == 'pareto':
            alpha = kwargs.get('alpha')
            if not (isinstance(alpha, (int, float)) and alpha > 2):
                raise ValueError(f"Pareto 分布参数 alpha 必须 > 2（确保期望与方差存在），当前: alpha={alpha}")
            self._random_method = random.paretovariate
            self.kwargs = kwargs.copy()
            self._theoretical_mean = alpha / (alpha - 1.0)
            self._theoretical_second_moment = alpha / (alpha - 2.0)

        elif norm_dist == 'beta':
            alpha = kwargs.get('alpha')
            beta = kwargs.get('beta')
            if not (isinstance(alpha, (int, float)) and isinstance(beta, (int, float)) and alpha > 0 and beta > 0):
                raise ValueError(f"Beta 分布参数需满足 alpha > 0, beta > 0，当前: alpha={alpha}, beta={beta}")
            self._random_method = random.betavariate
            self.kwargs = kwargs.copy()
            denom = alpha + beta
            self._theoretical_mean = alpha / denom
            self._theoretical_second_moment = (alpha * (alpha + 1.0)) / (denom * (denom + 1.0))

        # 3. 验证随机方法存在（防御性编程）
        if not callable(self._random_method):
            raise RuntimeError(f"无法获取分布 '{norm_dist}' 对应的随机生成函数")

    def __call__(self, *args: Any, **kwds: Any) -> int:
        """生成非负随机整数（高频调用，无分支逻辑）"""
        val = self._random_method(**self.kwargs)
        return int(round(val)) if val > 0.0 else 0

    def mean(self) -> float:
        """返回原始连续分布的理论期望（非取整后）"""
        return self._theoretical_mean

    def std(self) -> float:
        """返回原始连续分布的理论方差（非取整后）"""
        return self._theoretical_second_moment - self._theoretical_mean ** 2

# 定义 _LLcost1 函数
def _LLcost1(depth: int, size: int) -> int:
    """仅叶子列表（层级为1）花费1点"""
    return 1 if depth == 1 else 0

class _list_random:
    def __init__(self, size_random: _size_random, list_cost_fun: Union[int, float, Callable]) -> None:
        self.sizeRandom = size_random
        self.sub_random = self._bind_error
        self.leaf_method_index = []
        self.list_cost = list_cost_fun
        
        # 预估期望花费数组
        self._cost_estimate = [0.0] * (sys.getrecursionlimit()-1) # 系统递归池最大深度
        self._cost_estimate[0] = self.leaf_random.expectations() if hasattr(self, 'leaf_random') else 0
        
        # 预估非叶子节点的期望花费
        for d in range(1, len(self._cost_estimate)):
            # 预估的列表花费（假定 list_cost 是关于 size 的线性函数）
            list_cost = self.list_cost(d, self.sizeRandom.mean()) if callable(self.list_cost) else self.list_cost
            
            # 非叶子节点的期望花费
            self._cost_estimate[d] = list_cost + self._cost_estimate[d-1] * self.sizeRandom.mean()
    
    def _bind_error(self):
        raise ValueError("请先执行 bind_method，方可使用 __call__")
    
    def bind_method(self, sub_random: _meta_random) -> None:
        self.sub_random = sub_random
        # 不再通过 leaf_random 来额外区分叶子节点的调用函数，而是通过 cost 为非 None 这一叶子对象特征作为依据。
        self.leaf_random = _meta_random(list(sub_random.leaf_filter()))
        self.method_size = len(sub_random)
    
    def _get_safe_depth(self, depth: int, remain: int) -> int:
        """根据 remain 估算安全深度"""
        # 从高深度开始，找到最大的深度 d 使得 _cost_estimate[d] <= remain
        for d in range(min(depth, len(self._cost_estimate)-1), -1, -1):
            if self._cost_estimate[d] <= remain:
                return d
        return 0

    def __call__(self, depth: int, remain: int) -> Tuple[Any, float]:
        """生成列表 Args: depth: 当前深度 remain: 剩余花费 """
        # 1. 计算安全深度
        safe_depth = self._get_safe_depth(depth, remain)
        
        # 2. 生成列表大小
        size = self.sizeRandom()
        
        # 3. 计算列表花费
        if callable(self.list_cost):
            cost = self.list_cost(safe_depth, size)
        else:
            cost = self.list_cost
        
        # 4. 如果无法支付列表花费，返回叶子节点
        if safe_depth == 0 or cost > remain:
            return self.leaf_random(safe_depth, remain)
        
        # 5. 列表至少为1层
        res = [None] * size
        remain_after = remain - cost
        for i in range(size):
            # 递归调用，使用 safe_depth-1
            res[i], c = self.sub_random(depth=safe_depth-1, remain=remain_after)
            remain_after -= c
            if remain_after < 0:  # 放弃第 i 项，提前结束
                return res[:i], remain - (remain_after + c)
        
        return res, remain - cost

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
    size_random = _size_random('expo', lambd = 0.01)
    print( "E(size)={:.2f} , D(size)={:.2f}".format(size_random.mean(), size_random.std()) )
    
    # 创建递归列表随机生成器
    listRandom = _list_random(size_random, list_cost_fun=_LLcost1)
    
    # 将列表随机生成器与基础随机生成器结合，作为最终的随机对象生成器
    merge_random = leaf_base + (listRandom, 10, None)  # 需实现加法重载
    
    # 易错！必须绑定 _list_random 对象的 sub_random 方法
    listRandom.bind_method(merge_random)
    
    # 生成一个随机对象
    depth, remain = 1000, 1000
    print(f"depth:{depth},remain:{remain}")
    obj, cost = merge_random(depth=depth, remain=remain)
    print(f"生成的随机对象: {obj}")
    print(f"花费: {cost}")