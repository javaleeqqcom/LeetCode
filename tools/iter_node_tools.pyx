# distutils: language = c++

from libcpp.vector cimport vector
from libcpp.deque cimport deque
from libcpp.unordered_map cimport unordered_map
from libcpp.utility cimport pair
from cpython.object cimport PyObject

ctypedef PyObject* PyObjPtr

__DEBUG__ = True

from typing import (
    Any, Dict, List, Optional, Iterator, Tuple, TypeVar, Generic, Protocol, Hashable,
    cast, runtime_checkable
)
from collections import deque as pydeque
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


# ---------- KitBase3 ----------
cdef class KitBase3:
    """
    调试增强基类（代理模式），扩展支持哈希和索引存储。
    """
    cdef public object raw   # ✅ 必须声明

    def __cinit__(self):
        self.raw = None

    def __init__(self, node=None, visit_index=0):
        if isinstance(node, KitBase3):
            self.raw = (<KitBase3>node).raw
        else:
            self.raw = node
        # visit_index 在基类中未使用，子类可能会用到

    def __bool__(self):
        return self.raw is not None

    @classmethod
    def unwrap(cls, other: 'KitBase3 | Hashable | None') -> Optional[Hashable]:
        """
        提取包装类内部的原始节点。
        - 如果 other 是 KitBase3 子类实例，返回其内部 _node。
        - 否则直接返回 other 本身（可能为 None）。
        """
        if isinstance(other, KitBase3):
            return other.raw
        return other

    @property
    def visit_index(self) -> Any:
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

        setattr(node, name, KitBase3.unwrap(value))

    def __eq__(self, other: Any) -> bool:
        """比较两个包装节点是否包装同一个原生节点，并且 visit_index 相同"""
        if not isinstance(other, KitBase3):
            return False
        return self.raw is other.raw and self.visit_index == other.visit_index

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        vid = self.visit_index
        return "<%s>{%s, %s}" % (
            str(self.__class__),
            "raw.id: 0x{id(self.raw):x}" if self.raw else "raw: None",
            "visit.id: " + (f"0x{vid:x}" if vid and vid >= 2**16 else str(vid))
        )


# ---------- SafeIterBase3 ----------
ctypedef pair[PyObjPtr, bint] NodePair

