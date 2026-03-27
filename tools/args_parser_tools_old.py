from typing import Any, Callable, Dict, List, Tuple, Union, Optional, get_type_hints, get_args, get_origin,Generic,TypeVar,Iterator,Hashable,Deque
from collections import deque

def _is_standard_type(sig_type) -> bool:
    """
    判断类型是否属于 _STANDARD_TYPE 范畴
    _STANDARD_TYPE = Union[
        _BASE_TYPE,  # int, float, bool, None, str
        List["_STANDARD_TYPE"], 
        Dict[Union[str, int], "_STANDARD_TYPE"]
    ]
    """
    # 处理 Optional/Union 类型
    origin = get_origin(sig_type)
    
    if origin is Union:
        args = get_args(sig_type)
        # 过滤掉 NoneType，检查所有非 None 类型
        non_none_args = [arg for arg in args if arg is not type(None)]
        # 所有非 None 类型都必须是标准类型
        return all(_is_standard_type(arg) for arg in non_none_args)
    
    # 基础类型检查
    if sig_type in (int, float, bool, str, type(None)):
        return True
    
    # List 类型检查
    if origin is list or sig_type is list:
        args = get_args(sig_type)
        if not args:  # 裸 list
            return True
        # 检查元素类型
        return all(_is_standard_type(arg) for arg in args)
    
    # Dict 类型检查
    if origin is dict or sig_type is dict:
        args = get_args(sig_type)
        if not args:  # 裸 dict
            return True
        # 检查键类型（必须是 str 或 int）和值类型
        key_type, value_type = args[0], args[1] if len(args) > 1 else Any
        key_ok = key_type in (str, int) or get_origin(key_type) is Union
        value_ok = _is_standard_type(value_type)
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

T = TypeVar("T") # 泛型变量
    
class SafeFlatten(Generic[T]):
    """安全地扁平化一个可迭代对象，自动环检测，避免成环死循环。
    返回格式: (节点列表, 环节点索引)
    """
    @classmethod
    def flatten(cls, node: Optional[T]) -> Tuple[List[T], int]:
        """扁平化节点结构，返回节点列表和环索引（-1表示无环）"""
        seen = {}  # 存储节点id -> 索引
        res = []
        current = node
        
        while current is not None:
            node_id = id(current)
            if node_id in seen:
                return res, seen[node_id]  # 返回当前列表和环开始索引
            
            seen[node_id] = len(res)
            res.append(current)
            current = cls._get_next(current)
        
        return res, -1

    @classmethod
    def _get_next(cls, node: T) -> Optional[T]:
        """子类必须实现：返回下一个节点（类型必须为 Optional[T]）"""
        raise NotImplementedError
    
class 层序遍历(SafeFlatten[Deque[Generic[T]]]):
    def __init__(self, root: T) -> None:
        super().__init__()
        self.node_queue = deque([root])

    @classmethod
    def _push_queue(cls, queue: Deque[T],node:T):
        """子类必须实现：将 node 的子节点加入队"""
        # 如 if node.left: queue.append(node.left)
        raise NotImplementedError

    @classmethod
    def _get_next(cls, queue: Deque[T]) -> Optional[Deque[T]]:
        if queue:
            cur = queue.popleft()
            if cur is not None:
                cls._push_queue(queue,cur)
            return queue
        else:
            return None
