from typing import Any, Callable, Dict, List, Tuple, Union, Optional, get_type_hints, get_args, get_origin,Generic,TypeVar,Iterator,Hashable,Deque,Iterable,Protocol, runtime_checkable ,cast
from collections import deque
from binarytree import build

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

KT = TypeVar('KT')   # 键类型（例如索引）
NT = TypeVar('NT')   # 节点类型
class SafeIter(Generic[KT, NT]):
    def __init__(self, iterable: Iterator[Tuple[KT, NT]]):
        self._iter = iterable
        self._seen = {}
        self._repeat_key = None   # 记录首次重复的键，若无重复则为 None

    def __iter__(self):
        return self

    def __next__(self) -> Tuple[KT, NT]:
        try:
            key, node = next(self._iter)
        except StopIteration:
            raise
        node_id = id(node)
        if node_id in self._seen:
            self._repeat_key = self._seen[node_id]   # 记录重复键
            raise StopIteration   # 立即停止迭代
        self._seen[node_id] = key
        return key, node

    @property
    def repeat_key(self) -> Optional[KT]:
        """返回首次出现重复节点的键，若无重复返回 None。"""
        return self._repeat_key

    @classmethod
    def flatten(cls, iterable: Iterator[Tuple[KT, NT]]) -> Tuple[List[Tuple[KT, NT]], Optional[KT]]:
        """辅助方法：将安全迭代器的结果收集为列表，同时返回重复键。"""
        safe_iter = cls(iterable)
        items = list(safe_iter)
        return items, safe_iter.repeat_key
    
@runtime_checkable
class HasNext(Protocol):
    next: Optional[Any]
# 定义支持 .next 属性的协议（泛型约束）
T_NEXT = TypeVar("T_NEXT",bound=HasNext)

# 待修订，用于 ListNodeKit
class IterNext(Generic[T_NEXT]):
    """迭代器，用于遍历链表（通过 next 属性获取下一个节点）"""
    def __init__(self, head: Optional[T_NEXT]):
        """初始化迭代器，从指定节点开始"""
        self.link = head
        self.idx = 0
    
    def __next__(self) -> Tuple[int,T_NEXT]:
        """返回当前节点并移动到下一个节点"""
        if not self.link:
            raise StopIteration
        node = self.link
        self.link = node.next  # 移动到下一个节点
        self.idx += 1
        return (self.idx - 1,node)
    
    def __iter__(self) -> 'IterNext':
        """返回自身，使对象可迭代"""
        return self