cdef class SafeIterBase3:
    """
    安全迭代器基类（方案二版本）
    - 操作包装节点（KitBase3 实例）
    - 环检测使用包装节点的哈希（基于原生节点内存地址）
    - 子类需实现 _prepare_next()
    """
    cdef:
        KitBase3 _cur_node
        readonly bint _early_stop

        unordered_map[Py_ssize_t, Py_ssize_t] _seen
        vector[pair[Py_ssize_t, PyObjPtr]] _revisit

        Py_ssize_t _repeat_num

    def __cinit__(self):
        self._cur_node = KitBase3()          # 空占位
        self._early_stop = False
        self._repeat_num = 0

    def __init__(self, node, bint early_stop=False):
        # 1️⃣ 确定包装类型和当前节点
        if isinstance(node, KitBase3):
            # 保留完整包装对象（包括子类类型）
            self._cur_node = node
        elif node is not None:
            # 原生节点 -> 使用默认包装类（通常是 KitBase3，子类需自行重写）
            self._cur_node = KitBase3(node)
        else:
            self._cur_node = KitBase3(None)

        self._early_stop = early_stop

        # 2️⃣ 初始化环检测结构（基于原始节点内存地址）
        cdef Py_ssize_t rid
        if self._cur_node and self._cur_node.raw is not None:
            rid = <Py_ssize_t>id(self._cur_node.raw)
            self._seen[rid] = <Py_ssize_t>0
            self._revisit.push_back(pair[Py_ssize_t, PyObjPtr](-1, <PyObjPtr>self._cur_node))

    @property
    def repeat_num(self):
        return self._repeat_num

    @property
    def cur(self):
        return self._cur_node

    def index_revisit_visit(self)->List[Tuple[int,int,int]]:
        """返回所有涉及重复访问的节点（访问索引，重复索引，包装节点）"""
        cdef Py_ssize_t i, n = self._revisit.size()
        cdef list result = []

        for i in range(n):
            if self._revisit[i].first == i:
                result.append((i, self._revisit[i].first, (<KitBase3>self._revisit[i].second).visit_index ))

        return result

    @cur.setter
    def cur(self, node):
        assert isinstance(node,KitBase3)
        self._cur_node = node

    @classmethod
    def _getitem(cls, it: Self, index: int, allowed_null: bool = False) -> KitBase3:
        """
        根据索引获取节点。
        - 如果索引>=有效节点数量，当 allowed_null 为假则抛出 IndexError，否则为真则返回 包装类的 None 节点
        - 如果中途遇到重复节点，仅当 it._early_stop 为真时抛出 IndexError，否则将跳过重复节点（重复节点不计入有效节点数）
        - 其余情况按 iterator 的遍历次序返回节点
        """
        if index < 0:
            raise IndexError("Negative index not supported")

        i = -1
        for i, node in enumerate(it):
            if i == index:
                return node

        # 如果迭代因环而停止，抛出异常
        if it._early_stop and it.revisit_nodes:
            raise IndexError(f"Repeated reference detected by index: {it.revisit_nodes[0].visit_index}.")

        # 索引超出范围，若允许 allowed_null 返回空节点
        if allowed_null:
            return it.cur.__class__(None)  # ✅ 保持子类类型
        else:  # 否则报错
            raise IndexError(f"Index: {index} out of range")

    cdef bint _check_safe(self, KitBase3 node):
        if not node or node.raw is None:
            return False

        cdef Py_ssize_t rid = <Py_ssize_t>id(node.raw)

        cdef Py_ssize_t has_key = self._seen.count(rid)  # 先把結果存入變數
        if has_key > 0:
            rv_idx = self._seen[rid]
            self._revisit.push_back(pair[Py_ssize_t, PyObjPtr](rv_idx, <PyObjPtr>node))

            if self._revisit[rv_idx].first == -1:
                self._revisit[rv_idx].first = rv_idx
                self._repeat_num += 1
            return False
        else:
            rv_idx = <Py_ssize_t>self._revisit.size()
            self._seen[rid] = <Py_ssize_t>rv_idx
            self._revisit.push_back(pair[Py_ssize_t, PyObjPtr](-1, <PyObjPtr>node))
            return True

    @classmethod
    def _flatten(cls, it: SafeIterBase3, max_len: int = -1) -> List[KitBase3]:
        """
        安全展开链表，返回包装节点列表。
        默认 max_len = -1，则不会限制展开节点数量
        """
        if max_len == 0:
            return []
        nodes: List[KitBase3] = []  # 若 Cython 化，可以设置 max_len（非负时）为最大容量
        for cur_len, node in enumerate(it, 1):
            nodes.append(node)
            if cur_len == max_len:  # cur_len 是逐一递增的，若 max_len 为正，则必能生效
                break
        return nodes

    def __iter__(self) -> Iterator[KitBase3]:
        return self

    def __next__(self):
        if not self._cur_node or self._cur_node.raw is None:
            raise StopIteration

        result = self._cur_node
        self._prepare_next()

        if self._early_stop and self._repeat_num > 0:
            self._cur_node = KitBase3(None)

        return result

    cpdef void _prepare_next(self):
        raise NotImplementedError

    @property
    def revisit_nodes(self) -> List[KitBase3]:
        """返回所有重复访问的节点（按发现顺序）"""
        cdef Py_ssize_t i, n = self._revisit.size()
        cdef list result = []

        for i in range(n):
            if self._revisit[i].first == i:
                result.append(<KitBase3>self._revisit[i].second)

        return result


# 定义原生节点协议（必须包含 .next 属性）
@runtime_checkable
class HasNext(Protocol):
    next: Optional[Any]


