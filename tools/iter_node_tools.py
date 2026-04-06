"""
iter_node_tool.py - 链表调试增强工具（方案二：操作包装节点）
用于 LeetCode 本地自动化测试框架，支持环检测、安全遍历、美观打印。
纯 Python 实现，便于后续转换为 Cython。
"""
__DEBUG__ = False
MAX_LEN = 100

from typing import (
    Any, Dict, List, Optional, Iterator, Tuple, TypeVar, Generic, Protocol,
    cast,runtime_checkable
)
from collections import deque
import sys
from typing_extensions import Self

# ---------- 辅助函数 ----------
def _formatted_string(val: Any) -> str:
    """将值格式化为 Python 字面量字符串，用于打印链表节点值。"""
    if isinstance(val, str):
        escaped = val.replace("'", "\\'")
        return f"'{escaped}'"
    elif isinstance(val, list):
        return "[" + ", ".join(_formatted_string(item) for item in val) + "]"
    elif isinstance(val, dict):
        return "{" + ", ".join(f"{_formatted_string(k)}: {_formatted_string(v)}" for k, v in val.items()) + "}"
    elif isinstance(val, tuple):
        return "(" + ", ".join(_formatted_string(item) for item in val) + ")"
    else:
        return str(val)


T_Node = TypeVar("T_Node")

# ---------- KitBase2 ----------
class KitBase2(Generic[T_Node]):
    """
    调试增强基类（代理模式），扩展支持哈希和索引存储。
    子类应实现 __hash__ = id(_node)
    """

    def __init__(self, node: KitBase2|T_Node|None):
        object.__setattr__(self, '_node', KitBase2.unwrap(node))

    def __bool__(self) -> bool:
        return self.raw is not None

    @classmethod
    def unwrap(cls, other: 'KitBase2 | T_Node | None') -> Optional[T_Node]:
        """
        提取包装类内部的原始节点。
        - 如果 other 是 KitBase2 子类实例，返回其内部 _node。
        - 否则直接返回 other 本身（可能为 None）。
        """
        if isinstance(other, KitBase2):
            return other.raw
        return other

    @property
    def raw(self) -> Optional[T_Node]:
        """直接访问原生节点"""
        node = object.__getattribute__(self, '_node')
        assert not hasattr(node,'_node'), "Node has been wrapped twice!"
        return node

    @property
    def visit_index(self)->Any:
        """ 访问节点索引编号，子类需覆盖此属性以返回特定类型 """
        raise NotImplementedError("Subclasses must implement visit_index")
    
    def __getattr__(self, name: str) -> Any:
        """代理属性访问到原生节点"""
        return getattr(self.raw, name)

    def __setattr__(self, name: str, value: Any) -> None:
        """代理属性设置到原生节点，自动解包包装类"""
        node = self.raw
        if node is None:
            raise AttributeError(f"Can't set attribute '{name}' on empty node")
        # 如果 value 是包装类，提取原生节点
        setattr(node, name, KitBase2.unwrap(value))

    def __hash__(self) -> int:
        """基于原生节点内存地址的哈希，用于环检测"""
        return id(self._node)

    def __eq__(self, other: Any) -> bool:
        """比较两个包装节点是否包装同一个原生节点"""
        other_raw = KitBase2.unwrap(other)
        return self._node is other_raw

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

