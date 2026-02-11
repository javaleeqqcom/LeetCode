import random
import string
import re
import math
import sys
from typing import Any, List, Tuple, Union, Optional, Callable ,TypeVar, overload

# 定义基础类型生成函数（与 compacted_json.py 命名一致）
def _gen_none(*args, **kwargs) -> None: return None
def _gen_int(*args, **kwargs) -> int: return random.randint(-100, 100)
def _gen_float(*args, **kwargs) -> float: return random.uniform(-10.0, 10.0)
def _gen_bool(*args, **kwargs) -> bool: return random.choice([True, False])

# 判断是否为叶子序列
def _is_leaf_sequence(obj: Any) -> bool:
    """判断是否为叶子序列（list/tuple + 元素全为基础类型）"""
    if not isinstance(obj, (list, tuple)):
        return False
    return all(isinstance(x, (int, float, str, bool, type(None))) for x in obj)

class _alias:
    """ 以 f'{alias_prefix}{hex_len位十六进制数}' 的格式作为别名"""
    def __init__(self, hex_len: int = 32, alias_prefix: str = "@") -> None:
        if hex_len <= 0:
            raise ValueError("hex_len must be positive")
        if not alias_prefix:
            raise ValueError("alias_prefix cannot be empty")
        self._hex_len = hex_len
        self._alias_prefix = alias_prefix
        # 动态构建正则表达式（转义特殊字符）
        escaped_prefix = re.escape(alias_prefix)
        self._alias_pattern = re.compile(rf'"({escaped_prefix}[0-9a-fA-F]{{{hex_len}}})"')

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
        length = random.randint(1, self._hex_len + 3)
        while True:
            s = ''.join(random.choices(self.CHARSET, k=length))
            if re.match(self._alias_pattern, s) is None:
                return s

# 类型别名
_FuncWC = TypeVar('_FuncWC', bound='_func_weight_cost')
_CHOICE_RANDOM = TypeVar('_CHOICE_RANDOM', bound='_choice_random')
_META_RANDOM = TypeVar('_META_RANDOM', bound='_meta_random')
_OBJ_COST = Tuple[Any, Union[float, int]]


# 以下类定义保持不变
class _func_weight_cost:
    def __init__(self, func: Callable, weight: Union[float, int], 
                 cost0: Union[float, int, Callable],
                 cost1: Union[float, int, Callable] = 0,  # E[S]
                 cost2: Union[float, int, Callable] = 0):  # E[S(S-1)] = E[S^2] - E[S]
        self.func = func
        assert weight >= 0, "权重必须非负"
        self.weight = weight
        self.cost0 = cost0
        self.cost1 = cost1  # 用于期望递推 (E[S])
        self.cost2 = cost2  # 用于方差递推 (E[S(S-1)])
    
    def is_fixed(self) -> bool:
        """是否为固定 cost"""
        return isinstance(self.cost0, (float, int)) and (self.cost1 == self.cost2 == 0)
    
    def __lt__(self, other: '_func_weight_cost') -> bool:
        # 先比 is_fixed
        is_fixed = self.is_fixed()
        if is_fixed != other.is_fixed():
            return is_fixed
        # 若 cost可比 再比 cost
        if is_fixed and self.cost0 != other.cost0:
            return self.cost0 < other.cost0
        # 最后比 weight
        return self.weight > other.weight

class _meta_random:
    # 类静态变量：动态获取系统最大递归深度的一半
    _max_depth = sys.getrecursionlimit() // 2
    def __init__(self, UninstantiatedErrorMessage: str = "虚函数不能被实例化") -> None:
        self._uninstanciated_error_message = UninstantiatedErrorMessage
        pass
    
    def __call__(self, *args: Any, **kwds: Any) -> _OBJ_COST:
        raise Exception(self._uninstanciated_error_message)  # 虚函数，需要在子类中实现
    
    def mean(self, **kwargs) -> float:
        raise Exception(self._uninstanciated_error_message)
    
    def _get_safe_depth(self, depth: int, remain: Union[int, float]) -> int:
        """根据 remain 估算安全深度"""
        assert depth < self._max_depth  # 从高深度开始，找到最大的深度 d 使得 _dp_expectations[d] <= remain
        for d in range(depth, -1, -1):
            if self.mean(depth=d) <= remain:
                return d
        return 0