# ---------- IterNext2 ----------
cdef class IterNext2(SafeIterBase3):
    """
    链表安全迭代器，继承 SafeIterBase3 实现环检测，自动包装原生节点。
    支持 __getitem__ 和 flatten 方法。
    """
    cdef bint allowed_null

    def __cinit__(self):
        self.allowed_null = False

    def __init__(self, head: ListNodeKitBase, getitem_null_end: bool = False):
        """
        Args:
            head: 链表头节点（包装类实例）
            getitem_null_end: __getitem__ 风格索引越界时返回 None（True）或抛出 IndexError（False）
        """
        assert isinstance(head, ListNodeKitBase), f"head must be type of ListNodeKitBase, but {type(head)}"
        super().__init__(node=head, early_stop=True)  # 链表不支持跳过，故早停为 True
        self.allowed_null = getitem_null_end

    cpdef void _prepare_next(self):
        """移动到下一个节点，自动包装，并进行环检测。"""
        if self.cur:
            self.cur = self.cur.next
            self._check_safe(self.cur)  # 不安全会自动触发早停，无需置 None

    @property
    def circle_index(self) -> int:
        """获取当前迭代器的环节点索引，若无则返回 -1"""
        if self.repeat_num > 0:
            assert 1 == self.repeat_num, f"链表重复索引理论上不可能超过一次，而实际重复索引数量={self.repeat_num}，可能是被非法重置初始节点，重复迭代。"
            return self.revisit_nodes[0].visit_index
        return -1

    def copy(self, reset_index=False) -> IterNext2:
        """注意默认 reset_index=False，即默认不重置索引值"""
        assert isinstance(self.cur, ListNodeKitBase), f"IterNext2.cur must be type of ListNodeKitBase, but got {type(self.cur)}"
        node = self.cur.__class__(self.cur.raw, 0 if reset_index else self.cur.visit_index)

        return IterNext2(node, self.allowed_null)

    def __getitem__(self, index: int) -> ListNodeKitBase:
        """
        根据索引获取节点。
        - 如果索引越界且 allowed_null=True，返回 None
        - 如果遇到环且未达到索引，根据 allowed_null 返回 None 或抛出 IndexError
        """
        return cast(ListNodeKitBase,
                    self.cur.__class__(SafeIterBase3._getitem(self.copy(), index, self.allowed_null))
                    )

    def flatten(self, max_len: int = -1) -> Tuple[List[ListNodeKitBase], int]:
        """
        安全展开链表，返回节点列表和停止索引。当 max_len 为非负值时，则限制输出的长度不大于 max_len。
        :params max_len:
        raw ...
        :return nodes 注意会受到    
        self._early_stop 影响，为真时会跳过重复节点继续展开，为假时遇到重复节点就会停止收集和...
        stop_index < len(nodes) 说明包含重复节点，其下标为 stop_index， 若 因为 max_len 而停止，stop_index = max_len ，否则 stop_index = -1 （包含有效节点恰好为 max_len 个的情况）
        """
        it = self.copy()
        nodes = SafeIterBase3._flatten(it, max_len=max_len)

        stop_index = it.circle_index  # 检测到环，则以环节点索引为停止索引

        if -1 == stop_index and it.cur:  # 未检测到环，但是迭代器没有迭代到空节点
            stop_index = len(nodes)  # 说明迭代器因 max_len 限制而停止
        return nodes, stop_index


