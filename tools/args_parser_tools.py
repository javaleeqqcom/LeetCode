from typing import Any, Callable, Dict, List, Tuple, Union, Optional, get_type_hints, get_args, get_origin,Generic,TypeVar,Iterator,Hashable,Deque,Iterable,Protocol, runtime_checkable ,cast
from collections import deque,defaultdict
from itertools import chain
from typing_extensions import Self
from binarytree import build
import json
import numpy as np
import cython

__DEBUG__ = False

def _is_base_type(sig_type) -> bool:
    """
    判断类型是否属于 _BASE_TYPE 范畴
    _BASE_TYPE = Union[
        _BASE_TYPE,  # int, float, bool, None, str
        List["_BASE_TYPE"], 
        Dict[Union[str, int], "_BASE_TYPE"]
    ]
    """
    # 处理 Optional/Union 类型
    origin = get_origin(sig_type)
    
    if origin is Union:
        args = get_args(sig_type)
        # 过滤掉 NoneType，检查所有非 None 类型
        non_none_args = [arg for arg in args if arg is not type(None)]
        # 所有非 None 类型都必须是标准类型
        return all(_is_base_type(arg) for arg in non_none_args)
    
    # 基础类型检查
    if sig_type in (int, float, bool, str, type(None)):
        return True
    
    # List 类型检查
    if origin is list or sig_type is list:
        args = get_args(sig_type)
        if not args:  # 裸 list
            return True
        # 检查元素类型
        return all(_is_base_type(arg) for arg in args)
    
    # Dict 类型检查
    if origin is dict or sig_type is dict:
        args = get_args(sig_type)
        if not args:  # 裸 dict
            return True
        # 检查键类型（必须是 str 或 int）和值类型
        key_type, value_type = args[0], args[1] if len(args) > 1 else Any
        key_ok = key_type in (str, int) or get_origin(key_type) is Union
        value_ok = _is_base_type(value_type)
        return key_ok and value_ok
    
    # 其他类型（如 ListNode, TreeNode 等自定义类型）
    return False

def _extract_actual_type(sig_type):
    """
    从类型注解中提取实际类型，用于注册表匹配
    """
    origin = get_origin(sig_type)
    
    if origin is not None:
        # 处理 Union/Optional 情况
        if origin is Union:
            args = get_args(sig_type)
            # 过滤掉 NoneType，返回第一个非 None 类型
            non_none_args = [arg for arg in args if arg is not type(None)]
            if len(non_none_args) == 1:
                return _extract_actual_type(non_none_args[0])
            elif len(non_none_args) > 1:
                # 多个非 None 类型，返回第一个（Union 情况）
                return _extract_actual_type(non_none_args[0])
        else:
            return origin
    
    # 非泛型类型，直接返回
    return sig_type

def _formated_string(val):
    # 处理字符串类型：转义单引号并包裹在 '' 中
    if isinstance(val, str):
        escaped = val.replace("'", "\\'")
        return f"'{escaped}'"
    
    # 递归处理列表
    elif isinstance(val, list):
        return "[" + ", ".join(_formated_string(item) for item in val) + "]"
    
    # 递归处理字典
    elif isinstance(val, dict):
        items = [f"{_formated_string(k)}: {_formated_string(_formated_string(v))}" for k, v in val.items()]
        # 注意：这里根据需求，如果是嵌套处理，只需对内部值再次调用即可
        return "{" + ", ".join(f"{_formated_string(k)}: {_formated_string(v)}" for k, v in val.items()) + "}"
    
    # 递归处理元组
    elif isinstance(val, tuple):
        return "(" + ", ".join(_formated_string(item) for item in val) + ")"
    
    # 其他基本类型（int, float, bool 等）直接返回其字符串表示
    else:
        return str(val)

# 定义支持 .next 属性的协议（泛型约束）
T = TypeVar("T")

class KitBase(Generic[T]): # 泛型
    """调试增强基类（代理模式）"""
    
    def __init__(self, node: Optional[T]):
        object.__setattr__(self, '_node', node)

    def __bool__(self) -> bool:
        return self._node is not None

    @classmethod
    def unwrap(cls, other: 'KitBase[T] | T | None') -> T | None:
        """
        提取包装类内部的原始节点。
        - 如果 other 是 KitBase 子类实例，返回其内部 _node。
        - 否则直接返回 other 本身（可能为 None）。
        """
        if isinstance(other, KitBase):
            # other._node 的类型理论上为 T_Node，但类型检查器无法自动收窄，使用 cast
            return cast(T, other._node)
        return other
        
    def __getattr__(self, name: str) -> T:
        node = object.__getattribute__(self, '_node')
        if name in ['_node']:
            return node
        
        if __DEBUG__: print(f"KitBase.__getattr__({name})")

        if node is None:
            raise AttributeError(f"Empty node has no attribute '{name}'")
        return getattr(node, name)

    def __setattr__(self, name: str, value: Any) -> None:
        value = KitBase.unwrap(value) # 关键：若 value 是 KitBase 包装对象，必须用 KitBase.unwrap(value) 解包
        if name == '_node':
            object.__setattr__(self,'_node',value)
        else: # 其余属性视为给 self.node 赋值

            if __DEBUG__: print(f"KitBase.__setattr__({name})")

            node = object.__getattribute__(self, '_node')
            if node is None:
                raise AttributeError(f"Can't set attribute '{name}' on empty node")
            setattr(node, name, value)

    def __eq__(self, other: Any) -> bool:
        return id(self._node) == id(self.unwrap(other))
    
    def __ne__(self, other: Any) -> bool:
        return id(self._node) != id(self.unwrap(other))
    
