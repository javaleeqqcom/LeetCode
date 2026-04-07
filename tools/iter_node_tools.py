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


T_Node = TypeVar("T_Node")

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
        return id(self.raw)

    def __eq__(self, other: Any) -> bool:
        """比较两个包装节点是否包装同一个原生节点"""
        other_raw = KitBase2.unwrap(other)
        return self.raw is other_raw

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

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
        self._seen: Dict[KitBase2[T_Node], List[KitBase2[T_Node]]] = {}
        self._revisit: List[KitBase2[T_Node]] = []
        self._cur_node: KitBase2[T_Node] = node if isinstance(node,KitBase2) else KitBase2(node) # 必须代入包装类节点
        self._early_stop = early_stop

        if node:
            self._seen[node] = [node]

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
            if cur_len == max_len: # i 是逐一递增的，若 max_len 非负，则必能生效
                break
        return nodes
        
    @classmethod
    def _to_raw_list(cls, kit_nodes: List[KitBase2[T_Node]]) -> List[T_Node]:
        res = [node.raw for node in kit_nodes if node.raw] # 返回原始值
        assert len(res) == len(kit_nodes), "Empty node found during unwrapping, design error or data corrupted!"
        return res

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
        self.allowed_null = getitem_null_end

    def _prepare_next(self) -> None:
        """移动到下一个节点，自动包装，并进行环检测。"""
        if self._cur_node:
            self._cur_node = self._cur_node.next
            self._check_safe(self._cur_node) # 不安全会自动触发早停，无需置 None

    @property
    def circle_index(self) -> int:
        """获取当前迭代器的环节点索引，若无则返回 -1"""
        if self.revisit_nodes:
            assert 1 == len(self.revisit_nodes), f"链表重复索引理论上不可能超过一次，而实际重复索引数量={len(self.revisit_nodes)}，可能是被非法重置初始节点，重复迭代。"
            return cast(ListNodeKitBase,self.revisit_nodes[0]).visit_index 
        return -1

    def copy(self,reset_index = False) -> Self:
        """注意默认 reset_index=False，即默认不重置索引值"""
        node = ListNodeKitBase(self._cur_node) if reset_index else cast(ListNodeKitBase,self._cur_node)
        return self.__class__(node, self.allowed_null)

    def __getitem__(self, index: int) -> ListNodeKitBase[T_NEXT]:
        """
        根据索引获取节点。
        - 如果索引越界且 allowed_null=True，返回 None
        - 如果遇到环且未达到索引，根据 allowed_null 返回 None 或抛出 IndexError
        """
        return cast( ListNodeKitBase, SafeIterBase2._getitem( self.copy(), index, self.allowed_null ))
    
    def __next__(self) -> ListNodeKitBase[T_NEXT]:
        return cast(ListNodeKitBase,super().__next__())
    
    def __iter__(self) -> Iterator[ListNodeKitBase[T_NEXT]]:
        return self

    def flatten(self, max_len: int = -1) -> Tuple[List[KitBase2[T_NEXT]], int]:
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
            raise AttributeError("Empty node has no 'next' attribute")
        
        # 关键：返回当前类的实例，保持装饰器效果延续
        return self.__class__(node.next, self.visit_index + 1)
    
    @next.setter
    def next(self, value) -> None:
        raise NotImplementedError("ListNodeKitBase.next.setter should not be called")
        
    def flatten(self: 'ListNodeKitBase[T_NEXT] | T_NEXT | None', max_len: int = -1) -> Tuple[List[KitBase2[T_NEXT]], int]:
        """展开链表（包装节点类），若 max_len 非负则限制展开节点数量不超过 max_len"""
        return IterNext2[T_NEXT](ListNodeKitBase(self),False).flatten(max_len)
        
    def flatten_raw(self: 'ListNodeKitBase[T_NEXT] | T_NEXT | None', max_len: int = -1) -> Tuple[List[T_NEXT], int]:
        """展开链表（原生节点类），若 max_len 非负则限制展开节点数量不超过 max_len"""
        kit_nodes,stop_index = IterNext2[T_NEXT](ListNodeKitBase(self),False).flatten(max_len)
        return SafeIterBase2._to_raw_list(kit_nodes) , stop_index

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
    

# -------------------------- 待修改的代码 ------------------------------