class _choice_random(_meta_random):
    """根据 func_weight_cost 元组中的：（可调用方法，权重，花费）依据各项的权重随机抽取一个可调用方法，返回其结果和花费。
     若 cost 为 Tuple[Callable,Callable] 则为可变花费，通常用于非叶子节点随机对象，要求`可调用方法`必须返回一个元组（结果，花费）。
    """
    _max_times = 100  # 最大尝试次数，防止无限循环
    
    def __init__(self, source: List[_func_weight_cost]):
        self.data = sorted(source)  # 排序确保固定花费优先，权重高的靠前
        self.weights = tuple(obj.weight for obj in self.data)
        self.total_weight = sum(self.weights)
        # 固定花费项的索引范围
        self.fixed_weights = tuple(obj.weight for obj in self.data if obj.is_fixed())
        self.fixed_num = len(self.fixed_weights)
        self.fixed_sum_weight = sum(self.fixed_weights)
        # 新增：双矩DP表
        self._dp_expectations = []  # 一阶矩: E[T(d)]
        self._dp_second_moments = []  # 二阶矩: E[T(d)^2]
        if self.fixed_sum_weight <= 0:
            Warning("无固定花费项，无法计算期望值")
        else:
            self._init_expectation()
    
    def _init_expectation(self):
        """初始化深度0的双矩"""
        # 一阶矩 (E[T(0)])
        E0 = sum(obj.weight * obj.cost0 for obj in self.data if obj.is_fixed()) / self.fixed_sum_weight
        
        # 二阶矩 (E[T(0)^2])
        M0 = sum(obj.weight * (obj.cost0 ** 2) for obj in self.data if obj.is_fixed()) / self.fixed_sum_weight
        
        self._dp_expectations = [E0]
        self._dp_second_moments = [M0]
    
    def _extend_dp(self, depth: int):
        """扩展DP表至深度 'depth'，同时计算双矩"""
        if 0 ==len(self._dp_expectations):
            self._init_expectation()
        for d in range(len(self._dp_expectations), depth + 1):
            E_prev = self._dp_expectations[d-1]  # E[T(d-1)]
            M_prev = self._dp_second_moments[d-1]  # E[T(d-1)^2]

            E_prev = self._dp_expectations[d-1]  # E[T(d-1)]
            E_res,M_res = 0.0,0.0
            for obj in self.data:
                cost0 = obj.cost0 if isinstance(obj.cost0, (int, float)) else obj.cost0(depth=d)
                cost1 = obj.cost1 if isinstance(obj.cost1, (int, float)) else obj.cost1(depth=d)
                cost2 = obj.cost2 if isinstance(obj.cost2, (int, float)) else obj.cost2(depth=d)  # 重点：使用 cost2
                
                # 期望递推 (不变)
                E_res += obj.weight * (cost0 + cost1 * E_prev)
                
                # 二阶矩递推 (修正关键)
                M_res += obj.weight * (
                    cost0**2 + 
                    2 * cost0 * cost1 * E_prev + 
                    cost1 * M_prev + 
                    cost2 * E_prev**2  # 正确使用 cost2
                )
            
            self._dp_expectations.append(E_res / self.total_weight)
            self._dp_second_moments.append(M_res / self.total_weight)

    def mean(self, **kwargs) -> float:
        """估计随机对象在不限制总消费（remain = inf）情况下深度为 depth 的期望消费（深度0为叶子节点）"""
        depth = kwargs.get('depth', -1)
        self._extend_dp(depth)
        return self._dp_expectations[depth]
    
    def variance(self, **kwargs) -> float:
        depth = kwargs.get('depth', -1)
        self._extend_dp(depth)
        return self._dp_second_moments[depth] - self._dp_expectations[depth]**2
    
    def __len__(self):
        return len(self.data)
    
    def __call__(self, *args, **kwargs) -> _OBJ_COST:
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
    
    def __add__(self: _CHOICE_RANDOM, other: Union[_CHOICE_RANDOM, _FuncWC, List[_FuncWC]]) -> _CHOICE_RANDOM:
        """合并生成器（支持合并元组、列表或另一个_meta_random）"""
        # 转换其他类型为列表
        if isinstance(other, _func_weight_cost):
            other_list = [other]
        elif isinstance(other, _choice_random):
            other_list = other.data
        elif isinstance(other, list):
            other_list = other
        else:
            raise TypeError(
                f"不支持的类型: {type(other)}. " "必须是 _func_weight_cost, _meta_random, 或列表"
            )
        # 合并数据
        combined = self.data + other_list
        return self.__class__(combined)