# ---------- SafeIterBase2 ----------
class SafeIterBase2(Generic[T_Node]):
    """
    安全迭代器基类（方案二版本）
    - 操作包装节点（KitBase2 实例）
    - 环检测使用包装节点的哈希（基于原生节点内存地址）
    - 子类需实现 _prepare_next() 和 _clone_from_start()
    """

    def __init__(self, node: KitBase2[T_Node] = KitBase2(None), early_stop: bool = False):
        """
        Args:
            init_node: 起始包装节点（可为 None）
            early_stop: 遇到重复节点时是否立即停止迭代（环检测时强制停止）
        """
        self._seen: Dict[KitBase2[T_Node], List[KitBase2[T_Node]]] = {}
        self._revisit: List[KitBase2[T_Node]] = []
        self._cur_node: KitBase2[T_Node] = node if isinstance(node,KitBase2) else KitBase2(node) # 必须代入包装类节点
        self._early_stop = early_stop

        if node:
            self._seen[node] = [node]

    @classmethod
    def _getitem(cls,it: Self, index: int ,getitem_null_end:bool= False) -> KitBase2[T_Node]:
        """
        根据索引获取节点。
        - 如果遇到重复节点抛出 IndexError
        - 如果索引越界超过1次或 _getitem_null_end 为假则抛出 IndexError，否则返回 None
        - 其余情况按 iterator 的遍历次序返回节点
        """
        if index < 0:
            raise IndexError("Negative index not supported")

        i = -1
        for i,node in enumerate(it):
            if i == index:
                return node
            # 如果迭代因环而停止，抛出异常
            if it.revisit_nodes:
                raise IndexError(f"Repeated reference detected by index: {it.revisit_nodes[0].visit_index}.")

        # 索引恰好超出范围，若允许 _getitem_null_end 返回空节点
        if getitem_null_end and i+1 == index:
            return KitBase2(None)
        else: # 否则报错
            raise IndexError(f"Index: {index} out of range")

    def _check_safe(self, node: KitBase2[T_Node]) -> bool:
        """
        检查节点是否安全（无重复访问），并记录访问历史。
        Returns:
            True: 节点第一次出现，安全
            False: 不可访问（空节点或节点已出现过）
        """
        if not node: return False # 空节点不可访问
        if node in self._seen:
            visitor_list = self._seen[node] # 重复访问 node 的历次包装节点
            if len(visitor_list) == 1:
                self._revisit.append(visitor_list[0]) # 易错，_revisit 记录的必须是首次访问的包装节点，因此不能赋值 node，而是赋值 visitor_list[0]
            visitor_list.append(node)
            return False
        else:
            self._seen[node] = [node]
            return True

    def __iter__(self) -> Iterator[KitBase2[T_Node]]:
        return self

    def __next__(self) -> KitBase2[T_Node]:
        if not self._cur_node:
            raise StopIteration

        result = self._cur_node
        self._prepare_next()

        # 早停：一旦检测到重复节点就停止（环已出现）
        if self._early_stop and self._revisit:
            self._cur_node = self._cur_node.__class__(None) 
        # 注意 result 是有效结果，触发早停的是 result 的后继节点，因此不能在此 StopIteration，而应修改为空节点，待下一轮迭代 StopIteration
        return result

    def _prepare_next(self) -> None:
        """由子类实现：更新 self._cur_node 为下一个节点，并进行安全检查。"""
        raise NotImplementedError

    @property
    def revisit_nodes(self) -> List[KitBase2[T_Node]]:
        """返回所有重复访问的节点（按发现顺序）"""
        return self._revisit # 若改为 Cython 需只读
    
    @property
    def seen_nodes_dict(self)-> Dict[KitBase2[T_Node], List[KitBase2[T_Node]]]:
        return self._seen # 若改为 Cython 需只读（字典不可修改，不过提取的节点可以修改）

# 定义原生节点协议（必须包含 .next 属性）
@runtime_checkable
class HasNext(Protocol):
    next: Optional[Any]
# 定义支持 .next 属性的协议（泛型约束）
T_NEXT = TypeVar("T_NEXT",bound=HasNext)

# ---------- IterNext2 ----------
class IterNext2(SafeIterBase2[T_NEXT]):
    """
    链表安全迭代器，继承 SafeIterBase2 实现环检测，自动包装原生节点。
    支持 __getitem__ 和 flatten 方法。
    """

    def __init__(
        self,
        head: ListNodeKitBase[T_NEXT],
        getitem_null_end: bool = False
    ):
        """
        Args:
            head: 链表头节点（包装类实例）
            getitem_null_end: __getitem__ 风格索引越界时返回 None（True）或抛出 IndexError（False）
        """

        super().__init__(node=head if isinstance(head,ListNodeKitBase) else ListNodeKitBase(head),
                        early_stop=True) # 链表不支持跳过，故早停为 True
        self._getitem_null_end = getitem_null_end

    def _prepare_next(self) -> None:
        """移动到下一个节点，自动包装，并进行环检测。"""
        if self._cur_node:
            self._cur_node = self._cur_node.next
            self._check_safe(self._cur_node) # 不安全会自动触发早停，无需置 None

    @property
    def circle_index(self) -> Optional[int]:
        """获取当前迭代器的环节点索引，若无则返回 None"""
        if self.revisit_nodes:
            assert 1 == len(self.revisit_nodes), f"链表重复索引理论上不可能超过一次，而实际重复索引数量={len(self.revisit_nodes)}，可能是被非法重置初始节点，重复迭代。"
            return cast(ListNodeKitBase,self.revisit_nodes[0]).visit_index 
        return None

    def copy(self,reset_index = False) -> Self:
        """注意默认 reset_index=False，即默认不重置索引值"""
        node = ListNodeKitBase(self._cur_node) if reset_index else cast(ListNodeKitBase,self._cur_node)
        return self.__class__(node, self._getitem_null_end)

    def __getitem__(self, index: int) -> ListNodeKitBase[T_NEXT]:
        """
        根据索引获取节点。
        - 如果索引越界且 _getitem_null_end=True，返回 None
        - 如果遇到环且未达到索引，根据 _getitem_null_end 返回 None 或抛出 IndexError
        """
        return cast( ListNodeKitBase, SafeIterBase2._getitem( self.copy(), index, self._getitem_null_end ))
    
    def __next__(self) -> ListNodeKitBase[T_NEXT]:
        return cast(ListNodeKitBase,super().__next__())
    
    def __iter__(self) -> Iterator[ListNodeKitBase[T_NEXT]]:
        return self

    def flatten(self, max_len: Optional[int] = None) -> Tuple[List[T_NEXT], Optional[int]]:
        """
        安全展开链表，返回节点列表和停止索引。
        """
        assert self._getitem_null_end == False, "flatten 不支持 _getitem_null_end=True"
        it = self.copy()
        stop_index = None
        nodes: List[T_NEXT] = []
        for kit_node in it:
            if (max_len is None) or (kit_node.visit_index < max_len):
                assert kit_node.raw is not None, f"设计错误：_getitem_null_end={self._getitem_null_end}, 但是迭代到 None"
                nodes.append(kit_node.raw)
            else:
                stop_index = max_len # 迭代次数达到 max_len，则以 max_len 为停止索引
                break

        if it.revisit_nodes: # 检测到环，则以环节点索引为停止索引
            stop_index = it.circle_index
        return nodes, stop_index

