import random
import string
import re
import math
import sys
from typing import Any, List, Tuple, Union, Optional, Callable
from fractions import Fraction
from compacted_json import _alias  # 确保导入正确的 _alias 类

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
    def __init__(self, hex_len: int = 32, alias_prefix: str = "@"):
        super().__init__(hex_len, alias_prefix)
        self.CHARSET = tuple(set('"' + "'" + "{}[]" + self._alias_prefix + string.digits + string.ascii_letters))
    
    def _generate_trap_string(self, *args, **kwargs) -> str:
        """生成精确匹配_alias_pattern的陷阱字符串（格式: @{uuid4的hex_len位十六进制}）"""
        hex_part = ''.join(random.choices('0123456789abcdef', k=self._hex_len))
        return self._alias_prefix + hex_part
    
    def _generate_safe_string(self, *args, **kwargs) -> str:
        """生成不匹配 _alias_pattern 的随机字符串"""
        length = random.randint(1, self._hex_len+3)
        while True:
            s = ''.join(random.choices(self.CHARSET, k=length))
            if re.match(self._alias_pattern, s) is None:
                return s

# 类型别名
_FuncWC = TypeVar('_FuncWC', bound='_func_weight_cost')
_META = TypeVar('_META', bound='_meta_random')
_META_LIKE = Union[_META, _FuncWC, List[_FuncWC]]

# 以下类定义保持不变，只添加了必要的导入

from typing import List, Tuple, Any, Union, Callable, TypeVar, overload
import random

# 以下类定义保持不变
class _func_weight_cost:
    def __init__(self, func: Callable, weight: Union[float, int], cost0: Union[float, int, Callable], cost1: Union[float, int, Callable] = 0):
        self.func = func
        assert weight >= 0, "权重必须非负"
        self.weight = weight
        self.cost0 = cost0
        self.cost1 = cost1
    
    def is_fixed(self) -> bool:
        """是否为固定 cost"""
        return isinstance(self.cost0, (float, int)) and (self.cost1 == 0)
    
    def __lt__(self, other: '_func_weight_cost') -> bool:
        # 两者都是固定或都是非固定
        if self.is_fixed() and other.is_fixed() and self.cost0 != other.cost0:
            # 固定：先按 cost 升序，再按 weight 降序
            return self.cost0 < other.cost0
        else:
            # cost 相同，按 weight 降序
            return self.weight > other.weight

