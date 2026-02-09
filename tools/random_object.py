# json_test(directed).py (压力测试增强版)
import json
import re
import uuid
import random
import string
from typing import Any, List, Tuple, Dict, Optional, Callable, Union, Iterable
from multiprocessing import Pool, cpu_count
from functools import partial
import numpy as np
from fractions import Fraction
from compacted_json import _alias

Number = Union[int, float]
FuncWC = Tuple[Callable, Number,Optional[Number]]

def _is_leaf_sequence(obj: Any) -> bool:
    """判断是否为叶子序列（list/tuple + 元素全为基础类型）"""
    if not isinstance(obj, (list, tuple)):
        return False
    return all(isinstance(x, (int, float, str, bool, type(None))) for x in obj)

class _meta_random:
    """
    根据 func_weight_cost 元组中的：（可调用方法，权重，花费）
    依据各项的权重随机抽取一个可调用方法，返回其结果和花费。
    若cost为 None 则该方法为可变花费，要求方法返回一个元组（结果，花费）。
    """
    def __init__(self, fun_w_c_list: List[FuncWC] ):
        self.size = len(fun_w_c_list)
        self.funcs = tuple(fwc[0] for fwc in fun_w_c_list)
        self.weights = tuple(max(0,fwc[1]) for fwc in fun_w_c_list)
        self.cost = tuple(fwc[2] for fwc in fun_w_c_list)

    def __len__(self):
        return self.size
    def append(self,fun_w_c:FuncWC):
        pass
    def extend(self, fun_w_c_list:List[FuncWC]):
        pass
    def tolist(self) -> List[FuncWC]:
        pass
    def __call__(self, *args , **kwargs) -> Tuple[Any ,Number]:
        """返回（随机对象，实际花费）"""
        idx = random.choices(range(self.size), self.weights)[0]
        if self.cost[idx] is not None:
            return self.funcs[idx](*args, **kwargs), self.cost[idx]
        else:
            return self.funcs[idx](*args, **kwargs) # 可递归方法必须实时计算花费

    # def expected_cost(self, *args, **kwargs) -> float:
    #     return self.leaf_cost

class _alias_str_generator(_alias):
    def __init__(self, hex_len: int = 32, alias_prefix: str = "@" ):
        super()
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

def _none(*args , **kwargs) -> None:
    return None
def _int(*args , **kwargs) -> int:
    return random.randint(-100, 100)
def _float(*args , **kwargs) -> float:
    return random.uniform(-10.0, 10.0)
def _bool(*args , **kwargs) -> bool:
    return random.choice([True, False])

class _size_random(_meta_random):
    def __init__(self,哪一种分布函数:str,**分布函数的参数) -> None:
        func_weight_cost = (
            (self.对应分布函数, 1 , 长度的期望值（需要根据对应分布函数及**分布函数的参数计算理论结果） )
        ) # func_weight_cost 仅有一项
        super...func_weight_cost
    
    def 整型均匀分布():
        size = random.randint(*分布函数的参数)
        return size,size # 长度即是cost

    def 指数型分布取整()
        
    def 泊松分布

    ……其他整型分布函数……

def _LLcost1(self,depth:int,size:int)->int:
    return int(1==depth) # 仅叶子列表（层级为1）花费1点

class _recursive_random(_meta_random):
    def __init__(self, size_random:_size_random ,list_cost_fun:Union[Number,Callable], 
                 leaf_random:_meta_random , leaf_list_weight = [1,1]) -> None:
        # 确保 leaf_generator.cost 是数值类型 => 是非递归方法
        assert all(isinstance(c,Number) for c in leaf_random.cost)
        # 待完善，需要根据 递归层数自动计算不同深度的花费
        sum_weight = sum(leaf_random.weights)
        # cost 按 weights 加权平均
        self.leaf_cost = (sum(w*c for w,c in zip(leaf_random.weights,leaf_random.cost))/sum_weight)

        self.leaf_random = leaf_random
        self.leafSize = len(leaf_random) # 非递归方法的数量
        self.sizeRandom = size_random
        self.list_cost = list_cost_fun
        super().__init__([
            (self.leaf_random , leaf_list_weight[0] , self.leaf_cost),
            (self._gen_list , leaf_list_weight[1] , None),
        ]) # 将叶子方法加入递归方法
        
    def _gen_list(self, *args, **kwargs) -> Tuple[Any ,float]:
        """
        与_meta_random 的 __call__方法不同，需要动态计算具体的（随机列表，花费）
        :param self: 说明
        :param args: 说明
        :param kwargs: 说明
        :return: 说明
        :rtype: Tuple[Any, float]
        """
        depth , remain0 = args | kwargs # 需要润色：从参数中提取
        size,_ = self.sizeRandom()
        if callable(self.list_cost):
            remain = remain0 - self.list_cost(depth,size) # 列表额外开销
        else:
            remain = remain0 - self.list_cost
        if 0 == depth or remain<0: # 叶子节点，或者无法支付列表开销
            return self.leaf_random(depth , remain0)
        # 列表至少为1层
        res = [None]*size
        for i in range(size):
            # 递归调用
            res[i],c = self.__call__(depth = depth-1 ,remain = remain)
            remain -= c
            if remain < 0: # 放弃第 i 项，提前结束
                return res[:i] , remain0 - (remain + c)
        return res , remain0 - remain
        
alias = _alias_str_generator(8)
leaf_base = _meta_random(
    [
        (_int , 2 ,0),
        (_float,2 ,0),
        (_bool,1 ,0),
        (_none,1, 0),
        (alias._generate_safe_string, 2, 0),
        (alias._generate_trap_string ,2, 1),
    ]
)

listRandom = _recursive_random(
    _size_random(均匀分布,0,100),_LLcost1,
    leaf_base
    )
listRandom.__call__(depth = 10,remain = 1000)
