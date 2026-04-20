"""
iter_node_tool.py - 链表调试增强工具（方案二：操作包装节点）
用于 LeetCode 本地自动化测试框架，支持环检测、安全遍历、美观打印。
纯 Python 实现，便于后续转换为 Cython。
"""
__DEBUG__ = True

from typing import (
    Any, Dict, List, Optional, Iterator, Tuple
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

# ===== 模拟 C struct =====
class _RevisitEntry:
    __slots__ = ("uf_index", "node")  # 并查集索引 + PyObject*

    def __init__(self, uf_index, node):
        self.uf_index = uf_index   # int（未来 int32 / int64）
        self.node = node           # PyObject*（Cython中改指针）


# （链表不需要 visit_link，但为了兼容 TreeIterBase 保留接口）
class _VisitLinkEntry:
    __slots__ = ("parent", "bits", "depth")

    def __init__(self, parent, bits, depth):
        self.parent = parent  # int
        self.bits = bits      # uint
        self.depth = depth    # int

class SafeIterBase:
    __slots__ = (
        "_seen",        # dict[node] -> first_index
        "_revisit",     # list[_RevisitEntry]
        "_repeat_num",
    )

    def __init__(self):
        self._seen = {}        # Dict[PyObject*, int]
        self._revisit: List[_RevisitEntry] = []     # vector<_RevisitEntry>
        self._repeat_num: int = 0 # 重复节点数量

    @property
    def repeat_num(self):
        return self._repeat_num
    
    # ===== 核心：重复检测 =====
    def _check_safe(self, node)->bool:
        """
        返回：
            idx: 当前节点在 _revisit 中的位置
            is_repeat: 是否重复
        """

        if node is None: return False
        if node in self._seen:
            first_idx = self._seen[node] # 首次出现在 _revisit 的索引

            # 当前节点归于 first_idx 的重复集合
            self._revisit.append(_RevisitEntry(first_idx, node))
            if -1 == self._revisit[first_idx].uf_index: # 若首次记录为重复访问节点，需更新并查索引为 uf_index
                self._revisit[first_idx].uf_index = first_idx
                self._repeat_num += 1

            return False

        else:
            self._seen[node] = len(self._revisit)
            self._revisit.append(_RevisitEntry(-1, node)) # 以 -1 表示无重复时不指向集合
            return True

    @classmethod
    def _flatten(cls, it: Self, max_len: int = -1) -> List[Any]:
        """
        用安全遍历器展开并返回节点序列。
        默认 max_len = -1，则不会限制展开节点数量（Cython 化后可用 unsinged(-1) 表示无穷大）
        """
        if 0==max_len: return []
        nodes: List[Any] = [] # 若 Cython 化，可以设置 max_len（非负时）为最大容量
        for cur_len,node in enumerate(it,1): 
            nodes.append(node)
            if cur_len == max_len: # cur_len 是逐一递增的，若 max_len 为正，则必能生效
                break
        return nodes
    
    # ===== get_next =====
    @classmethod
    def _get_next(cls,it: Self, index: int ,allowed_null:bool= True , early_stop = True) -> Any:
        """
        根据索引获取节点。
        - 如果索引>=有效节点数量，当 allowed_null 为假则抛出 IndexError，否则为真则返回 包装类的 None 节点
        - 如果中途遇到重复节点，仅当 early_stop 为真时抛出 IndexError，否则将跳过重复节点（重复节点不计入有效节点数）
        - 其余情况按 iterator 的遍历次序返回节点
        """
        if index < 0:
            raise IndexError("Negative index not supported")

        i = -1
        for i,node in enumerate(it):
            if i == index:
                return node
            
        # 如果迭代因环而停止，抛出异常
        if early_stop and it.repeat_num > 0:
            raise IndexError(f"Repeated reference detected by index: {it.revisit_nodes[0].uf_index}.")

        # 索引超出范围，若允许 allowed_null 返回空节点
        if allowed_null:
            return None
        else: # 否则报错
            raise IndexError(f"Index: {index} out of range")

    if __DEBUG__: # 方便编程不报警告所用
        def __iter__(self):
            return self
        def __next__(self):
            raise NotImplementedError

    @property
    def revisit_nodes(self) -> List[_RevisitEntry]:
        """返回所有重复访问的节点（按发现顺序）"""
        return [rv_n for i,rv_n in enumerate(self._revisit) if i==rv_n.uf_index]
        
# ===============================
# KitBase（轻量代理）
# ===============================
class KitBase:
    """
    调试增强基类（代理模式）
    """
    def __init__(self, node: KitBase|Any):
        object.__setattr__(self, '_node', KitBase.unwrap(node))

    def __bool__(self) -> bool:
        return self.raw is not None

    @classmethod
    def unwrap(cls, other: 'KitBase|Any'):
        """
        提取包装类内部的原始节点。
        - 如果 other 是 KitBase2 子类实例，返回其内部 _node。
        - 否则直接返回 other 本身（可能为 None）。
        """
        if isinstance(other, KitBase):
            return other.raw
        return other

    @property
    def raw(self):
        """直接访问原生节点"""
        node = object.__getattribute__(self, '_node')
        assert not hasattr(node,'_node'), "Node has been wrapped twice!"
        return node

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

        setattr(node, name, KitBase.unwrap(value))

    def __eq__(self, other: Any) -> bool:
        """比较两个包装节点是否包装同一个原生节点"""
        if not isinstance(other,KitBase): return False
        return self.raw is other.raw

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)
    