class _meta_random:
    """根据 func_weight_cost 元组中的：（可调用方法，权重，花费）依据各项的权重随机抽取一个可调用方法，返回其结果和花费。
    若 cost 为 Tuple[Callable,Callable] 则为可变花费，通常用于非叶子节点随机对象，要求`可调用方法`必须返回一个元组（结果，花费）。
    """
    _max_times = 100  # 最大尝试次数，防止无限循环
    _max_depth = 1000 # 应当替换为 sys 获取的最大递归深度
    
    def __init__(self, source: List[_func_weight_cost]):
        self.data = sorted(source)  # 排序确保固定花费优先，权重高的靠前
        self.weights = tuple(obj.weight for obj in self.data)
        self.total_weight = sum(self.weights)
        
        # 固定花费项的索引范围
        self.fixed_weights = tuple(obj.weight for obj in self.data if obj.is_fixed())
        self.fixed_num = len(self.fixed_weights)
        
        # 初始化DP数组（深度0的期望花费）
        self._dp_expectations = [self._calculate_fixed_expectation()]
    
    def _calculate_fixed_expectation(self) -> float:
        """计算深度0（叶子节点）的期望花费"""
        return sum(obj.weight * obj.cost0 for obj in self.data[:self.fixed_num] if isinstance(obj.cost0, (float, int))) / self.total_weight
    
    def mean(self, **kwargs) -> float:
        """估计随机对象在不限制总消费（remain = inf）情况下深度为 depth 的期望消费（深度0为叶子节点）"""
        depth = kwargs.get('depth', -1)
        
        # 采用记忆化 DP
        if depth < len(self._dp_expectations):
            return self._dp_expectations[depth]
        else:
            assert depth > 0, "0==len(_dp_expectations)错误！需要重新初始化 _dp_expectations"
            for d in range(len(self._dp_expectations), depth + 1):
                res = self._dp_expectations[0]  # 首先是固定期望花费
                for obj in self.data[self.fixed_num:]:
                    cost0 = obj.cost0 if isinstance(obj.cost0, (float, int)) else obj.cost0(**kwargs)
                    cost1 = obj.cost1 if isinstance(obj.cost1, (float, int)) else obj.cost1(**kwargs)
                    res += obj.weight / self.total_weight * (cost0 + cost1 * self.mean(depth=d - 1))
                self._dp_expectations[d] = res
            return self._dp_expectations[depth]
    
    def _get_safe_depth(self, depth: int, remain: Union[int, float]) -> int:
        """根据 remain 估算安全深度"""
        # 从高深度开始，找到最大的深度 d 使得 _dp_expectations[d] <= remain
        for d in range(min(depth, len(self._dp_expectations) - 1), -1, -1):
            if self._dp_expectations[d] <= remain:
                return d
        return 0
    
    def __len__(self):
        return len(self.data)
    
    def __call__(self, *args, **kwargs) -> Tuple[Any, Union[int, float]]:
        depth = kwargs.get("depth", 0)
        remain = kwargs.get("remain", float('inf'))
        
        # 计算安全深度
        safe_depth = self._get_safe_depth(depth, remain)
        
        # 重置 depth 为安全深度（避免递归过深）
        kwargs["depth"] = safe_depth
        
        for t in range(self._max_times):
            if safe_depth == 0:
                # 只能使用固定花费的项（叶子节点）
                idx = random.choices(range(self.fixed_num), self.fixed_weights)[0]
                obj = self.data[idx].func(*args, **kwargs)
                cost = self.data[idx].cost0
                assert isinstance(cost, (int, float)), f"ERROR! self.data 未按要求将固定花费排在前面，可能是数据遭到篡改！"
            else:
                # 选择任意项（固定或可变）
                idx = random.choices(range(len(self)), self.weights)[0]
                if idx < self.fixed_num:
                    # 固定花费项
                    obj = self.data[idx].func(*args, **kwargs)
                    cost = self.data[idx].cost0
                    assert isinstance(cost, (int, float)), f"ERROR! self.data 未按要求将固定花费排在前面，可能是数据遭到篡改！"
                else:
                    # 可变花费项
                    obj, cost = self.data[idx].func(*args, **kwargs)
                    assert isinstance(cost, (int, float)), f"可变花费方法 {self.data[idx].func} 未返回 (结果, 花费) 元组"
                
                if cost <= remain:
                    return obj, cost
        
        Warning(f"投掷超过最大重试次数{self._max_times}")
        return None, float('inf')
    
    def __add__(self: _META, other: _META_LIKE) -> _META:
        """合并生成器（支持合并元组、列表或另一个_meta_random）"""
        # 转换其他类型为列表
        if isinstance(other, _func_weight_cost):
            other_list = [other]
        elif isinstance(other, _meta_random):
            other_list = other.data
        elif isinstance(other, list):
            other_list = other
        else:
            raise TypeError(
                f"不支持的类型: {type(other)}. "
                "必须是 _func_weight_cost, _meta_random, 或列表"
            )
        
        # 合并数据
        combined = self.data + other_list
        return self.__class__(combined)

class _pairs_random(_meta_random):
    def __init__(self, key_random: _META_LIKE ,val_random: _META_LIKE):
        assert key_random.fixed_num == len(key_random) , "key_random must be a fixed-cost meta_random."
        super().__init__(...)
    
    def 

