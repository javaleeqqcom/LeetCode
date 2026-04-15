"""
iter_node_tool.py - 链表调试增强工具（方案二：操作包装节点）
用于 LeetCode 本地自动化测试框架，支持环检测、安全遍历、美观打印。
纯 Python 实现，便于后续转换为 Cython。
"""
__DEBUG__ = True

from typing import (
    Any, Dict, List, Optional, Iterator, Tuple, TypeVar, Generic, Protocol,Hashable,
    cast,runtime_checkable
)
from collections import deque
import sys
from typing_extensions import Self
from itertools import chain
from binarytree import build

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


# ---------- SafeIterBase2 ----------
class SafeIterBase2(Generic[T_Node]):
    """
    安全迭代器基类（方案二版本）
    - 操作包装节点（KitBase2 实例）
    - 环检测使用包装节点的哈希（基于原生节点内存地址）
    - 子类需实现 _prepare_next()
    """

    def __init__(self, node: KitBase2[T_Node] = KitBase2(None), early_stop: bool = False):
        """
        Args:
            init_node: 起始包装节点（可为 None）
            early_stop: 遇到重复节点时是否立即停止迭代（环检测时强制停止）
        """
        self._cur_node: KitBase2[T_Node] = node if isinstance(node,KitBase2) else KitBase2(node) # 必须代入包装类节点
        self._early_stop = early_stop
        self._kit_cls = type(self._cur_node) # 类型“向下保持”

        # 重复节点识别字典： raw.id -> rv_idx
        self._seen: Dict[int,int] = {} 
        # self._revisit[rv_idx] = (并查下标 , node) : 
        #   并查下标：
        #       当为 -1 时表示非重复节点；
        #       当为 rv_idx 表示并查集所指向的重复节点下标；
        # 特别地 ._revisit[rv_idx]=(rv_idx,node) 时说明 node 是重复节点
        self._revisit: List[Tuple[int,KitBase2[T_Node]]] = [] 
        self._repeat_num: int = 0 # 重复节点数量

        if node:
            self._seen[id(node.raw)] = 0    # 首个 rv_idx = 0
            self._revisit.append((-1,node)) # 首次出现，并查下标为 -1

    @property
    def repeat_num(self):
        return self._repeat_num

    @classmethod
    def _getitem(cls,it: Self, index: int ,allowed_null:bool= False) -> KitBase2[T_Node]:
        """
        根据索引获取节点。
        - 如果索引>=有效节点数量，当 allowed_null 为假则抛出 IndexError，否则为真则返回 包装类的 None 节点
        - 如果中途遇到重复节点，仅当 it._early_stop 为真时抛出 IndexError，否则将跳过重复节点（重复节点不计入有效节点数）
        - 其余情况按 iterator 的遍历次序返回节点
        """
        if index < 0:
            raise IndexError("Negative index not supported")

        i = -1
        for i,node in enumerate(it):
            if i == index:
                return node
            
        # 如果迭代因环而停止，抛出异常
        if it._early_stop and it.revisit_nodes:
            raise IndexError(f"Repeated reference detected by index: {it.revisit_nodes[0].visit_index}.")

        # 索引超出范围，若允许 allowed_null 返回空节点
        if allowed_null:
            return it._kit_cls(None)  # ✅ 保持子类类型
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

        raw_id = id(node.raw)
        if raw_id in self._seen:
            # 原生节点id 为 raw_id 的首个包装节点存于 self._revisit[rv_idx]
            rv_idx = self._seen[raw_id]    
            self._revisit.append((rv_idx, node))
            # self._revisit2[rv_idx] = (并查索引, 包装节点)
            if -1 == self._revisit[rv_idx][0]: # 若首次记录为重复访问节点，需更新并查索引为 rv_idx
                self._revisit[rv_idx] = (rv_idx, self._revisit[rv_idx][1])
                self._repeat_num += 1

            return False
        else:
            rv_idx = len(self._revisit)
            self._seen[raw_id] = rv_idx
            self._revisit.append((-1, node)) # 首次出现节点的并查索引为 -1

            return True

    @classmethod
    def _flatten(cls, it:SafeIterBase2, max_len: int = -1) -> List[KitBase2[T_Node]]:
        """
        安全展开链表，返回包装节点列表。
        默认 max_len = -1，则不会限制展开节点数量
        """
        if 0==max_len: return []
        nodes: List[KitBase2[T_Node]] = [] # 若 Cython 化，可以设置 max_len（非负时）为最大容量
        for cur_len,node in enumerate(it,1): 
            nodes.append(node)
            if cur_len == max_len: # cur_len 是逐一递增的，若 max_len 为正，则必能生效
                break
        return nodes
        
    def __iter__(self) -> Iterator[KitBase2[T_Node]]:
        return self

    def __next__(self) -> KitBase2[T_Node]:
        if not self._cur_node:
            raise StopIteration

        result = self._cur_node
        self._prepare_next()

        # 早停：一旦检测到重复节点就停止（环已出现）
        if self._early_stop and self.repeat_num > 0:
            self._cur_node = KitBase2(None) 
        # 注意 result 是有效结果，触发早停的是 result 的后继节点，因此不能在此 StopIteration，而应修改为空节点，待下一轮迭代 StopIteration
        return result

    def _prepare_next(self) -> None:
        """由子类实现：更新 self._cur_node 为下一个节点，并进行安全检查。"""
        raise NotImplementedError

    @property
    def revisit_nodes(self) -> List[KitBase2[T_Node]]:
        """返回所有重复访问的节点（按发现顺序）"""
        return [node for i,(p,node) in enumerate(self._revisit) if i==p]
        
