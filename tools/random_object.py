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

class _alias_str_generator(_alias):
    def __init__(self, hex_len: int = 32, alias_prefix: str = "@" ):
        super().__init__(hex_len, alias_prefix)
        self.CHARSET = tuple(set('"' + "'" + "{}[]" + self._alias_prefix + string.digits + string.ascii_letters))

    def _generate_trap_string(self) -> str:
        """生成精确匹配_alias_pattern的陷阱字符串（格式: @{uuid4的hex_len位十六进制}）"""
        hex_part = ''.join(random.choices('0123456789abcdef', k=self._hex_len))
        return self._alias_prefix + hex_part  # 与CompactedJson默认alias_prefix一致

    def _generate_safe_string(self) -> str:
        """生成不匹配 _alias_pattern 的随机字符串"""
        length = random.randint(1, self._hex_len+3)
        while True:
            s = ''.join(random.choices(self.CHARSET, k=length))
            if re.match(self._alias_pattern, s) is None:
                return s

# 定义元组类型
FuncWC = Tuple[Callable, Union[int, float], Optional[Union[int, float]]]

# 判断是否为叶子序列
def _is_leaf_sequence(obj: Any) -> bool:
    """判断是否为叶子序列（list/tuple + 元素全为基础类型）"""
    if not isinstance(obj, (list, tuple)):
        return False
    return all(isinstance(x, (int, float, str, bool, type(None))) for x in obj)

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

    def __len__(self):
        return self.size

    def __call__(self, *args, **kwargs) -> Tuple[Any, Union[int, float]]:
        """返回（随机对象，实际花费）"""
        idx = random.choices(range(self.size), self.weights)[0]
        if self.cost[idx] is not None:
            return self.funcs[idx](*args, **kwargs), self.cost[idx]
        else:
            return self.funcs[idx](*args, **kwargs)

# 定义 _size_random 类
class _size_random:
    """根据分布函数生成大小"""
    def __init__(self, distribution: str, **kwargs):
        """
        初始化大小随机生成器
        
        Args:
            distribution: 分布函数的名称
            **kwargs: 分布函数的参数
        """
        self.distribution = distribution
        self.kwargs = kwargs
        self._validate_distribution()
        
    def _validate_distribution(self):
        """验证分布函数是否支持"""
        if self.distribution not in ['uniform', 'exponential', 'poisson']:
            raise ValueError(f"Unsupported distribution: {self.distribution}")
    
    def __call__(self) -> int:
        """生成大小"""
        if self.distribution == 'uniform':
            return random.randint(self.kwargs['min'], self.kwargs['max'])
        elif self.distribution == 'exponential':
            return int(random.expovariate(1.0 / self.kwargs['mean']))
        # poisson "不是模块“ random "的己知属性 pylance(reportAttributeAccessIssue)
        # elif self.distribution == 'poisson':
        else:
            raise ValueError(f"Unsupported distribution: {self.distribution}")

# 定义 _LLcost1 函数
def _LLcost1(depth: int, size: int) -> int:
    """仅叶子列表（层级为1）花费1点"""
    return 1 if depth == 1 else 0

# 定义 _recursive_random 类
class _recursive_random(_meta_random):
    """递归生成随机对象"""
    def __init__(self, size_random: _size_random, list_cost_fun: Union[int, float, Callable], leaf_random: _meta_random, leaf_list_weight: List[int] = [1, 1]):
        """初始化递归随机生成器
        
        Args:
            size_random: 生成列表大小的随机器
            list_cost_fun: 列表的花费函数
            leaf_random: 叶子节点的随机器
            leaf_list_weight: 叶子列表和非叶子列表的权重
        """
        # 确保 leaf_generator.cost 是数值类型
        assert all(isinstance(c, (int, float)) for c in leaf_random.cost)
        
        # 计算叶子节点的平均花费
        sum_weight = sum(leaf_random.weights)
        self.leaf_cost = sum(w * c for w, c in zip(leaf_random.weights, leaf_random.cost)) / sum_weight
        self.leaf_random = leaf_random
        self.leafSize = len(leaf_random)
        self.sizeRandom = size_random
        self.list_cost = list_cost_fun
        
        # 初始化元随机生成器
        super().__init__([
            (self.leaf_random, leaf_list_weight[0], self.leaf_cost),
            (self._gen_list, leaf_list_weight[1], None)
        ])
    
    def _gen_list(self, depth: int, remain: int) -> Tuple[Any, float]:
        """生成列表
        
        Args:
            depth: 当前深度
            remain: 剩余花费
        """
        # 生成列表大小
        size = self.sizeRandom()
        
        # 计算列表花费
        if callable(self.list_cost):
            remain_after_list = remain - self.list_cost(depth, size)
        else:
            remain_after_list = remain - self.list_cost
        
        # 如果无法支付列表花费，返回叶子节点
        if depth == 0 or remain_after_list < 0:
            return self.leaf_random(depth, remain)
        
        # 递归生成列表元素
        res = []
        for _ in range(size):
            item, cost = self(depth - 1, remain_after_list)
            res.append(item)
            remain_after_list -= cost
            if remain_after_list < 0:
                # 无法支付剩余元素，提前结束
                break
        
        return res, remain - remain_after_list

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
    
    # 创建递归随机生成器
    listRandom = _recursive_random(size_random, _LLcost1, leaf_base)
    
    # 生成一个随机对象
    obj, cost = listRandom(depth=10, remain=1000)
    print(f"生成的随机对象: {obj}")
    print(f"花费: {cost}")