class ListNodeKitBase(KitBase2[T_NEXT]):
    """ 链表调试增强工具，使用代理模式（安全实现） 用法: link = ListNodeKit(head_node) """
    def __init__(self, node: KitBase2 | T_NEXT | None , visit_index:int = 0):
        super().__init__(node)
        object.__setattr__(self, '_visit_index', visit_index)
        
    @property
    def visit_index(self)->int: # Cython 用int计算机位数的普通有符号整型即可
        """ 访问节点索引编号，用于标记遍历到该节点的迭代次数 """
        return object.__getattribute__(self, '_visit_index')

    @property
    def next(self)->'ListNodeKitBase[T_NEXT]':
        node = self.raw
        if node is None:
            raise AttributeError(f"空链表不能使用 next 属性")
        
        # 关键：返回当前类的实例，保持装饰器效果延续
        return self.__class__(node.next, self.visit_index + 1)
    
    @next.setter
    def next(self, value) -> None:
        raise NotImplementedError("ListNodeKitBase.next.setter 本该仅用于声明，但却被调用了")
        
    def flatten(self: 'ListNodeKitBase[T_NEXT] | T_NEXT | None', max_len: Optional[int] = None) -> Tuple[List[T_NEXT], Optional[int]]:
        """
        安全展开链表，返回节点列表和停止索引。

        支持两种调用方式：
        - 实例调用：`kit.flatten()` 或 `kit.flatten(max_len)`
        - 类/静态风格：`ListNodeKitBase.flatten(head [,max_len])`

        Args:
            max_len: 最大收集节点数，超出则提前终止。

        Returns:
            (nodes, stop_index)
            - nodes: 节点列表（原始节点对象）。
            - stop_index:
                - 检测到环 → 环起始索引
                - 达到 max_len → max_len
                - 正常结束 → None
        """
        return IterNext2[T_NEXT](ListNodeKitBase(self),False).flatten(max_len=max_len)

    def __iter__(self)->IterNext2[T_NEXT]:
        """返回安全链表迭代器"""
        return IterNext2[T_NEXT](ListNodeKitBase(self,visit_index=0),False) # 注意不能用 self 代替 ListNodeKitBase(self)，因为要重置 visit_index
    
    def __getitem__(self, key)->ListNodeKitBase[T_NEXT]:
        """根据索引获取链表节点，返回的是 ListNodeKitBase 包装类对象，允许最后一个节点恰为空节点返回，但若中途遇到重复节点或空节点则抛出异常"""
        return self.__class__(IterNext2[T_NEXT](ListNodeKitBase(self,0),True)[key]) # 用 ListNodeKitBase 同理（见 __iter__）
    
    @classmethod
    def _to_string(cls, head: Optional[T_NEXT], prep_property: str = "val" , max_len:int = MAX_LEN) -> str:
        """安全打印链表，自动标记环（> 和 ^）"""
        # 注意要用 unwrap 去包装节点
        nodes, stop_index = ListNodeKitBase(head).flatten( max_len = max_len)       

        str_lst = []
        
        # 环之前的节点（若无环则全部节点）
        for i in range(stop_index if stop_index else len(nodes)):
            try:
                str_lst.append(_formatted_string(getattr(nodes[i],prep_property)))
            except:
                raise Exception(f"len(nodes)={len(nodes)}, stop_index={stop_index}, node={nodes[-1]}")
        
        # 有异常终止索引
        if stop_index is not None:
            if stop_index == len(nodes):
                str_lst.append("...") # 说明链表长度超过最大限制，截断打印

            else: # 说明检测到链表环
                str_lst.append(">")
            
                # 环之后的节点
                for i in range(stop_index, len(nodes)):
                    assert len(nodes)>0,"len(nodes)==0"
                    str_lst.append(_formatted_string(getattr(nodes[i],prep_property)))
            
                # 环结束标记
                str_lst.append("^")

        return f"<class 'ListNodeKit'>: [{','.join(str_lst)}]"
    