class _size_random:
    """根据非负分布函数生成随机整数，并提供理论期望与方差（连续分布）"""
    # 用户友好别名映射 -> 标准前缀（用于拼接 *variate）
    _ALIAS_MAP = {
        'exp': 'expo', 'exponential': 'expo',
        'gamma': 'gamma', 'weibull': 'weibull',
        'lognorm': 'lognorm', 'lognormal': 'lognorm',
        'pareto': 'pareto', 'beta': 'beta',
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

class make_list_FuncWC:
    def __init__(self, size_random: _size_random, init_cost: Union[int, float, Callable]) -> None:
        self._size_random = size_random
        self._init_cost = init_cost
        self._sub_random = self._bind_error
    
    def branch_cost(self, **kwargs):
        return (self._init_cost if isinstance(self._init_cost, (int, float)) else self._init_cost(**kwargs))
    
    def toFuncWC(self, weight: Union[float, int]) -> _func_weight_cost:
        """导出 _FuncWC 以供合并调用，需要设置权重"""
        return _func_weight_cost(self.__call__, weight, self.branch_cost, self._size_random.mean())
    
    def _bind_error(self):
        raise ValueError("请先执行 bind_method，方可使用 __call__")
    
    def bind_method(self, sub_random: _meta_random) -> None:
        self._sub_random = sub_random
    
    def __call__(self, depth: int, remain: int) -> Tuple[Any, float]:
        # 生成列表大小
        size = self._size_random()
        
        # 根据 size 个子节点计算安全递归深度
        sub_depth = self._sub_random._get_safe_depth(depth - 1, remain / size)
        
        # 3. 计算列表花费
        cost = self.branch_cost( depth = sub_depth + 1, size = size)
        
        # 4. 如果无法支付列表花费，返回非法对象
        if remain < cost:
            return None, float('inf')
        
        # 若子深度为负，则返回空列表（不能有递归）
        if sub_depth < 0:
            return [], cost
        
        # 5. 列表至少为1层
        res = [None] * size
        for i in range(size):
            # 递归调用，使用 safe_depth-1
            res[i], c = self._sub_random(depth=sub_depth, remain=remain - cost)
            cost += c
            if remain < cost:  # 放弃第 i 项，提前结束
                return res[:i], (cost - c)
        
        # 深度为0时，无法递归子节点故返回空列表（相当于一个元素）
        return res, cost

# 重点改进：完成 _dict_random 类
class make_dict_FuncWC(make_list_FuncWC):
    def __init__(self, size_random: _size_random, init_cost: Union[int, float, Callable], key_random: _meta_random) -> None:
        assert key_random.fixed_num == len(key_random) , "key_random must be a fixed-cost meta_random."
        super().__init__(size_random=size_random, init_cost=init_cost)
        # 字典的平均长度 × 键的期望值
        self.keys_cost = size_random.mean() * key_random.mean()
    
    def branch_cost(self, **kwargs):
        # 字典本体的开销 + 字典键值对的期望开销
        return super().branch_cost(**kwargs) + self.keys_cost
    
    def __call__(self, depth: int, remain: int) -> Tuple[Any, float]:
        res,cost = super().__call__(depth = depth, remain =remain)
        if res is None: return None,cost # 无效返回
        return dict(res),cost + self.keys_cost

# 仅叶子列表（层级为1）花费1点
@staticmethod
def _LLcost1(depth: int, size: int) -> int:
    """仅叶子列表（层级为1）花费1点"""
    return 1 if depth == 1 else 0

# 重点改进：完善 main 函数
if __name__ == "__main__":
    # 创建别名生成器
    alias = _alias_str_generator(8)
    
    # 创建基础随机生成器
    leaf_base = _meta_random([
        _func_weight_cost(_int, 2, 0),
        _func_weight_cost(_float, 2, 0),
        _func_weight_cost(_bool, 1, 0),
        _func_weight_cost(_none, 1, 0),
        _func_weight_cost(alias._generate_safe_string, 2, 0),
        _func_weight_cost(alias._generate_trap_string, 2, 1),
    ])
    
    # 创建列表大小随机生成器（均匀分布，0-100）
    size_random = _size_random('expo', lambd=0.01)
    print("E(size)={:.2f} , D(size)={:.2f}".format(size_random.mean(), size_random.std()))
    
    # 创建递归列表随机生成器
    listRandom = make_list_FuncWC(size_random, init_cost=_LLcost1)
    listRandom_func = listRandom.toFuncWC(10)
    
    # 创建递归字典随机生成器
    dictRandom = _dict_random(size_random, dict_cost_fun=2, alias_generator=alias)
    dictRandom_func = dictRandom.toFuncWC(15)
    
    # 将列表和字典随机生成器与基础随机生成器结合
    merge_random = leaf_base + [listRandom_func, dictRandom_func]
    
    # 必须绑定 _list_random 和 _dict_random 对象的 sub_random 方法
    listRandom.bind_method(merge_random)
    dictRandom.bind_method(merge_random)
    
    # 生成一个随机对象
    depth, remain = 1000, 1000
    print(f"depth:{depth},remain:{remain}")
    obj, cost = merge_random(depth=depth, remain=remain)
    print(f"生成的随机对象: {obj}")
    print(f"花费: {cost}")