cdef class ListNodeKitBase(KitBase3):
    cdef:
        Py_ssize_t _visit_index
    """ 调试增强工具，使用代理模式（安全实现） 用法: link = ListNodeKit(head_node) """

    def __cinit__(self):
        self._visit_index = 0

    def __init__(self, node: KitBase3 | HasNext | None = None, visit_index: int|Py_ssize_t = 0):
        super().__init__(node)
        self._visit_index = <Py_ssize_t>visit_index

    @property
    def visit_index(self) -> Py_ssize_t:  # Cython 用int计算机位数的普通有符号整型即可
        """ 访问节点索引编号，用于标记遍历到该节点的迭代次数 """
        return self._visit_index

    @visit_index.setter
    def visit_index(self, Py_ssize_t new_index):  # Cython 用int计算机位数的普通有符号整型即可
        """ 访问节点索引编号，用于标记遍历到该节点的迭代次数 """
        self._visit_index = new_index

    @property
    def next(self) -> 'ListNodeKitBase':
        node = self.raw
        if node is None:
            raise AttributeError("Empty node has no 'next' attribute")

        # 关键：返回当前类的实例，保持装饰器效果延续
        cdef res = self.__class__()
        res.raw = node.next
        res.visit_index = self.visit_index + 1
        return res

    @next.setter
    def next(self, value) -> None:
        node = self.raw  # 提取原生节点
        if node is None:
            raise AttributeError("Empty node has no 'next' attribute")
        node.next = self.unwrap(value)  # 对原生节点赋值需要去包装

    def flatten(self: 'ListNodeKitBase | HasNext | None', max_len: int = -1) -> Tuple[List[ListNodeKitBase], int]:
        """展开链表（包装节点类），若 max_len 非负则限制展开节点数量不超过 max_len"""
        return IterNext2(ListNodeKitBase(self), False).flatten(max_len)

    def flatten_raw(self: 'ListNodeKitBase | HasNext | None', max_len: int = -1) -> Tuple[List[HasNext], int]:
        """展开链表（原生节点类），若 max_len 非负则限制展开节点数量不超过 max_len"""
        kit_nodes, stop_index = IterNext2(ListNodeKitBase(self), False).flatten(max_len)
        return [node.raw for node in kit_nodes if node.raw], stop_index

    def __iter__(self) -> IterNext2:
        """返回安全链表迭代器"""
        return IterNext2(ListNodeKitBase(self, visit_index=0), False)  # 注意不能用 self 代替 ListNodeKitBase(self)，因为要重置 visit_index

    def __getitem__(self, key) -> ListNodeKitBase:
        """根据索引获取链表节点，返回的是 ListNodeKitBase 包装类对象，允许最后一个节点恰为空节点返回，但若中途遇到重复节点或空节点则抛出异常"""
        return ListNodeKitBase(IterNext2(ListNodeKitBase(self, 0), True)[key])  # 用 ListNodeKitBase 同理（见 __iter__）

    @classmethod
    def _to_string(cls, head: ListNodeKitBase | HasNext | None, prep_property: str = "val", max_len: int = -1) -> str:
        """安全打印链表，自动标记环（> 和 ^）"""
        # 注意要用 unwrap 去包装节点
        nodes, stop_index = (head if isinstance(head, ListNodeKitBase) else ListNodeKitBase(head)).flatten(max_len=max_len)

        str_lst = []

        # 环之前的节点（若无环则全部节点）
        for i in range(stop_index if -1 != stop_index else len(nodes)):
            try:
                str_lst.append(_formatted_string(getattr(nodes[i], prep_property)))
            except:
                raise Exception(f"len(nodes)={len(nodes)}, stop_index={stop_index}, node={nodes[-1]}")

        # 有异常终止索引
        if stop_index >= 0:
            if stop_index == len(nodes):
                str_lst.append("...")  # 说明链表长度超过最大限制，截断打印

            else:  # 说明检测到链表环
                str_lst.append(">")

                # 环之后的节点
                for i in range(stop_index, len(nodes)):
                    assert len(nodes) > 0, "len(nodes)==0"
                    str_lst.append(_formatted_string(getattr(nodes[i], prep_property)))

                # 环结束标记
                str_lst.append("^")

        return f"<class 'ListNodeKit'>: [{','.join(str_lst)}]"

# -------------------------- 树的遍历 ------------------------------

cdef enum OpCode:
    OP_L
    OP_R
    OP_C
    OP_U

@runtime_checkable
class HasLR(Protocol):
    left: Optional[Any]
    right: Optional[Any]


