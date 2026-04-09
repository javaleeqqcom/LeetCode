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


T_Node = TypeVar("T_Node",bound=Hashable)

# ---------- KitBase2 ----------
class KitBase2(Generic[T_Node]):
    """
    调试增强基类（代理模式），扩展支持哈希和索引存储。
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
        return None
    
    def __getattr__(self, name: str) -> Any:
        """代理属性访问到原生节点"""
        # 1️⃣ 先查类属性
        attr = getattr(type(self), name, None)

        # 2️⃣ 如果是 data descriptor（有 __set__）
        if hasattr(attr, "__get__"):
            # ✅ 调用 property
            return attr.__get__(self)

        # 3️⃣ 否则走你原来的逻辑
        node = self.raw
        return getattr(node, name)

    def __setattr__(self, name: str, value: Any) -> None:
        # 1️⃣ 先查类属性
        attr = getattr(type(self), name, None)

        # 2️⃣ 如果是 data descriptor（有 __set__）
        if hasattr(attr, "__set__"):
            attr.__set__(self, value)   # ✅ 调用 property setter
            return

        # 3️⃣ 否则走你原来的逻辑
        node = self.raw
        if node is None:
            raise AttributeError(f"Can't set attribute '{name}' on empty node")

        setattr(node, name, KitBase2.unwrap(value))

    def __eq__(self, other: Any) -> bool:
        """比较两个包装节点是否包装同一个原生节点，并且 visit_index 相同"""
        if not isinstance(other,KitBase2): return False
        return self.raw is other.raw and self.visit_index == other.visit_index

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)
    
    def __repr__(self) -> str:
        vid = self.self.visit_index
        return "<%s>{%s, %s}"%(
            str(self.__class__),
            "raw.id: 0x{id(self.raw):x}" if self.raw else "raw: None",
            "visit.id: " + (f"0x{vid:x}" if vid and vid >= 2**16 else str(vid))
            )

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
    
# -------------------------- 待修改的代码 ------------------------------

@runtime_checkable
class HasLR(Protocol):
    left: Optional[Any]
    right: Optional[Any]
# 定义支持 .left , .right 属性的协议（泛型约束）
T_LR = TypeVar("T_LR", bound=HasLR)

class TreeBase(KitBase2[T_LR]):
    """二叉树包装基类，支持堆索引和深度计算"""
    def __init__(self, node: KitBase2 | T_LR | None, heap_index: int = 1):
        super().__init__(node)
        object.__setattr__(self, '_heap_index', heap_index)

    @property
    def visit_index(self) -> int:
        """完全二叉树索引（从1开始）"""
        return object.__getattribute__(self,"_heap_index")

    @property
    def depth(self) -> int:
        """节点深度（根深度为1）"""
        if not self.raw:
            return 0
        return self.visit_index.bit_length()

    @property
    def left(self) -> 'TreeBase[T_LR]':
        node = self.raw
        if node is None:
            raise AttributeError("空树节点不能使用 left 属性")
        return self.__class__(node.left if node else None, self.visit_index * 2)

    @left.setter
    def left(self, value: 'TreeBase[T_LR] | T_LR | None'):
        node = self.raw
        if node is None:
            raise AttributeError("空树节点不能设置 left 属性")
        node.left = self.unwrap(value)

    @property
    def right(self) -> 'TreeBase[T_LR]':
        node = self.raw
        if node is None:
            raise AttributeError("空树节点不能使用 right 属性")
        return self.__class__(node.right if node else None, self.visit_index * 2 + 1)

    @right.setter
    def right(self, value: 'TreeBase[T_LR] | T_LR | None'):
        node = self.raw
        if node is None:
            raise AttributeError("空树节点不能设置 right 属性")
        node.right = self.unwrap(value)

    def __repr__(self) -> str:
        return super().__repr__()

class TreeIter(SafeIterBase2[T_LR]):
    """二叉树通用迭代器，支持前/中/后/层序遍历，操作字符串驱动"""
    def __init__(
        self,
        root: TreeBase[T_LR] | T_LR | None,
        operation: str,
        use_queue: bool,
        early_stop: bool = False,
        max_depth: int = -1
    ):
        super().__init__(TreeBase[T_LR](None), early_stop)
        self._kit_cls = type(root) if isinstance(root, TreeBase) else TreeBase[T_LR] # 用于类型向下兼容
        
        self._root = root if isinstance(root,TreeBase) else TreeBase(root) # 类型必须是 TreeBase 及其子类，尽可能保持子类
        self._operation = operation.lower()
        self._instant_updates = 'c' not in self._operation # 无入栈、队本节点，则为即时更新本节点
        self._max_depth = max_depth
        self._depth_exceeded = False

        self._container = deque() if use_queue else []
        self._pop = self._container.popleft if use_queue else self._container.pop

        if self._root:
            self._push(self._root, False)
            self._prepare_next()

    def _push(self, node: TreeBase[T_LR], checked: bool) -> bool:
        """将节点压入容器，若超出深度限制则忽略"""
        if not node:
            return False
        if self._max_depth != -1 and node.depth > self._max_depth:
            self._depth_exceeded = True
            return False
        self._container.append((node, checked))
        return True

    def _prepare_next(self) -> None:
        while self._container:
            node, checked = self._pop()
            if not checked:
                if self._check_safe(node):
                    for op in self._operation:    # 只有检查安全才能 PUSH 后继节点
                        if 'l' == op: self._push(node.left, False)
                        elif 'r' == op: self._push(node.right, False)
                        else: self._push(node, True)
                    if not self._instant_updates: # 非即时更新当前节点，继续 POP
                        continue
                elif self._early_stop: break # 不安全且早停，置为空节点
                else: continue # 不安全，继续 POP
            # 已检查安全，或即时更新，设置 POP 节点为当前节点，跳出循环
            self._cur_node = self.assert_TreeBase(node)
            return
        # 早停或容器为空，置空当前节点
        self._cur_node = self._kit_cls(None)

    def clone_init(self) -> 'TreeIter[TreeBase[T_LR]]':
        """返回从头开始的新迭代器（用于索引访问）"""
        return TreeIter(
            self._root,
            self._operation,
            isinstance(self._container, deque),
            early_stop=self._early_stop,
            max_depth=self._max_depth
        )

    @classmethod
    def assert_TreeBase(cls, node:Any)->TreeBase[T_LR]:
        assert isinstance(node,TreeBase), "设计错误，传入的节点类型应当保持 TreeBase 类及其继承"
        return node

    def flatten(self, max_len: int = -1, raw: bool = False)->Tuple[List[TreeBase[T_LR]] | List[T_LR], TreeIter[TreeBase[T_LR]]]:
        """
        展平遍历结果。
        :param max_len: 最大节点数限制，-1表示无限制
        :param raw: 若为True返回原生节点列表，否则返回包装节点列表
        :return: (节点列表, 迭代器自身)
        """
        it = self.clone_init()
        nodes = SafeIterBase2._flatten(it, max_len)
        if raw:
            nodes = [n.raw for n in nodes if n.raw]
        else:
            nodes = [self.assert_TreeBase(n) for n in nodes] # 保持与初始节点类型一致
        return nodes, it
    
    @property
    def rep_nodes_idx(self) -> List[int]: # 注意是大整数类
        return [node.visit_index for node in self.revisit_nodes]
    
    
class HeapIter(SafeIterBase2[T_LR]):
    """
    沿堆索引路径的安全迭代器，用于 get_heap
    root  必须是 TreeBase 的（后继）类型
    """
    def __init__(self, root: TreeBase[T_LR] | T_LR, heap_index: int):
        super().__init__(root if isinstance(root, TreeBase) else TreeBase(root), early_stop=True)
        self.visit_index = heap_index
        # 将 heap_index 转为左右路径列表：True=右，False=左
        bits = bin(heap_index)[3:]  # 去掉 '0b1'
        self._route = [bit == '1' for bit in bits]

    def _prepare_next(self) -> None:
        if not self._route:
            self._cur_node = TreeBase(None)
            return
        go_right = self._route.pop(0)
        if self._cur_node:
            nxt = self._cur_node.right if go_right else self._cur_node.left
            if nxt and self._check_safe(nxt):
                self._cur_node = nxt
            else:
                self._cur_node = TreeBase(None)

    def copy(self) -> 'HeapIter[T_LR]':
        assert isinstance(self._cur_node,TreeBase), "HeapIter 仅支持 TreeBase 极其后继类型作为 _cur_node"
        return HeapIter(self._cur_node, self.visit_index)

class TreeNodeKitBase(TreeBase[T_LR]):
    """二叉树调试增强工具，提供安全遍历、环检测、美观打印"""

    def get_heap(self, heap_index: int ,allowed_null:bool = False) -> 'TreeNodeKitBase[T_LR]':
        """按堆索引获取节点（从1开始），路径断裂或遇环时抛出 IndexError"""
        if heap_index < 1:
            raise IndexError("堆索引不能小于1")        
        it = HeapIter(self, heap_index)
        node = SafeIterBase2._getitem(it, len(it._route), allowed_null=allowed_null)
        assert isinstance(node, TreeNodeKitBase), f"设计错误：SafeIterBase2._getitem 丢失了节点包装类型的保持状态, 实际类型为 {type(node)}"
        return node

    def __getitem__(self, index: int) -> 'TreeNodeKitBase[T_LR]':
        """按层序遍历顺序索引（从0开始），返回包装节点"""
        it = self.layer_iter(early_stop=False)
        node = SafeIterBase2._getitem(it,index,False)
        assert isinstance(node, TreeNodeKitBase), f"设计错误：SafeIterBase2._getitem 丢失了节点包装类型的保持状态, 实际类型为 {type(node)}"
        return node

    def flatten(self ,early_stop: bool = False, max_depth: int = -1 ,max_len:int = -1)->Tuple[List[TreeNodeKitBase[T_LR]], TreeIter[Self]]:
        """
        层序遍历树，返回 (索引, 原生节点) 列表 和 重复索引列表。
        :param max_depth: 最大深度限制（包含）
        :param early_stop: 遇到重复节点是否停止
        """
        it = TreeIter(self, "LR",  use_queue= True,
                       early_stop=early_stop, max_depth=max_depth)
        nodes = SafeIterBase2._flatten(it,max_len)
        if __DEBUG__:
            cast_nodes = [TreeNodeKitBase(None)] * len(nodes)
            for i,n in enumerate(nodes):
                assert isinstance(n, TreeNodeKitBase), f"设计错误：SafeIterBase2._flatten 丢失了节点包装类型的保持状态, 实际类型为 {type(n)}"
                cast_nodes[i] = n
            return cast_nodes,it
        else:
            return nodes,it  # pyright: ignore[reportReturnType]

    def flatten_raw(self ,early_stop: bool = False, max_depth: int = -1 ,max_len:int = -1)->Tuple[List[T_LR], TreeIter[Self]]:
        """
        层序遍历树，返回 (索引, 原生节点) 列表 和 重复索引列表。
        :param max_depth: 最大深度限制（包含）
        :param early_stop: 遇到重复节点是否停止
        
        """
        nodes,it = self.flatten(early_stop, max_depth,max_len)
        return [node.raw for node in nodes if node.raw],it

    def layer_iter(self, early_stop: bool = False, max_depth: int = -1) -> TreeIter[Self]:
        """层序遍历迭代器 (ULR)"""
        return TreeIter(self, "LR", use_queue= True,
                         early_stop=early_stop, max_depth=max_depth)

    def NLR_iter(self, early_stop: bool = False, max_depth: int = -1) -> TreeIter[Self]:
        """前序遍历迭代器 (NLR) -> 操作字符串 "RLU" """
        return TreeIter(self, "RL",  use_queue= False,
                         early_stop=early_stop, max_depth=max_depth)

    def LNR_iter(self, early_stop: bool = False, max_depth: int = -1) -> TreeIter[Self]:
        """中序遍历迭代器 (LNR) -> 操作字符串 "RCL" """
        return TreeIter(self, "RCL",  use_queue= False,
                         early_stop=early_stop, max_depth=max_depth)

    def LRN_iter(self, early_stop: bool = False, max_depth: int = -1) -> TreeIter[Self]:
        """后序遍历迭代器 (LRN) -> 操作字符串 "CRL" """
        return TreeIter(self, "CRL",  use_queue= False,
                         early_stop=early_stop, max_depth=max_depth)

    def __iter__(self):
        return self.layer_iter()

    @classmethod
    def _to_string(
        cls,
        root: 'TreeNodeKitBase[T_LR] | T_LR | None',
        prep_property: str = "val",
        max_depth: int = 10,
        max_node_len: int = -1,
        full_traversal: bool = False
    ) -> str:
        """
        生成树的字符串表示（树形图 + 索引映射）。
        :param root: 根节点（包装或原生）
        :param prep_property: 取值属性名，如 'val'
        :param max_depth: 最大显示深度
        :param max_node_len: 最多显示节点数（-1无限制）
        :param full_traversal: True则遍历所有节点（跳过重复），False则遇重复停止
        """
        # 因为 _to_string 是类方法，不能依赖 TreeNodeKitBase 对象，最低只需依赖基类 TreeBase
        node:TreeBase = root if isinstance(root, TreeBase) else TreeBase(root)
        if not node:
            return "<class 'TreeNodeKit'>: empty"

        kit_nodes, it_res = TreeIter(
            node, "ULR", use_queue = True,
            early_stop=not full_traversal,
            max_depth=max_depth
        ).flatten(max_len=max_node_len, raw=False)

        # 构建重复索引标注
        repeat_mark = {}
        for i,(p,kn) in enumerate(it_res._revisit):
            if i == p: # 是重复节点
                repeat_mark[kn.visit_index] = f"*{kn.visit_index}"
            elif -1 != p:
                repeat_mark[kn.visit_index] = f"^{it_res._revisit[p][1].visit_index}"
        
        # 收集索引 -> 值
        idx_val = {kn.visit_index: getattr(kn.raw, prep_property) for kn in kit_nodes}

        if not idx_val:
            return "<class 'TreeNodeKit'>: empty"

        max_idx = max(max(idx_val.keys()), max(repeat_mark.keys()) if repeat_mark else 0)
        # 构建层序列表用于 binarytree
        level_list = [""] * max_idx
        for idx, val in idx_val.items():
            level_list[idx - 1] = str(idx)
        for idx, mark in repeat_mark.items():
            level_list[idx - 1] = mark

        # 生成树形图
        try:
            from binarytree import build
            bt = build(level_list)
            tree_str = str(bt) if bt else "null"
        except Exception:
            tree_str = "Error: binarytree build failed"

        parts = []
        repeat_idxs = [n.visit_index for n in it_res.revisit_nodes]
        if full_traversal:
            if repeat_idxs:
                parts.append(f'  "warning_duplicate_idx": {repeat_idxs}')
        else:
            if repeat_idxs:
                assert 1 == len(repeat_idxs), "使用了 full_traversal=False, 但发现重复索引数量 > 1"
                parts.append(f'  "stop_by_duplicate_idx": {repeat_idxs[0]}')

        tree_part = '  "tree_by_idx": """{}{}"""'.format(
            tree_str,
            '...\n' if (it_res._depth_exceeded or it_res._cur_node) else ''
        )
        parts.append(tree_part)
        parts.append(f'  "idx:val": {idx_val}')

        body = ",\n".join(parts)
        return f"<class 'TreeNodeKit'>: {{\n{body}\n}}"

