from typing import Any, Callable, Dict, List, Tuple, Union, Optional, get_type_hints, get_args, get_origin,Generic,TypeVar,Iterator,Hashable,Deque,Iterable,Protocol, runtime_checkable

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
    
    def __next__(self) -> T_NEXT:
        """返回当前节点并移动到下一个节点"""
        if not self.link:
            raise StopIteration
        node = self.link
        self.link = node.next  # 移动到下一个节点
        return node
    
    def __iter__(self) -> 'IterNext[T_NEXT]':
        """返回自身，使对象可迭代"""
        return self
    
class ListNodeKitBase(Generic[T_NEXT]):
    """ 链表调试增强工具，使用代理模式（安全实现） 用法: link = ListNodeKit(head_node) """
    def __init__(self, node: Optional[T_NEXT]):
        # 使用 object.__setattr__ 避免触发 __setattr__，防止无限递归
        object.__setattr__(self, '_node', node)

    def __bool__(self):
        return object.__getattribute__(self, '_node') is not None
    
    # 返回原生节点
    @property
    def node(self)->Optional['T_NEXT']:
        return object.__getattribute__(self, "_node")
    
    @node.setter
    def node(self, value: 'ListNodeKitBase[T_NEXT]|T_NEXT') -> None:
        # 如果赋值的是包装类，提取其内部节点
        object.__setattr__(self, "_node", 
            value.node if isinstance(value, ListNodeKitBase) else value
        )

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
        self.node.next = value.node if isinstance(value, ListNodeKitBase) else value

    def __getattr__(self, name: str) -> Any:
        if name == '_node':
            return object.__getattribute__(self, name)
        return getattr(self._node, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == '_node':
            # 直接设置原生节点
            object.__setattr__(self, name, value)
        else:
            if self.node is None: # 如果当前是空节点，不能设置属性
                raise AttributeError("Can't set attribute on None (empty ListNodeKitBase)")
            else:
                # 除了 _node 都视为对原生节点的属性赋值
                setattr(self.node, name, value)

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
    
    def flatten(self:Optional[Union[ListNodeKitBase[T_NEXT],T_NEXT]]) -> Tuple[List[T_NEXT], int]:
        """
        1. 实例调用：kit.flatten() -> arg 为 kit 实例
        2. 类调用：ListNodeKit.flatten(head) -> arg 为 head 节点
        """
        # 如果 arg 是 ListNodeKit 实例，取出其内部 node
        if isinstance(self, ListNodeKitBase):
            node = self._node
        else:
            node = self

        it = IterNext[T_NEXT](node)  # 👈 从原始节点开始
        Node_List, circle_index = SafeFlatten[T_NEXT, IterNext].flatten(it)

        return Node_List, circle_index

    @classmethod
    def to_string(cls, head: Optional[T_NEXT], prep_property: str = "val") -> str:
        """安全打印链表，自动标记环（> 和 ^）"""
        nodes, circle_index = ListNodeKitBase[T_NEXT].flatten(head)        

        str_lst = []
        
        # 环之前的节点
        for i in range(circle_index):
            str_lst.append(_formated_string(getattr(nodes[i],prep_property)))
        
        # 有环标记
        if circle_index != -1:
            str_lst.append(">")
        
        # 环之后的节点
        for i in range(max(0,circle_index), len(nodes)):
            assert len(nodes)>0,"len(nodes)==0"
            str_lst.append(_formated_string(getattr(nodes[i],prep_property)))
        
        # 环结束标记
        if circle_index != -1:
            str_lst.append("^")
        
        return f"<ListNodeKit>:[{','.join(str_lst)}]"
    
    def __eq__(self, other: Any) -> bool:
        """
        核心逻辑：比较包装的 T_NEXT 对象的内存地址 (id)
        支持: Kit == Kit, Kit == Node, Kit == None
        """
        # 如果 compare 对象也是包装类，取出其内部 node
        if isinstance(other, ListNodeKitBase):
            other_node = other._node
        else:
            # 否则视其为原始 Node 或 None
            other_node = other
            
        return id(self._node) == id(other_node)

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
    """迭代器，用于遍历链表（通过 next 属性获取下一个节点）"""
    def __init__(self, root: Optional[T_LR]):
        """初始化迭代器，从指定节点开始"""
        if root:
            self._node_queue = deque([root])
        else:
            self._node_queue = deque()
    
    def __next__(self) -> T_LR:
        """返回当前队首节点并将其后继节点加入队列"""
        if not self._node_queue:
            raise StopIteration
        node = self._node_queue.popleft()
        # _node_queue push 进的节点要求全部有效，若本次 pop 出的节点居然无效，则说明数据遭到破坏，可能是其他进程篡改
        assert node, "当前节点无效，可能是数据遭到破坏或被其他进程篡改"
        if node.left:
            self._node_queue.append(node.left)
        if node.right:
            self._node_queue.append(node.right)
        return node
    
    def __iter__(self) -> 'LayeredTraversal[T_LR]':
        """返回自身，使对象可迭代"""
        return self
    
class TreeNodeKitBase(Generic[T_LR]):
    """
    二叉树调试增强工具基类，使用代理模式。
    提供安全的扁平化（层序遍历）和环检测，避免因错误的树结构导致死循环。
    """
    
    def __init__(self, root: Optional[T_LR]):
        # 使用 object.__setattr__ 避免触发 __setattr__，防止无限递归
        object.__setattr__(self, '_node', root)

    def __getattr__(self, name: str) -> Any:
        """
        代理所有属性访问。
        如果访问的是 'left' 或 'right'，返回包装后的 TreeNodeKitBase 实例。
        """
        # 获取原生节点
        node:T_LR = object.__getattribute__(self, '_node')
        
        if name in ('left', 'right'):
            if not node: 
                raise AttributeError(f"空节点不能使用 {name} 属性")
            # 关键：返回当前类的实例，保持装饰器效果延续
            return self.__class__(getattr(node, name))
        # 访问原生节点
        if name == '_node':
            return node
        # 其余属性都视为访问原生节点下的属性值
        return getattr(node, name)

    def __setattr__(self, name: str, value: Any) -> None:
        """
        代理属性设置。
        如果设置的是 left 或 right，解包值（如果它是 TreeNodeKit）并设置到底层节点。
        """
        
        if name == '_node':
            # 直接设置原生节点
            object.__setattr__(self, name, value)
        else:
            # 获取底层节点引用
            node = object.__getattribute__(self, '_node')
            if not node: # 如果当前是空节点，不能设置属性
                raise AttributeError("Can't set attribute on None (empty TreeNodeKitBase)")
            else:
                # 处理 left/right 赋值
                if name in ('left', 'right') and isinstance(value, TreeNodeKitBase):
                    # 如果赋值的是包装类，提取其内部节点
                    value = value._node
                    
                # 将属性设置到底层原生节点上
                setattr(node, name, value)

    def __bool__(self) -> bool:
        """
        布尔值判断：仅当内部节点不为 None 时为 True。
        用于判断树是否为空：if kit: ...
        """
        return self._node is not None

    @property
    def node(self) -> Optional[T_LR]:
        """
        返回原生的 TreeNode 节点。
        这是解包获取原始数据的关键属性。
        """
        return object.__getattribute__(self, '_node')

    def flatten(self) -> Tuple[List[T_LR], int]:
        """
        安全扁平化二叉树（层序遍历）。
        使用 SafeFlatten 配合 LayeredTraversal 迭代器，自动检测环路。
        
        Returns:
            Tuple[List[T_LR], int]: (节点列表, 环索引)
            - 如果无环，环索引返回 -1。
            - 如果有环，返回检测到的第一个重复节点的索引。
        """
        # 如果是空节点，直接返回空列表
        if not self._node:
            return ([], -1)
            
        # 创建层序遍历迭代器
        it = LayeredTraversal[T_LR](self._node)
        
        # 使用 SafeFlatten 进行安全遍历，自动处理环路
        Node_List, circle_index = SafeFlatten[T_LR, LayeredTraversal].flatten(it)
        
        return Node_List, circle_index

    # --- 为了配合框架的比较逻辑，建议保留 __eq__ ---
    def __eq__(self, other: Any) -> bool:
        """
        比较逻辑：比较包装的 T_LR 对象的内存地址 (id)。
        支持: Kit == Kit, Kit == Node, Kit == None
        """
        # 如果 compare 对象也是包装类，取出其内部 node
        if isinstance(other, TreeNodeKitBase):
            other_node = other._node
        else:
            # 否则视其为原始 Node 或 None
            other_node = other
            
        # 如果两边都是 None，视为相等
        if self._node is None and other_node is None:
            return True
        # 如果一边是 None 另一边不是，视为不等
        if self._node is None or other_node is None:
            return False
            
        # 否则比较内存地址
        return id(self._node) == id(other_node)