# ===============================
# LinkIterBase
# ===============================
class LinkIterBase(SafeIterBase):
    __slots__ = (
        "_cur",        # 当前节点（PyObject*）
        "_head",       # 初始节点（兼容 reset）
        "_allowed_null",
    )

    def __init__(self, head: KitBase|Any , allowed_null = True):
        super().__init__()
        self._head = KitBase.unwrap(head) if isinstance(head,KitBase) else head # 注意提纯为原生节点
        self._cur = self._head
        self._allowed_null = allowed_null
        self._check_safe(self._head) # 易错！必须将起点执行查重

    # ===== 迭代 =====
    def __iter__(self):
        return self

    def __next__(self): # 必须遵循标准3步走
        # 1. 判空则停
        if not self._cur:
            raise StopIteration
        res = self._cur
        # 2. 准备下一节点（需查重）
        next_node = self._cur.next
        if self._check_safe(next_node):
            self._cur = next_node
        else: # 链表务必早停：一旦检测到重复节点就停止（环已出现）
            self._cur = None
        # 3. 返回：注意 res 是有效结果，触发早停的是 res 的后继节点，因此不能在此 StopIteration，而应修改为空节点，待下一轮迭代 StopIteration
        return res
    
    @property
    def circle_index(self) -> int:
        """获取当前迭代器的环节点索引，若无则返回 -1"""
        if self.repeat_num > 0:
            assert 1 == self.repeat_num, f"链表重复索引理论上不可能超过一次，而实际重复索引数量={self.repeat_num}，可能是被非法重置初始节点，重复迭代。"
            return self.revisit_nodes[0].uf_index 
        return -1

    def get_next(self, iter_times: int):
        """
        迭代 iter_times 次并返回该元素
        注意会改变 self 对象！
        """
        return SafeIterBase._get_next( self, iter_times, self._allowed_null )
    
    def iter_flatten_raw(self, max_len: int = -1)-> List[Any]:
        return SafeIterBase._flatten(self, max_len=max_len)
    
class LinkIterKit(KitBase):
    
    def __init__(self, node: KitBase | Any , allowed_null =  True):
        super().__init__(node)
        # self._allowed_null = allowed_null
        object.__setattr__(self, '_allowed_null', allowed_null) # 若改为 cdef 可在 cinit 中执行


    def __iter__(self):
        return LinkIterBase(self._node,self._allowed_null)

    @property
    def next(self)->'LinkIterKit':
        node = self.raw
        if node is None:
            raise AttributeError("Empty node has no 'next' attribute")
        
        # 关键：返回当前类的实例，保持装饰器效果延续
        return self.__class__(node = node.next)
    
    @next.setter
    def next(self, value) -> None:
        node = self.raw # 提取原生节点
        if node is None:
            raise AttributeError("Empty node has no 'next' attribute")
        node.next = self.unwrap(value) # 对原生节点赋值需要去包装
        
    # ===== flatten =====
    def flatten(self)->List[Any]:
        """
        安全展开链表，返回节点列表
        """
        return LinkIterBase(self.raw).iter_flatten_raw()

    def flatten_stopIDX(self: KitBase|Any, max_len= -1)->Tuple[List[Any],int]:
        """
        安全展开链表，返回节点列表和停止索引。当 max_len 为非负值时，则限制输出的长度不大于 max_len。
        :params max_len:
        raw ...
        :return nodes 注意会受到    
        self._early_stop 影响，为真时会跳过重复节点继续展开，为假时遇到重复节点就会停止收集和...
        stop_index < len(nodes) 说明包含重复节点，其下标为 stop_index， 若 因为 max_len 而停止，stop_index = max_len ，否则 stop_index = -1 （包含有效节点恰好为 max_len 个的情况）
        """
        it = LinkIterBase(self)
        nodes = SafeIterBase._flatten(it, max_len=max_len)
        return nodes, it.circle_index if it._cur is None else max_len # 若 cur 非空说明是因为 max_len 截止

    # ===== getitem =====
    def __getitem__(self, idx):
        """
        根据索引获取节点。
        - 如果索引越界且 allowed_null=True，返回 None
        - 如果遇到环且未达到索引，根据 allowed_null 返回 None 或抛出 IndexError
        """
        return LinkIterKit(iter(self).get_next(idx),self._allowed_null)
    
    @classmethod
    def _to_string(cls, head: KitBase|Any, prep_property: str = "val" , max_len:int = -1) -> str:
        """安全打印链表，自动标记环（> 和 ^）"""
        # 注意要用 unwrap 去包装节点
        nodes, stop_index = LinkIterKit(head).flatten_stopIDX( max_len = max_len)       

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
        