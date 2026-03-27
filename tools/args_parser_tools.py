from typing import Any, Callable, Dict, List, Tuple, Union, Optional, get_type_hints, get_args, get_origin,Generic,TypeVar,Iterator,Hashable,Deque,Iterable,Protocol, runtime_checkable

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
ITER_TYPE = TypeVar("ITER_TYPE", bound=Iterable) # 可迭代对象类型变量

class SafeFlatten(Generic[T,ITER_TYPE]):
    """安全地扁平化一个可迭代对象，自动环检测，避免成环死循环。
    返回格式: (节点列表, 环节点索引)
    """
    @classmethod
    def flatten(cls, iter:ITER_TYPE) -> Tuple[List[T], int]:
        """
        扁平化节点结构，返回节点列表和环索引（-1表示无环）
        节点需要通过 iter 构造成可迭代对象
        """
        seen = {}  # 存储节点id -> 索引
        res = []
        
        for cur in iter:
            node_id = id(cur)
            if node_id in seen:
                return res, seen[node_id]  # 返回当前列表和环开始索引
            
            seen[node_id] = len(res)
            res.append(cur)
        
        return res, -1
    
# 待修订，用于 ListNodeKit
class IterNext(Generic[T]):
    """迭代器，用于遍历链表（通过 next 属性获取下一个节点）"""
    def __init__(self, head: T):
        """初始化迭代器，从指定节点开始"""
        self.link = head
    
    def __next__(self) -> T:
        """返回当前节点并移动到下一个节点"""
        if self.link is None:
            raise StopIteration
        node = self.link
        self.link = node.next  # 移动到下一个节点
        return node
    
    def __iter__(self) -> 'IterNext[T]':
        """返回自身，使对象可迭代"""
        return self
    
@runtime_checkable
class HasNext(Protocol):
    next: Optional[Any]

# 定义支持 .next 属性的协议（泛型约束）
T_NEXT = TypeVar("T_NEXT",bound=HasNext)

class ListNodeKit(Generic[T_NEXT]):
    """
    链表调试增强工具，使用代理模式（安全实现）
    用法: link = ListNodeKit(head_node)
    """
    def __init__(self, node: T_NEXT , prep_property: str = "val"):
        self._node = node  # 保留原始节点，不修改原始对象
        if node is not None:
            assert hasattr(node, prep_property), f"ListNodeKit 的 node 参数对象非空，但缺少属性 {prep_property} （其通过 prep_property 参数设置）"
            self._prep_property = prep_property

    def __getattr__(self, name: str) -> Any:
        """代理属性访问，使next属性返回ListNodeKit"""
        if name == 'next':
            if self._node.next is None:
                return None
            return ListNodeKit(self._node.next)  # 返回ListNodeKit代理
        return getattr(self._node, name)

    def flatten(self) -> Tuple[List[T_NEXT], int]:
        """安全扁平化链表，返回节点列表和环索引"""
        if self._node is None and "标记1":
            return [], -1
        # 使用迭代器遍历ListNodeKit对象
        it = IterNext[ListNodeKit[T_NEXT]](self)
        return SafeFlatten[T_NEXT, IterNext[ListNodeKit[T_NEXT]]].flatten(it)

    def __repr__(self) -> str:
        """安全打印链表，自动标记环（> 和 ^）"""
        nodes, circle_index = self.flatten()
        str_lst = []
        
        # 环之前的节点
        for i in range(circle_index):
            str_lst.append(_formated_string(nodes[i].val))
        
        # 有环标记
        if circle_index != -1:
            str_lst.append(">")
        
        # 环之后的节点
        for i in range(circle_index, len(nodes)):
            str_lst.append(_formated_string(nodes[i].val))
        
        # 环结束标记
        if circle_index != -1:
            str_lst.append("^")
        
        return f"<ListNodeKit>:[{','.join(str_lst)}]"
    
    # 使ListNodeKit可以像列表一样索引
    def __getitem__(self, index: int) -> 'ListNodeKit[T_NEXT]':
        if index < 0:
            raise IndexError("Negative index not supported")
        cur = self
        for _ in range(index):
            if cur.next is None:
                raise IndexError("Index out of range")
            cur = cur.next
        return cur

    def __eq__(self, other: Any) -> bool:
        """支持与ListNode或ListNodeKit的比较，使用ID比较确保正确性"""
        if isinstance(other, ListNodeKit):
            return id(self._node) == id(other._node)
        else:
            return id(self._node) == id(other)
        return False

# 用于 TreeNodeKit（但需要保留一定的泛用性）
# class 层序遍历(SafeFlatten[Deque[Generic[T]]]):
#     def __init__(self, root: T) -> None:
#         super().__init__()
#         self.node_queue = deque([root])

#     def __next__(self):
#         """子类可以修改：将 node 的子节点加入队"""
#         if self.node_queue:
#             node = self.node_queue.popleft()
#             if node:
#                 yield node
#                 if node.left:
#                     self.node_queue.append(node.left)
#                 if node.right:
#                     ...
    
#     def __iter__(self):
#         ...