# 定义原生节点协议（必须包含 .next 属性）
@runtime_checkable
class HasNext(Protocol):
    next: Optional[Any]

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
        self.allowed_null = getitem_null_end

    def _prepare_next(self) -> None:
        """移动到下一个节点，自动包装，并进行环检测。"""
        if self._cur_node:
            self._cur_node = self._cur_node.next
            self._check_safe(self._cur_node) # 不安全会自动触发早停，无需置 None

    @property
    def circle_index(self) -> int:
        """获取当前迭代器的环节点索引，若无则返回 -1"""
        if self.repeat_num > 0:
            assert 1 == self.repeat_num, f"链表重复索引理论上不可能超过一次，而实际重复索引数量={self.repeat_num}，可能是被非法重置初始节点，重复迭代。"
            return self.revisit_nodes[0].visit_index 
        return -1

    def copy(self,reset_index = False) -> IterNext2[T_NEXT]:
        """注意默认 reset_index=False，即默认不重置索引值"""
        
        node = cast(ListNodeKitBase ,self._kit_cls(self._cur_node) 
                    if reset_index else self._cur_node)
        return IterNext2(node, self.allowed_null)

    def __getitem__(self, index: int) -> ListNodeKitBase[T_NEXT]:
        """
        根据索引获取节点。
        - 如果索引越界且 allowed_null=True，返回 None
        - 如果遇到环且未达到索引，根据 allowed_null 返回 None 或抛出 IndexError
        """
        return cast(ListNodeKitBase,
                    self._kit_cls(SafeIterBase2._getitem( self.copy(), index, self.allowed_null ))
                    )
    
    def flatten(self, max_len: int = -1) -> Tuple[List[ListNodeKitBase[T_NEXT]], int]:
        """
        安全展开链表，返回节点列表和停止索引。当 max_len 为非负值时，则限制输出的长度不大于 max_len。
        :params max_len:
        raw ...
        :return nodes 注意会受到    
        self._early_stop 影响，为真时会跳过重复节点继续展开，为假时遇到重复节点就会停止收集和...
        stop_index < len(nodes) 说明包含重复节点，其下标为 stop_index， 若 因为 max_len 而停止，stop_index = max_len ，否则 stop_index = -1 （包含有效节点恰好为 max_len 个的情况）
        """
        it = self.copy()
        nodes = SafeIterBase2._flatten(it, max_len=max_len)

        stop_index = it.circle_index # 检测到环，则以环节点索引为停止索引
        if -1 == stop_index and it._cur_node: # 未检测到环，但是迭代器没有迭代到空节点
            stop_index = len(nodes) # 说明迭代器因 max_len 限制而停止
        return nodes, stop_index

class ListNodeKitBase(KitBase2[T_NEXT]):
    """ 调试增强工具，使用代理模式（安全实现） 用法: link = ListNodeKit(head_node) """
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
            raise AttributeError("Empty node has no 'next' attribute")
        
        # 关键：返回当前类的实例，保持装饰器效果延续
        return self.__class__(node = node.next, visit_index = self.visit_index + 1)
    
    @next.setter
    def next(self, value) -> None:
        node = self.raw # 提取原生节点
        if node is None:
            raise AttributeError("Empty node has no 'next' attribute")
        node.next = self.unwrap(value) # 对原生节点赋值需要去包装
        
    def flatten(self: 'ListNodeKitBase[T_NEXT] | T_NEXT | None', max_len: int = -1) -> Tuple[List[ListNodeKitBase[T_NEXT]], int]:
        """展开链表（包装节点类），若 max_len 非负则限制展开节点数量不超过 max_len"""
        return IterNext2[T_NEXT](ListNodeKitBase(self),False).flatten(max_len)
        
    def flatten_raw(self: 'ListNodeKitBase[T_NEXT] | T_NEXT | None', max_len: int = -1) -> Tuple[List[T_NEXT], int]:
        """展开链表（原生节点类），若 max_len 非负则限制展开节点数量不超过 max_len"""
        kit_nodes,stop_index = IterNext2[T_NEXT](ListNodeKitBase(self),False).flatten(max_len)
        return [node.raw for node in kit_nodes if node.raw], stop_index

    def __iter__(self)->IterNext2[T_NEXT]:
        """返回安全链表迭代器"""
        return IterNext2[T_NEXT](ListNodeKitBase(self,visit_index=0),False) # 注意不能用 self 代替 ListNodeKitBase(self)，因为要重置 visit_index
    
    def __getitem__(self, key)->ListNodeKitBase[T_NEXT]:
        """根据索引获取链表节点，返回的是 ListNodeKitBase 包装类对象，允许最后一个节点恰为空节点返回，但若中途遇到重复节点或空节点则抛出异常"""
        return ListNodeKitBase(IterNext2[T_NEXT](ListNodeKitBase(self,0),True)[key]) # 用 ListNodeKitBase 同理（见 __iter__）
    
    @classmethod
    def _to_string(cls, head: ListNodeKitBase[T_NEXT]|T_NEXT|None, prep_property: str = "val" , max_len:int = -1) -> str:
        """安全打印链表，自动标记环（> 和 ^）"""
        # 注意要用 unwrap 去包装节点
        nodes, stop_index = (head if isinstance(head,ListNodeKitBase) else ListNodeKitBase(head)).flatten( max_len = max_len)       

        str_lst = []
        
        # 环之前的节点（若无环则全部节点）
        for i in range(stop_index if -1 != stop_index else len(nodes)):
            try:
                str_lst.append(_formatted_string(getattr(nodes[i],prep_property)))
            except:
                raise Exception(f"len(nodes)={len(nodes)}, stop_index={stop_index}, node={nodes[-1]}")
        
        # 有异常终止索引
        if stop_index >= 0:
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
    
    def __repr__(self) -> str:
        return super().__repr__()
    