@runtime_checkable
class HasLR(Protocol):
    left: Optional[Any]
    right: Optional[Any]
# 定义支持 .left , .right 属性的协议（泛型约束）
T_LR = TypeVar("T_LR",bound=HasLR)

class TreeBase(KitBase2[T_LR]):
    def __init__(self, node: KitBase2 | T_LR | None, heap_index: int = 1):
        super().__init__(node)
        self._heap_index = heap_index # 将来 heap_index 需要改造为专用大整数类

    @property
    def visit_index(self)->int: # Cython 用int计算机位数的普通有符号整型即可
        """ 访问节点索引编号，用于标记遍历到该节点的迭代次数 """
        return object.__getattribute__(self, '_visit_index')

    @visit_index.setter
    def visit_index(self)->int: # Cython 用int计算机位数的普通有符号整型即可
        raise AttributeError("访问索引编号是只读")
    
    @property
    def depth(self)->int:
        """用于树深遍历限制"""
        if not self: return 0 # 空树为 0 层
        return len(bin(self.visit_index)) - 2 # 去掉 '0b' 开头的位数

    @property
    def left(self) -> 'TreeBase[T_LR]':
        if self.raw is None:
            raise AttributeError("空树节点不能使用 left 属性")
        # 注意若 depth 改为 usize ，则仅当 depth < uszie 最大值时可后继，否则报错（不过一般的计算机系统的地址既然能容纳节点（节点至少得占用一个字），应该不可能树深超过 usize 最大值的）
        return self.__class__(self.raw.left, self.visit_index * 2)

    @left.setter
    def left(self, value: 'TreeBase[T_LR] | T_LR | None'):
        if self.raw is None:
            raise AttributeError("空树节点不能设置 left 属性")
        self.raw.left = self.unwrap(value)   # 使用 unwrap 简化

    @property
    def right(self) -> 'TreeBase[T_LR]':
        if self.raw is None:
            raise AttributeError("空树节点不能使用 right 属性")
        return self.__class__(self.raw.right, self.visit_index * 2 + 1)

    @right.setter
    def right(self, value: 'TreeBase[T_LR] | T_LR | None'):
        if self.raw is None:
            raise AttributeError("空树节点不能设置 right 属性")
        self.raw.right = self.unwrap(value)

class TreeIter(SafeIterBase2[T_LR]):
    def __init__(self, root: TreeBase[T_LR]|T_LR|None, operation:str, use_queue: bool,  early_stop: bool = False ,max_depth:int = -1):
        super().__init__(TreeBase(None), early_stop)
        # _operation_funs = {
        #     "l": self._push_left,
        #     "r": self._push_right,
        #     "c": self._push_current,
        #     "u": self._update_current
        # }
        self._operation = operation
        # self._operation_funs:Tuple[Callable] = tuple(_operation_funs[c] for c in operation.lower())
        self._instant_updates = "u" in operation.lower()
        self._max_depth = max_depth # self._max_depth == -1 的初始值在 Cython 化后可以改为 usize 的最大值
        self._depth_exceeded = False
        
        if use_queue:
            self._container = deque()
            self._pop = self._container.popleft
        else:
            self._container = list()
            self._pop = self._container.pop

        if self._push(TreeBase(root), False):
            self._prepare_next()

    def _push(self, node: TreeBase[T_LR], status: bool) -> bool:
        assert isinstance(node, TreeBase) , "node must be a KitTree"
        if node: 
            if -1 != self._max_depth and node.depth > self._max_depth:
                # 检测到遍历的节点非空且超出深度限制
                self._depth_exceeded = True
            else:
                self._container.append((node, status))
                return True
        return False
    
    # Cython调用 Python 函数开销很大，不如 ifelse

    # def _push_left(self, node: KitTree[T_LR])->None:
    #     self._push(node.left, False)
    
    # def _push_right(self, node: KitTree[T_LR])->None:
    #     self._push(node.right, False)
    
    # def _push_current(self, node: KitTree[T_LR]) ->None:
    #     self._push(node, True)

    # def _update_current(self, node: KitTree[T_LR]) ->None:
    #     self._cur_node = node
      
    def _prepare_next(self) -> None:
        """默认实现：适用于栈容器（DFS）的通用迭代逻辑"""
        while self._container:
            # 弹出栈顶元素，检查是否已安全
            idx, node, checked = self._pop()
            if checked: # 检查过已安全，设置为当前节点
                self._update_current(idx, node)
                return
            elif self._check_safe(idx, node): # 未检查过，则进行查重
                for op_fun in self._operation_funs:
                    # op_fun(idx,node)
                    # 改用 ifelse
                if self._instant_updates:
                    return # 已经更新 _current_node，马上返回
            elif self._early_stop: # 不安全（重复）节点，若早停则跳出循环，按无后继处理
                break
        # 无后继
        self._cur_node = None

    def copy(self):
        # 调用 init（root, 是否为队列，是否早停）
        return self.__class__(
            TreeBase(self._cur_node), # 重置 index = 1 
            self._operation, 
            isinstance(self._container, deque),
            early_stop=self._early_stop,
            max_depth = self._max_depth
            )

    def flatten(self, max_len = ... ,raw = ...)->Tuple[List[Any],Self]:  # Any 需要替代更精细
        # max_len 是限制输出数组的最大长度，与 max_depth 成与关系
        # max_depth 已经在初始化时定义了，由迭代器内部判断
        it = self.copy()
        nodes = SafeIterBase2._flatten(it, max_len)
        return (SafeIterBase2._to_raw_list(nodes) if raw else nodes) , it