cdef class TreeBase(KitBase3):
    cdef:
        vector[NodePair] stack
        deque[NodePair] queue

    """二叉树包装基类，支持堆索引和深度计算"""

    def __cinit__(self):
        pass
        # C++ 容器自动初始化，无需额外操作

    def __init__(self, node: KitBase3 | HasLR | None = None, heap_index: int = 1):
        super().__init__(node)
        object.__setattr__(self, '_heap_index', heap_index)

    @property
    def visit_index(self) -> int:
        """完全二叉树索引（从1开始）"""
        return object.__getattribute__(self, "_heap_index")

    @property
    def depth(self) -> int:
        """节点深度（根深度为1）"""
        if not self.raw:
            return 0
        return self.visit_index.bit_length()

    @property
    def left(self) -> 'TreeBase':
        node = self.raw
        if node is None:
            raise AttributeError("空树节点不能使用 left 属性")
        return self.__class__(node.left if node else None, self.visit_index * 2)

    @left.setter
    def left(self, value: 'TreeBase | HasLR | None'):
        node = self.raw
        if node is None:
            raise AttributeError("空树节点不能设置 left 属性")
        node.left = self.unwrap(value)

    @property
    def right(self) -> 'TreeBase':
        node = self.raw
        if node is None:
            raise AttributeError("空树节点不能使用 right 属性")
        return self.__class__(node.right if node else None, self.visit_index * 2 + 1)

    @right.setter
    def right(self, value: 'TreeBase | HasLR | None'):
        node = self.raw
        if node is None:
            raise AttributeError("空树节点不能设置 right 属性")
        node.right = self.unwrap(value)


cdef class TreeIter3(SafeIterBase3):
    """二叉树通用迭代器，支持前/中/后/层序遍历，操作字符串驱动"""
    cdef:
        vector[pair[PyObjPtr, bint]] stack
        deque[pair[PyObjPtr, bint]] queue

        bint use_queue
        vector[OpCode] ops
        KitBase3 _root
        str _operation
        int _max_depth

    def __cinit__(self):
        self.use_queue = False
        self._max_depth = -1
        self._root = KitBase3()
        self._operation = ""

    def __init__(self, root, str operation, bint use_queue, bint early_stop=False, int max_depth=-1):
        super().__init__(None, early_stop)
        self.use_queue = use_queue
        self._max_depth = max_depth
        self._root = root  # 保存根节点
        self._operation = operation

        # 预编译 operation
        self.ops.clear()
        for c in operation.lower():
            if c == 'l':
                self.ops.push_back(OP_L)
            elif c == 'r':
                self.ops.push_back(OP_R)
            elif c == 'c':
                self.ops.push_back(OP_C)
            else:
                self.ops.push_back(OP_U)

        if root:
            self._push(root, False)
            self._prepare_next()

    cdef void _push(self, KitBase3 node, bint checked):
        if node is None: return

        cdef NodePair p = pair[PyObjPtr, bint](<PyObjPtr>node, checked)

        if self.use_queue:
            self.queue.push_back(p)
        else:
            self.stack.push_back(p)

    cdef NodePair _pop(self):
        cdef NodePair p

        if self.use_queue:
            p = self.queue.front()
            self.queue.pop_front()
        else:
            p = self.stack.back()
            self.stack.pop_back()

        return p

    cpdef void _prepare_next(self):
        cdef NodePair item
        cdef KitBase3 node
        cdef bint checked

        while True:
            if self.use_queue:
                if self.queue.empty():
                    break
            else:
                if self.stack.empty():
                    break

            item = self._pop()
            node = <KitBase3>item.first
            checked = item.second

            if not checked:
                if self._check_safe(node):
                    for op in self.ops:
                        if op == OP_L:
                            self._push(node.left, False)
                        elif op == OP_R:
                            self._push(node.right, False)
                        else:
                            self._push(node, True)
                    continue
                elif self._early_stop:
                    break
                else:
                    continue

            self.cur = node
            return

        self.cur = KitBase3(None)

    def clone_init(self) -> 'TreeIter3':
        """返回从头开始的新迭代器（用于索引访问）"""
        return TreeIter3(
            self._root,
            self._operation,
            self.use_queue,
            early_stop=self._early_stop,
            max_depth=self._max_depth
        )

    @classmethod
    def assert_TreeBase(cls, node: Any) -> TreeBase:
        assert isinstance(node, TreeBase), "设计错误，传入的节点类型应当保持 TreeBase 类及其继承"
        return node

    def flatten(self, max_len: int = -1, raw: bool = False) -> Tuple[List[TreeBase] | List[HasLR], TreeIter3]:
        """
        展平遍历结果。
        :param max_len: 最大节点数限制，-1表示无限制
        :param raw: 若为True返回原生节点列表，否则返回包装节点列表
        :return: (节点列表, 迭代器自身)
        """
        it = self.clone_init()
        nodes = SafeIterBase3._flatten(it, max_len)
        if raw:
            nodes = [n.raw for n in nodes if n.raw]
        else:
            nodes = [self.assert_TreeBase(n) for n in nodes]  # 保持与初始节点类型一致
        return nodes, it

    @property
    def rep_nodes_idx(self) -> List[int]:  # 注意是大整数类
        return [node.visit_index for node in self.revisit_nodes]