class SafeIterBase(Iterator[Tuple[int, T]]):
    def __init__(
        self,
        init_node: KitBase[T]|T|None = None,
        init_idx: int = 0,
        early_stop: bool = not __DEBUG__,
        getitem_null_end: bool = False
    ):
        """
        安全收集迭代结果，避免访问重复节点（支持BFS、DFS遍历）。
        :param init_node: 初始节点，可以是 KitBase 包装的对象，也可以是原生节点对象，还可以为空
        :param init_idx: 初始索引，默认为 0
        :param early_stop: 是否提前停止（为 True 时遇到重复节点马上停止，为 False 时则跳过重复节点直到无非重复节点为止）
        :param getitem_null_end: 使用 __getitem__ 访问索引 i 时，若没有遇到重复节点，且 0..i-1 的索引非空，是否允许 None 作为索引 i 的返回值（默认 False）
        """
        # ⚠️ 核心：统一 unwrap
        init_node = KitBase.unwrap(init_node)

        self._seen: Dict[int, List[int]] = defaultdict(list)
        self._revisit = list()

        self._current_node = init_node
        self._current_idx = init_idx
        self._early_stop = early_stop 
        self._getitem_null_end = getitem_null_end

        if init_node is not None:
            self._seen[id(init_node)].append(init_idx)

    # ==================== 核心安全检查（统一 unwrap） ====================
    def _safe_id(self, node: Optional[T]) -> int:
        node = KitBase.unwrap(node)
        return id(node)

    def _check_safe(self, assigned_idx: int, node: Optional[T]) -> bool:
        if node is None:
            return False

        nid = self._safe_id(node)

        if nid in self._seen:
            if 1 ==  len(self._seen[nid]):
                self._revisit.append(nid)
            return False

        self._seen[nid].append(assigned_idx)

        return True

    # ==================== 新增 __getitem__ ====================
    def __getitem__(self, idx: int) -> Optional[T]:
        if idx < 0:
            raise IndexError("Negative index not supported")

        # ⭐ 关键：让子类提供“重建入口”
        it = self._clone_from_start()
        i = 0
        for i,(_, node) in enumerate(it):
            if i==idx:
                return KitBase.unwrap(node)
        if it.repeat_indices:
            raise IndexError("出现重复节点")
        # 允许 None 作为合法索引，但仅限于末端
        if self._getitem_null_end and i+1 == idx:
            return None
        raise IndexError("索引超出范围")
    
    def _clone_from_start(self):
        raise NotImplementedError("子类必须实现 _clone_from_start")
    
    # ==================== next ====================
    def __next__(self) -> Tuple[int, T]:
        if self._current_node is None:
            raise StopIteration

        # 1. 准备当前要返回的结果 POP
        res = (self._current_idx, self._current_node)

        # 2. 由子类实现寻找后继节点 PUSH
        self._prepare_next()

        # 如果开启了 early_stop 且刚刚探测到了环
        if self._early_stop and self._revisit:
            self._current_node = None

        return res

    @property
    def repeat_indices(self) -> List[int]:
        """返回所有重复节点的首次索引，顺序与重复检测到顺序一致"""
        res = [self._seen[nid][0] for nid in self._revisit]
        if __DEBUG__:
            assert len(res) == len(set(res)), "重复索引列表中存在重复元素"
        return res

    @property
    def first_repeat(self) -> Optional[int]:
        """返回第一个检测到的重复节点的首次索引"""
        return self._seen[self._revisit[0]][0] if self._revisit else None

    def _prepare_next(self):
        """抽象方法：由子类实现，内部必须使用 _check_safe 控制入栈/入队"""
        raise NotImplementedError

    @classmethod
    def _flatten(cls, it: "SafeIterBase", max_idx: Optional[int] = None)->Tuple[List[Tuple[int,T]],List[int]]:
        """
        安全收集迭代结果，可选限制最大索引。

        :param iterable: 产生 (索引, 节点) 对的迭代器
        :param max_idx:   最大索引（包含），若提供则仅收集 idx < max_idx 的元素，并提前停止迭代
        :return 停止索引列表: 遍历时遇到的“重复节点索引”或“超过max_idx的索引（强制停止）”的列表
        :return: ([(索引, 节点),...], 停止索引列表)
        """
        items = []
        for idx, node in it:
            if max_idx is not None and idx > max_idx:
                return items, it.repeat_indices + [idx]
            items.append((idx, node))
        return items, it.repeat_indices

def ReprDecorator(prep_property: str = "val"):
    """
    类装饰器：为 ToStringClass 注入指定的打印属性，调用 to_string(self,prep_property) 实现默认打印行为。
    用法: 
    @ReprDecorator("value")
    class HasReprClass(ToStringClass): pass
    """
    def wrapper(cls):
        # 在被装饰的类中定义 __repr__，利用闭包捕获 prep_property
        def __repr__(self):
            # 直接调用类方法 to_string，传入捕获的属性名
            return self._to_string(self._node, prep_property)
        
        cls.__repr__ = __repr__

        return cls
    return wrapper