class _size_random:
    """根据非负分布函数生成随机整数，并提供理论期望与方差（连续分布）"""
    # 用户友好别名映射 -> 标准前缀（用于拼接 *variate）
    _ALIAS_MAP = {
        'exp': 'expo',
        'exponential': 'expo',
        'gamma': 'gamma',
        'weibull': 'weibull',
        'lognorm': 'lognorm',
        'lognormal': 'lognorm',
        'pareto': 'pareto',
        'beta': 'beta',
        'uniform': 'uniform',
        'uni': 'uniform'
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
    
    def variance(self) -> float:
        """返回原始连续分布的理论方差（非取整后）"""
        return self._theoretical_second_moment - self._theoretical_mean ** 2

def _assert_cost_fun(cost_fun:Callable , fun_name:str= "cost_fun"):
    assert isinstance(cost_fun, Callable) , f"{fun_name} must be int, float, or a callable accepting 'depth' and 'size'"
    # 检查可调用对象是否接受 depth 和 size 参数
    try:
        # 测试调用：检查函数签名
        test_val = cost_fun(depth=0, size=0)
        assert isinstance(test_val, (int, float)),f"{fun_name} callable must return a numeric value (int/float)"
    except TypeError as e:
        # 捕获参数错误（函数不接受 depth/size）
        raise TypeError(f"{fun_name} callable must accept 'depth' and 'size' keyword arguments") from e
    except Exception as e:
        # 捕获其他异常
        raise ValueError(f"{fun_name} callable raised unexpected error: {e}") from e
    return True

class make_list_FuncWC:
    def __init__(self, size_random: _size_random, init_cost: Union[int, float, Callable]) -> None:
        # === 关键修复：添加 init_cost 类型检查 ===
        assert isinstance(init_cost, (int, float)) or _assert_cost_fun(init_cost, "init_cost")

        self._size_random = size_random
        self._init_cost = init_cost
        self._sub_random = _meta_random("需要先使用 bind_method 绑定递归生成随机子对象的 _choice_random 方法")
    
    def branch_cost(self, **kwargs):
        return (self._init_cost if isinstance(self._init_cost, (int, float)) else self._init_cost(**kwargs))
    
    def toFuncWC(self, weight: Union[float, int]) -> _func_weight_cost:
        # 计算 E[S(S-1)] = E[S^2] - E[S]
        mu_S = self._size_random._theoretical_mean
        mu_S2 = self._size_random._theoretical_second_moment
        cost2 = mu_S2 - mu_S  # 正确计算 E[S(S-1)]
        
        return _func_weight_cost(
            self.__call__,
            weight,
            self.branch_cost,
            self._size_random.mean(),  # cost1 = E[S]
            cost2  # cost2 = E[S(S-1)]
        )
    
    def bind_method(self, sub_random: _meta_random) -> None:
        self._sub_random = sub_random
    
    def __call__(self, depth: int, remain: int) -> _OBJ_COST:
        # 生成列表大小
        size = self._size_random()
        # 根据 size 个子节点计算安全递归深度。注意 size 为0时，则为空列表，深度为 0，则 sub_depth = -1，但依然需要计算列表花费
        sub_depth = self._sub_random._get_safe_depth(depth - 1, remain / size) if size > 0 else -1
        # 3. 计算列表花费
        cost = self.branch_cost(depth=sub_depth + 1, size=size)
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

class _pair_random(_meta_random):
    def __init__(self, A: _meta_random, B: _meta_random) -> None:
        self.A = A
        self.B = B
    
    def __call__(self, *args: Any, **kwds: Any) -> _OBJ_COST:
        a, ca = self.A(*args, **kwds)
        b, cb = self.B(*args, **kwds)
        return (a, b), ca + cb
    
    def mean(self, **kwargs) -> float:
        return self.A.mean(**kwargs) + self.B.mean(**kwargs)

# 重点改进：完成 _dict_random 类
class make_dict_FuncWC(make_list_FuncWC):
    def __init__(self, size_random: _size_random, init_cost: Union[int, float, Callable], keys_random: _choice_random) -> None:
        super().__init__(size_random=size_random, init_cost=init_cost)
        self._keys_random = keys_random
    
    def bind_method(self, sub_random: _meta_random) -> None:
        self._sub_random = _pair_random(self._keys_random, sub_random)
    
    def __call__(self, depth: int, remain: int) -> _OBJ_COST:
        res, cost = super().__call__(depth=depth, remain=remain)
        if res is None:
            return None, cost  # 无效返回
        return dict(res), cost

# 仅叶子列表（层级为1）花费1点
@staticmethod
def _LLcost1(**kwargs):
    """仅叶子列表（层级为1）花费1点"""
    depth = kwargs.get('depth', 0)
    return 1 if depth == 1 else 0

def dict_cost_fun(**kwargs):
    depth = kwargs.get('depth', 0)
    return math.sqrt(depth)

import pandas as pd

if __name__ == "__main__":
    # 创建别名生成器
    alias = _alias_str_generator(8)
    
    # 创建基础随机生成器
    leaf_base = _choice_random([
        _func_weight_cost(_gen_int, 2, 1),
        _func_weight_cost(_gen_float, 2, 2),
        _func_weight_cost(_gen_bool, 1, 1),
        _func_weight_cost(_gen_none, 1, 0),
        _func_weight_cost(alias._generate_safe_string, 2, 1),
        _func_weight_cost(alias._generate_trap_string, 2, 5),
    ])
    
    # 创建列表大小随机生成器（指数分布，λ=0.1）
    NL_size_random = _size_random('expo', lambd=0.1)
    print("E(size)={:.2f} , D(size)={:.2f}".format(NL_size_random.mean(), NL_size_random.variance()))
    
    # 创建递归列表随机生成器
    listRandom = make_list_FuncWC(NL_size_random, init_cost=1)
    
    # 创建递归字典随机生成器
    keysRandom = _choice_random([
        _func_weight_cost(alias._generate_safe_string, 1, 0),
        _func_weight_cost(alias._generate_trap_string, 1, 1),
    ])
    D_size_random = _size_random('uniform', a=0, b=4)
    dictRandom = make_dict_FuncWC(D_size_random, dict_cost_fun, keysRandom)
    
    # 将列表和字典随机生成器与基础随机生成器结合
    merge_random = leaf_base + [listRandom.toFuncWC(5), dictRandom.toFuncWC(5)]
    print(f"merge_random: total_num = {len(merge_random)} ,fixed_num = {merge_random.fixed_num}")
    
    # 必须绑定 _list_random 和 _dict_random 对象的 sub_random 方法
    listRandom.bind_method(merge_random)
    dictRandom.bind_method(merge_random)
    
    # ================== 完整统计代码（含卡方检验） ==================
    depths = list(range(0, 10))
    results = []
    all_costs = {d: [] for d in depths}
    
    # 95%置信区间临界值（自由度=99）
    t_critical = 1.984
    chi2_lower = 73.36  # 自由度99的χ²分布下限
    chi2_upper = 128.42 # 自由度99的χ²分布上限
    
    for depth in depths:
        costs = []
        for _ in range(100):  # 100次实验
            _, cost = merge_random(depth=depth, remain=float('inf'))
            costs.append(cost)
        
        # 计算实际统计量
        avg_cost = sum(costs) / 100
        std_dev = math.sqrt(sum((x - avg_cost) ** 2 for x in costs) / 99)  # 样本标准差
        sample_var = std_dev ** 2  # 样本方差
        
        # 理论统计量
        theory_mean = merge_random.mean(depth=depth)
        theory_var = merge_random.variance(depth=depth)  # 新增：理论方差
        
        # 95%置信区间（期望）
        margin = t_critical * std_dev / math.sqrt(100)
        lower_bound = avg_cost - margin
        upper_bound = avg_cost + margin
        in_interval = lower_bound <= theory_mean <= upper_bound
        
        # 卡方检验（方差）
        in_chi2_interval = False
        if theory_var > 0:
            chi2 = (100 - 1) * sample_var / theory_var
            in_chi2_interval = (chi2_lower <= chi2 <= chi2_upper)
        
        # 保存结果
        results.append((
            depth,
            avg_cost,
            theory_mean,
            std_dev,
            in_interval,
            in_chi2_interval
        ))
        all_costs[depth] = costs
    
    # 创建DataFrame并打印
    df = pd.DataFrame(results, columns=[
        '深度',
        '平均cost',
        '理论期望cost',
        '实际标准差',
        '理论期望在95%CI内',
        '卡方检验通过'
    ])
    
    pd.set_option('display.float_format', '{:.8f}'.format)
    print("\n深度比较表格（含95%置信区间和卡方检验）:")
    print(df)
    
    # 保存到CSV
    df.to_csv('cost_comparison_with_ci_and_chi2.csv', index=False)
    print("\n结果已保存到 cost_comparison_with_ci_and_chi2.csv")
    # ================== 结束完整统计代码 ==================