cdef class HeapIter(SafeIterBase3):
    """
    沿堆索引路径的安全迭代器，用于 get_heap
    root  必须是 TreeBase 的（后继）类型
    """
    cdef:
        int visit_index
        list _route

    def __cinit__(self):
        self.visit_index = 0
        self._route = []

    def __init__(self, root: TreeBase, heap_index: int):
        super().__init__(root, early_stop=True)
        assert isinstance(root, TreeBase)
        self.visit_index = heap_index
        # 将 heap_index 转为左右路径列表：True=右，False=左
        bits = bin(heap_index)[3:]  # 去掉 '0b1'
        self._route = [bit == '1' for bit in bits]

    def _prepare_next(self):
        if not self._route:
            self.cur = TreeBase(None)
            return
        go_right = self._route.pop(0)
        if self.cur:
            nxt = self.cur.right if go_right else self.cur.left
            if nxt and self._check_safe(nxt):
                self.cur = nxt
            else:
                self.cur = TreeBase(None)

    def copy(self) -> 'HeapIter':
        assert isinstance(self.cur, TreeBase), "HeapIter 仅支持 TreeBase 极其后继类型作为 cur"
        cdef HeapIter res = HeapIter.__new__(HeapIter)
        res.cur = self.cur
        res.visit_index = self.visit_index
        return res