T_Node = TypeVar('T_Node', bound=Optional[Any]) # NodeType 必须包含 None 的情况
class KitBase(Generic[T_Node]): # 泛型
    """调试增强基类（代理模式）"""
    
    def __init__(self, node: Optional[T_Node]):
        object.__setattr__(self, '_node', node)

    @property
    def node(self) -> T_Node:
        return object.__getattribute__(self, '_node')

    @node.setter
    def node(self, value: T_Node) -> None:
        object.__setattr__(self, '_node', value)

    def __bool__(self) -> bool:
        return self.node is not None

    def __getattr__(self, name: str) -> T_Node:
        if name == '_node':
            return object.__getattribute__(self, name)
        if self.node is None:
            raise AttributeError(f"Empty node has no attribute '{name}'")
        return getattr(self.node, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == '_node':
            object.__setattr__(self, name, value)
        else:
            if self.node is None:
                raise AttributeError(f"Can't set attribute '{name}' on empty node")
            setattr(self.node, name, value)

    @classmethod
    def unwrap(cls: type['KitBase[T_Node]'], other: 'KitBase[T_Node] | T_Node | None') -> T_Node | None:
        """
        提取包装类内部的原始节点。
        - 如果 other 是 KitBase 子类实例，返回其内部 _node。
        - 否则直接返回 other 本身（可能为 None）。
        """
        if isinstance(other, KitBase):
            # other._node 的类型理论上为 T_Node，但类型检查器无法自动收窄，使用 cast
            return cast(T_Node, other._node)
        return other
        
    def __eq__(self, other: Any) -> bool:
        return id(self.node) == id(self.unwrap(other))

class ListNodeKitBase(KitBase[T_NEXT]):
    """ 链表调试增强工具，使用代理模式（安全实现） 用法: link = ListNodeKit(head_node) """
    @property
    def next(self)->'ListNodeKitBase[T_NEXT]':
        if self.node is None:
            raise AttributeError(f"空链表不能使用 next 属性")
        # 关键：返回当前类的实例，保持装饰器效果延续
        return self.__class__(self.node.next)
    
    @next.setter
    def next(self, value: 'ListNodeKitBase[T_NEXT]|T_NEXT') -> None:
        """
        显式定义 setter，支持 kit.next = node 或 kit.next = other_kit
        """
        if self.node is None:
            raise AttributeError("Can't set attribute on None (empty ListNodeKitBase)")
        
        # 如果赋值的是包装类，提取其内部节点
        self.node.next = self.unwrap(value)

    # 使ListNodeKit可以像列表一样索引
    def __getitem__(self, index: int) -> 'ListNodeKitBase[T_NEXT]':
        if index < 0:
            raise IndexError("Negative index not supported")
        cur = self
        for _ in range(index):
            if cur: # 非空链表
                cur = cur.next
            else:
                raise IndexError("Index out of range")
            
        return cur
    
    def flatten(self:'ListNodeKitBase[T_NEXT]|T_NEXT|None') -> Tuple[List[T_NEXT], int|None]:
        """
        1. 实例调用：kit.flatten() -> arg 为 kit 实例
        2. 类调用：ListNodeKit.flatten(head) -> arg 为 head 节点
        """
        # 如果 arg 是 ListNodeKit 实例，取出其内部 node
        node = self.node if isinstance(self, ListNodeKitBase) else self

        it = IterNext[T_NEXT](node)  # 👈 从原始节点开始
        Node_List, circle_index = SafeIter.flatten(it)

        return [node for idx,node in Node_List], circle_index

    @classmethod
    def to_string(cls, head: Optional[T_NEXT], prep_property: str = "val") -> str:
        """安全打印链表，自动标记环（> 和 ^）"""
        nodes, circle_index = ListNodeKitBase[T_NEXT].flatten(head)        

        str_lst = []
        
        # 环之前的节点（若无环则全部节点）
        for i in range(circle_index if circle_index else len(nodes)):
            str_lst.append(_formated_string(getattr(nodes[i],prep_property)))
        
        # 有环标记
        if circle_index is not None:
            str_lst.append(">")
        
            # 环之后的节点
            for i in range(circle_index, len(nodes)):
                assert len(nodes)>0,"len(nodes)==0"
                str_lst.append(_formated_string(getattr(nodes[i],prep_property)))
        
            # 环结束标记
            str_lst.append("^")
        
        return f"<ListNodeKit>:[{','.join(str_lst)}]"
    
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
            return self.to_string(self._node, prep_property)
        
        cls.__repr__ = __repr__
        return cls
    return wrapper

@runtime_checkable
class HasLR(Protocol):
    left: Optional[Any]
    right: Optional[Any]

# 定义支持 .next 属性的协议（泛型约束）
T_LR = TypeVar("T_LR",bound=HasLR)

# 待修订，用于 ListNodeKit
class LayeredTraversal(Generic[T_LR]):
    """迭代器，用于遍历二叉树，输出（完全二叉树索引，二叉树节点）"""
    def __init__(self, root: Optional[T_LR]):
        """初始化迭代器，从指定节点开始"""
        if root:
            # 完全二叉树索引+1 作为键，方便计算后继索引
            self._node_queue = deque([(1,root)])
        else:
            self._node_queue = deque()
    
    def __next__(self) -> Tuple[int,T_LR]:
        """返回当前队首节点并将其后继节点加入队列"""
        if not self._node_queue:
            raise StopIteration
        idx1,node = self._node_queue.popleft()
        # _node_queue push 进的节点要求全部有效，若本次 pop 出的节点居然无效，则说明数据遭到破坏，可能是其他进程篡改
        assert node, "当前节点无效，可能是数据遭到破坏或被其他进程篡改"
        if node.left:
            self._node_queue.append((2*idx1,node.left))
        if node.right:
            self._node_queue.append((2*idx1+1,node.right))
        return (idx1,node)
    
    def __iter__(self) -> 'LayeredTraversal[T_LR]':
        """返回自身，使对象可迭代"""
        return self
    
class TreeNodeKitBase(KitBase[T_LR]):
    """
    二叉树调试增强工具基类，使用代理模式。
    提供安全的扁平化（层序遍历）和重复节点检测，避免因错误的树结构导致死循环。
    """

    @property
    def left(self) -> 'TreeNodeKitBase[T_LR]':
        if self.node is None:
            raise AttributeError("空树节点不能使用 left 属性")
        return self.__class__(self._node.left)

    @left.setter
    def left(self, value: 'TreeNodeKitBase[T_LR] | T_LR | None'):
        if self._node is None:
            raise AttributeError("空树节点不能设置 left 属性")
        self.node.left = self.unwrap(value)   # 使用 unwrap 简化

    @property
    def right(self) -> 'TreeNodeKitBase[T_LR]':
        if self._node is None:
            raise AttributeError("空树节点不能使用 right 属性")
        return self.__class__(self._node.right)

    @right.setter
    def right(self, value: 'TreeNodeKitBase[T_LR] | T_LR | None'):
        if self._node is None:
            raise AttributeError("空树节点不能设置 right 属性")
        self._node.right = self.unwrap(value)

    def __getitem__(self, index: int) -> 'TreeNodeKitBase[T_LR]':
        """按层序遍历顺序索引...若树非法...节点可能出现重复，停止迭代并报错"""
        if index < 0:
            raise IndexError("索引不能为负数")
        safe_iter = SafeIter(LayeredTraversal[T_LR](self._node))
        node_count = 0
        for i, (_, node) in enumerate(safe_iter):
            node_count += 1
            if i == index:
                return self.__class__(node)
        # 迭代提前终止，可能因为环或正常结束
        if safe_iter.repeat_key is not None:
            raise IndexError(
                f"索引 {index} 访问时遇到环或重复节点，首次重复键为 {safe_iter.repeat_key}。"
                f"已遍历 {node_count} 个节点后检测到重复。"
            )
        else:
            # 正常结束，节点总数 = node_count
            raise IndexError(
                f"索引 {index} 超出节点总数（共 {node_count} 个节点）。"
            )
    
    def layer_iter(self) -> SafeIter:
        """调用 SafeIter 安全地层序遍历，遍历完毕或出现重复节点时停止"""
        pass 

    def flatten(self) -> Tuple[List[Tuple[int, T_LR]], Optional[int]]:
        """层序遍历树，返回 (<完全二叉树索引键，节点>列表, 首次出现重复节点的键)。"""
        it = LayeredTraversal[T_LR](self._node)
        return SafeIter.flatten(it)   # 直接使用 SafeIter.flatten

    def __repr__(self) -> str:
        if self._node is None:
            return "<TreeNodeKit: empty>"
        idx_node, repeat_key = self.flatten()
        idx_node_str_list = [f'{idx}:{node.val}' for idx, node in idx_node]
        return "<TreeNodeKit: {}{}>".format(
            idx_node_str_list,
            f", repeat_key:{repeat_key}"if repeat_key else ""
        )