class HeapIter(SafeIterBase2):
    """仅防止堆索引路由过程中重复访问祖先节点的错误"""
    def __init__(self, root: TreeBase[T_LR]|T_LR, heap_index: int):
        super().__init__(TreeBase(root),True) # 必须用 KitTree 将 visit_index 重置为 1，堆索引访问只有一条链路，等价于链表，因此必须使用早停避免重复节点输出。
        self._heap_index = heap_index # 用于还原堆索引的路径操作列表
        # 將 '101' 轉為 [False, True] (0=左, 1=右)
        self.route_ops = [op == '1' for op in bin(heap_index)[3:]]

    def _prepare_next(self):
        if not self.route_ops:
            self._cur_node = TreeBase(None) # 索引已经用完，返回空
            return

        is_right = self.route_ops.pop(0)
        
        if self._cur_node:
            next_node:TreeBase = getattr(self._cur_node, 'right' if is_right else 'left', None)

            # 恰好是最後一跳到達空節點，允許更新，但如果後面還有指令則會中斷
            if not self._check_safe( next_node ):
                self._cur_node = next_node
            # early_stop=True 会将 self._cur_node = None

    def copy(self):
        # 调用 init（root, 是否为队列，是否早停）
        return self.__class__(
            TreeBase(self._cur_node), # 重置 index = 1 
            heap_index = self._heap_index
            )