class TreeNodeKitBase(TreeBase):
    """二叉树调试增强工具，提供安全遍历、环检测、美观打印"""

    def get_heap(self, heap_index: int, allowed_null: bool = False) -> 'TreeNodeKitBase':
        """按堆索引获取节点（从1开始），路径断裂或遇环时抛出 IndexError"""
        if heap_index < 1:
            raise IndexError("堆索引不能小于1")
        it = HeapIter(self, heap_index)
        node = SafeIterBase3._getitem(it, len(it._route), allowed_null=allowed_null)
        assert isinstance(node, TreeNodeKitBase), f"设计错误：SafeIterBase3._getitem 丢失了节点包装类型的保持状态, 实际类型为 {type(node)}"
        return node

    def __getitem__(self, index: int) -> 'TreeNodeKitBase':
        """按层序遍历顺序索引（从0开始），返回包装节点"""
        it = self.layer_iter(early_stop=False)
        node = SafeIterBase3._getitem(it, index, False)
        assert isinstance(node, TreeNodeKitBase), f"设计错误：SafeIterBase3._getitem 丢失了节点包装类型的保持状态, 实际类型为 {type(node)}"
        return node

    def flatten(self, early_stop: bool = False, max_depth: int = -1, max_len: int = -1) -> Tuple[List[TreeNodeKitBase], TreeIter3]:
        """
        层序遍历树，返回 (索引, 原生节点) 列表 和 重复索引列表。
        :param max_depth: 最大深度限制（包含）
        :param early_stop: 遇到重复节点是否停止
        """
        it = TreeIter3(self, "LR", use_queue=True,
                       early_stop=early_stop, max_depth=max_depth)
        nodes = SafeIterBase3._flatten(it, max_len)
        if __DEBUG__:
            cast_nodes = [TreeNodeKitBase(None)] * len(nodes)
            for i, n in enumerate(nodes):
                assert isinstance(n, TreeNodeKitBase), f"设计错误：SafeIterBase3._flatten 丢失了节点包装类型的保持状态, 实际类型为 {type(n)}"
                cast_nodes[i] = n
            return cast_nodes, it
        else:
            return nodes, it  # pyright: ignore[reportReturnType]

    def flatten_raw(self, early_stop: bool = False, max_depth: int = -1, max_len: int = -1) -> Tuple[List[HasLR], TreeIter3]:
        """
        层序遍历树，返回 (索引, 原生节点) 列表 和 重复索引列表。
        :param max_depth: 最大深度限制（包含）
        :param early_stop: 遇到重复节点是否停止
        """
        nodes, it = self.flatten(early_stop, max_depth, max_len)
        return [node.raw for node in nodes if node.raw], it

    def layer_iter(self, early_stop: bool = False, max_depth: int = -1) -> TreeIter3:
        """层序遍历迭代器 (ULR)"""
        return TreeIter3(self, "LR", use_queue=True,
                         early_stop=early_stop, max_depth=max_depth)

    def NLR_iter(self, early_stop: bool = False, max_depth: int = -1) -> TreeIter3:
        """前序遍历迭代器 (NLR) -> 操作字符串 "RLU" """
        return TreeIter3(self, "RL", use_queue=False,
                         early_stop=early_stop, max_depth=max_depth)

    def LNR_iter(self, early_stop: bool = False, max_depth: int = -1) -> TreeIter3:
        """中序遍历迭代器 (LNR) -> 操作字符串 "RCL" """
        return TreeIter3(self, "RCL", use_queue=False,
                         early_stop=early_stop, max_depth=max_depth)

    def LRN_iter(self, early_stop: bool = False, max_depth: int = -1) -> TreeIter3:
        """后序遍历迭代器 (LRN) -> 操作字符串 "CRL" """
        return TreeIter3(self, "CRL", use_queue=False,
                         early_stop=early_stop, max_depth=max_depth)

    def __iter__(self):
        return self.layer_iter()

    @classmethod
    def _to_string(
        cls,
        root: 'TreeNodeKitBase | HasLR | None',
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
        node: TreeBase = root if isinstance(root, TreeBase) else TreeBase(root)
        if not node:
            return "<class 'TreeNodeKit'>: empty"

        kit_nodes, it_res = TreeIter3(
            node, "ULR", use_queue=True,
            early_stop=not full_traversal,
            max_depth=max_depth
        ).flatten(max_len=max_node_len, raw=False)

        # 构建重复索引标注
        repeat_mark = {}
        i_rv_v = it_res.index_revisit_visit()
        for i, p, v in i_rv_v: # 遍历 revisit索引、访问索引、树堆索引
            if i == p:  # 是重复节点
                repeat_mark[v] = f"*{v}"
            elif -1 != p:
                repeat_mark[v] = f"^{i_rv_v[p][2]}"

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
        repeat_idxs = [n.visit_index for _,_,n in it_res.revisit_nodes]
        if full_traversal:
            if repeat_idxs:
                parts.append(f'  "warning_duplicate_idx": {repeat_idxs}')
        else:
            if repeat_idxs:
                assert 1 == len(repeat_idxs), "使用了 full_traversal=False, 但发现重复索引数量 > 1"
                parts.append(f'  "stop_by_duplicate_idx": {repeat_idxs[0]}')

        tree_part = '  "tree_by_idx": """{}{}"""'.format(
            tree_str,
            '...\n' if (it_res._depth_exceeded or it_res.cur) else ''
        )
        parts.append(tree_part)
        parts.append(f'  "idx:val": {idx_val}')

        body = ",\n".join(parts)
        return f"<class 'TreeNodeKit'>: {{\n{body}\n}}"