class TreeNodeKitBase(TreeBase[T_LR]):
    """
    二叉树调试增强工具基类，使用代理模式。
    提供安全的扁平化（层序遍历）和重复节点检测，避免因错误的树结构导致死循环。
    """

    def get_heap(self, heap_index: int) -> 'TreeNodeKitBase[T_LR]':
        """
        按從1開始的堆索引獲取節點。
        邏輯：
        - 正常路徑：返回該節點的 Kit 包裝。
        - 路徑中途斷裂：拋出 IndexError("堆索引超出範圍")。
        - 遇到重複的祖先節點（環）：由 SafeIterBase 攔截並拋出 IndexError。
        - 注意仅防止堆索引路由过程中重复访问祖先节点的错误，对于树中非祖先路径的重复节点，无法检测到重复节点的错误。
        """
        if heap_index < 1:
            raise IndexError("堆索引不能小於1")
        
        # 這裡 early_stop 設為 True，保證一撞環就停止
        raise NotImplemented("未实现")

    def __getitem__(self, index: int) -> 'TreeNodeKitBase[T_LR]':
        """按层序遍历顺序索引，跳过重复节点和空节点，若超出树的有效节点，则报错"""
        it = self.layer_iter(False)
        return cast(TreeNodeKitBase,SafeIterBase2._getitem(it,index,False)) # 不能用 TreeNodeKitBase.__init__ 否则会丢失 visit_index
    
    def flatten(self,max_depth:int|None = None ,early_stop:bool=False) -> Tuple[List[Tuple[int, T_LR]], List[int]]:
        """层序遍历树，返回 (<完全二叉树索引键，节点>列表, 重复节点的索引列表)。"""
        # 同理调用 SafeIterBase2

    def layer_iter(self,early_stop:bool=False) -> TreeIter[T_LR]:
        """调用 SafeIter 安全地层序遍历，遍历完毕或出现重复节点时停止"""
        return TreeIter(self.raw, "ULR", True, early_stop=early_stop)
    
    def NLR_iter(self, early_stop:bool=False) -> TreeIter[T_LR]:
        """前序遍历迭代器 (NLR)"""
        return TreeIter(self.raw, "RLU", False, early_stop=early_stop)

    def LNR_iter(self, early_stop:bool=False) -> TreeIter[T_LR]:
        """中序遍历迭代器 (LNR)"""
        return TreeIter(self.raw, "RCL", False, early_stop=early_stop)

    def LRN_iter(self, early_stop:bool=False) -> TreeIter[T_LR]:
        """后序遍历迭代器 (LRN)"""
        return TreeIter(self.raw, "CRL", False, early_stop=early_stop)
    
    def __iter__(self):
        """默认返回层序遍历迭代器"""
        return self.layer_iter()
    
    @classmethod
    def _to_string(cls, root: TreeNodeKitBase[T_LR] | T_LR | None,
                  prep_property: str = "val", max_depth: int = 10,
                  max_node_len: int = -1,
                  full_traversal: bool = False) -> str:
        """
        生成树的字符串表示，包含：
        - 树形结构（使用 binarytree 库）
        - 完全二叉树索引与节点值的映射
        - 重复节点键（若存在环）

        Args:
            root: 根节点
            prep_property: 节点取值属性名
            max_depth: 最大深度
            full_traversal: 是否完整遍历所有节点（跳过重复节点），并展示所有非法链接。
                           若为 False，则遇到第一个重复节点即停止。
        """
        node: Optional[T_LR] = cls.unwrap(root)
        if node is None:
            return "<class 'TreeNodeKit'>: empty"

        # 收集所有可达节点和索引
        kit_nodes,it_res = TreeIter(node, "ULR", True, early_stop = not full_traversal,max_depth=max_depth).flatten(max_node_len,False)
        repeat_idx_dict = {}
        for repete_node in it_res.revisit_nodes:
            revisit_index = [node.visit_index for node in it_res.seen_nodes_dict[repete_node]]
            first_idx = revisit_index[0]
            repeat_idx_dict[first_idx] = f"*{first_idx.visit_index}"
            for dup_idx in revisit_index[1:]:
                if dup_idx not in repeat_idx_dict:
                    repeat_idx_dict[dup_idx] = f"^{first_idx}"

        # 构建索引到节点值的映射
        idx_val = {kn.visit_index: getattr(kn.raw, prep_property) for kn in kit_nodes}

        idx_max = max(chain(idx_val.keys(),repeat_idx_dict.keys()))
        print_size = idx_max
        print_bit_map = [None] * print_size   # 索引从 1 开始，列表长度为 max_idx'

        for idx in idx_val.keys():
            if idx <= print_size:
                print_bit_map[idx-1] = str(idx)
            
        for idx,s in repeat_idx_dict.items():
            if idx <= print_size:
                print_bit_map[idx-1] = s
        
        # 构建用于 binarytree.build 的层序列表
        try:
            bt = build(print_bit_map)
            tree_str = str(bt) if bt else "null"
        except Exception:
            tree_str = "Error: binarytree build failed"

        # 构建输出部分
        parts = []
        repeat_indices = [node.visit_index for node in it_res.revisit_nodes]
        if full_traversal:
            if repeat_indices:
                parts.append(f'  "warning_duplicate_idx": {repeat_indices}')
        else:
            # assert 1 == len(repeat_idxs),"使用了早停，理应只有1个重复索引" # 无法通过验证
            if repeat_indices:
                parts.append(f'  "stop_by_duplicate_idx": {repeat_indices}')

        tree_part = '  "tree_by_idx": """{}{}"""'.format(
            tree_str,
            '...\n' if (it_res._depth_exceeded or it_res._cur_node) else '' 
        )
        parts.append(tree_part)
        parts.append(f'  "idx:val": {idx_val}')

        body = ",\n".join(parts)
        return f"<class 'TreeNodeKit'>: {{\n{body}\n}}"
    