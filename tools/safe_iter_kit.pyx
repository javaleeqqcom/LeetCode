# distutils: language = c++
# ===============================
# 基础导入
# ===============================
from cpython.ref cimport PyObject
from libcpp.vector cimport vector
from libcpp.deque cimport deque
from libcpp.pair cimport pair

from collections import deque as pydeque
from typing import List,Tuple
from args_parser_tools import _formated_string # _to_string 需要
__DEBUG__ = True
# ===============================
# C struct（核心）
# ===============================
cdef struct RevisitEntry:
    size_t uf_index
    PyObject* node
cdef _is_null(PyObject* ptr):
    if ptr == NULL: # 防御性编程，虽然统一用 None 指针表达空节点，但以防意外判断 NULL
        return True
    obj = <object>ptr
    # ✅ 关键修复：拦住 None
    if obj is None:
        return True
    return False

cdef enum:
    UPP_SIZE = <size_t>(-2) # 区分 size_t 最大值时可取得的上限（若不减2有从 <size_t>-1 溢出变为 0 的死循环风险）
# ===============================
# SafeIterBase
# ===============================
cdef class SafeIterBase:
    cdef:
        dict _seen                 # node -> first_index
        vector[RevisitEntry] _revisit
        int _repeat_num
        PyObject* _cur
        readonly bint _early_stop # 将来改进：做成泛型模板，静态条件
    def __cinit__(self):
        self._seen = {}
        self._repeat_num = 0
        self._cur = <PyObject*>None
        self._early_stop = True
    def __init__(self, bint early_stop=True):
        self._early_stop = early_stop

    @property
    def repeat_num(self):
        return self._repeat_num

    # ===== 核心：重复检测 =====
    cdef size_t _check_safe(self,PyObject* node): # node 必须用 Object 而不能用指针，否则无法让 _seen 自动持有
        """
        检查 node 是否在 _seen 中记录过：
        若已记录过，返回 <size_t>-1；
        否则返回节点在 _revisit 追加的索引值也就是 _seen[node]。
        """
        cdef size_t first_idx
        cdef RevisitEntry entry
        if _is_null(node):
            return <size_t>(-1)
        key = <object>node # 关键！指针 -> PyObj
        if key in self._seen:
            first_idx = self._seen[key]
            entry.uf_index = first_idx
            entry.node = node      # 存储指针，不增加引用计数
            self._revisit.push_back(entry)
            # 标记首次重复
            if <size_t>(-1) == self._revisit[first_idx].uf_index:
                self._revisit[first_idx].uf_index = first_idx
                self._repeat_num += 1
            return <size_t>(-1)
        else:
            first_idx = self._revisit.size()
            self._seen[key] = first_idx # node 通过 _seen 的引用计数维持不在 SafeIterBase 析构前消亡
            entry.uf_index = <size_t>(-1)
            entry.node = node
            self._revisit.push_back(entry)
            if self._revisit.size() >= UPP_SIZE:
                raise RuntimeError("SafeIterBase: Max size exceeded capacity.")
            return first_idx

    # ===== flatten =====
    @staticmethod
    cdef list _flatten(SafeIterBase it, size_t max_len=UPP_SIZE):
        cdef list out = []
        cdef int i = 0
        cdef object node
        for node in it:
            out.append(node)
            i += 1
            if max_len >= 0 and i >= max_len:
                break
        return out
    # ===== get_next =====
    @staticmethod
    cdef object _get_next(SafeIterBase it, Py_ssize_t index, bint allowed_null):
        cdef Py_ssize_t i = 0
        cdef object node
        if index < 0:
            raise IndexError()
        for node in it: # 不用 enumerate 性能更好
            if i == index:
                return node
            i += 1
        # 如果迭代因环而停止，抛出异常
        if it._early_stop and it.repeat_num > 0:
            raise IndexError("Repeated reference detected")
        if allowed_null:
            return None
        else: # 否则报错
            raise IndexError(f"Index: {index} out of range")
    
    def _prepare_next(self):
        """不用检查 self._cur 非空，但需赋值 self._cur 并确保查重安全"""
        raise NotImplementedError("_prepare_next method should be implemented by the SafeIterBase inheritance class.")
    
    def __iter__(self): return self
    def __next__(self):
        cdef PyObject* res
        if _is_null(self._cur):
            raise StopIteration
        res = self._cur
        # 获取 next（Python属性访问）
        self._prepare_next() 
        return <object>res

    @property
    def revisit_nodes(self):
        cdef list result = []
        cdef Py_ssize_t i
        cdef RevisitEntry entry
        # 顯式使用 range，Cython 會優化為 C 循環
        for i in range(self._revisit.size()):
            entry = self._revisit[i]
            if i == <Py_ssize_t>entry.uf_index:
                # 將 PyObject* 轉回 object
                result.append((entry.uf_index,<object>entry.node))
        return result


# ===============================
# KitBase（轻量代理）
# ===============================
cdef class KitBase:
    cdef readonly object raw
    def __cinit__(self):
        self.raw= None
    def __init__(self, object node) -> None:
        self.raw = KitBase.unwrap(node)
    @classmethod
    def unwrap(cls, other):
        """
        提取包装类内部的原始节点。
        - 如果 other 是 KitBase 子类实例，返回其内部 _node。
        - 否则直接返回 other 本身（可能为 None）。
        """
        if isinstance(other, KitBase):
            return other.raw
        return other
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
    def __eq__(self, other) -> bool:
        """比较两个包装节点是否包装同一个原生节点"""
        if not isinstance(other,KitBase): return False
        return self.raw is other.raw
    def __ne__(self, other) -> bool:
        return not self.__eq__(other)
    def __bool__(self) -> bool:
        return self.raw is not None

    def __repr__(self) -> str:
        return KitBase._format_repr(self)

    @staticmethod
    def _format_repr(obj, *attributes, **children):
        """
        统一格式化函数
        :param obj: 当前实例 (self)
        :param attributes: 需要显示的属性名，包含 "id" 则显示地址
        :param children: 子节点对象，如 left=self.left, right=self.right
        """
        # 1. 处理本节点信息
        lines = [line for line in f"self: {obj.raw}".splitlines()]
        
        # 2. 处理子节点
        for key, prop in children.items():
            # 假设 KitBase 在全局作用域，或此处改用通用的 unwrap 逻辑
            prop_raw = KitBase.unwrap(prop) if prop is not None else None
            
            if prop_raw is None:
                lines.append(f"{key}: None")
            else:            
                attr_list = []
                for attr in attributes:
                    if attr == "id":
                        val = f"0x{id(prop_raw):012X}"
                    elif hasattr(prop_raw, attr):
                        val = getattr(prop_raw, attr)
                    else:
                        # 建议用 f-string 报错，并包含 key 信息方便定位
                        raise AttributeError(f"Node '{key}' ({type(prop_raw)}) has no attribute '{attr}'")
                    attr_list.append(f"{attr}: {val}")
                
                # 修正点：子节点属性通常建议在同一行显示，或者增加额外缩进
                # 如果 attributes 很多，可以使用 ", ".join 保持紧凑
                attrs_str = ", ".join(attr_list)
                prop_str = f"{key}: {{<class '{prop_raw.__class__.__name__}'>: {{{attrs_str}}}}}"
                lines.append(prop_str)
                
        # 3. 统一处理换行和缩进
        # 每一行前面都加一个 \t
        body = "\n\t".join(lines)
        
        return f"<class '{obj.__class__.__name__}'>: {{\n\t{body}\n}}"

# ===============================
# LinkIterBase
# ===============================
cdef class LinkIterBase(SafeIterBase):
    def __init__(self, object head):
        super().__init__(early_stop = True) # 链表只支持早停，因为无分支，不可跳过重复节点，否则永远都重复死循环
        head = KitBase.unwrap(head)
        if head is not None:
            self._cur = <PyObject*>head
            # ⚠️ 必须先登记 head
            self._check_safe(self._cur)
    # 覆盖 SafeIterBase 基类
    def _prepare_next(self): # 调用前已确保 self._cur 非空
        next_node = getattr(<object>self._cur, "next") # next_node 必须赋值为 PyObject 类型否则会报错：`Storing unsafe C derivative of temporary Python reference`
        self._cur = <PyObject*>next_node
        # 必须确保早停，__next__ 才会检测重复 _cur 不重复
        if <size_t>(-1) == self._check_safe(self._cur): # 经过 _check_safe 后的 next_node 对象确保了引用计数安全
            self._cur = <PyObject*>None
    @property
    def circle_index(self)->int:
        if self._repeat_num > 0:
            return self.revisit_nodes[0][0]
        return -1
    cpdef object get_next(self, Py_ssize_t index , bint allowed_null):
        return SafeIterBase._get_next(self, index, allowed_null)
    cpdef list iter_flatten_raw(self, size_t max_len=UPP_SIZE):
        return SafeIterBase._flatten(self, max_len)

# ===============================
# LinkIterKit（用户层）
# ===============================
cdef class LinkIterKit(KitBase):
    cdef bint _allowed_null
    def __cinit__(self):
        self._allowed_null = True
    def __init__(self, object head, bint allowed_null=True):
        KitBase.__init__(self, head)
        self._allowed_null = allowed_null
    def __iter__(self):
        return LinkIterBase(self.raw)
    @property
    def next(self)->'LinkIterKit':
        node = self.raw
        if node is None:
            raise AttributeError("Empty node has no 'next' attribute")
        
        # 关键：返回当前类的实例，保持装饰器效果延续
        return self.__class__(head = node.next)
    @next.setter
    def next(self, value) -> None:
        node = self.raw # 提取原生节点
        if node is None:
            raise AttributeError("Empty node has no 'next' attribute")
        node.next = self.unwrap(value) # 对原生节点赋值需要去包装
    # ===== flatten =====
    cpdef list flatten(self):
        cdef LinkIterBase it = LinkIterBase(self.raw)
        return it.iter_flatten_raw()
    # ===== flatten + stop index =====
    def flatten_stopIDX(self, size_t max_len=UPP_SIZE)->Tuple[List, int]:
        cdef LinkIterBase it = LinkIterBase(self.raw) if isinstance(self, LinkIterKit) else LinkIterBase(self)
        cdef list nodes = it.iter_flatten_raw(max_len)
        if _is_null(it._cur):
            return nodes, it.circle_index
        else:
            return nodes, <int>max_len
    # ===== getitem =====
    def __getitem__(self, int idx):
        cdef LinkIterBase it = LinkIterBase(self.raw)
        return LinkIterKit(it.get_next(<Py_ssize_t>idx, self._allowed_null))
    @classmethod
    def _to_string(cls, head, prep_property: str = "val" , size_t max_len=UPP_SIZE) -> str:
        """安全打印链表，自动标记环（> 和 ^）"""
        # 注意要用 unwrap 去包装节点
        nodes, stop_index = LinkIterKit(head).flatten_stopIDX( max_len = max_len)       
        str_lst = []
        
        # 环之前的节点（若无环则全部节点）
        for i in range(stop_index if -1 != stop_index else len(nodes)):
            try:
                str_lst.append(_formated_string(getattr(nodes[i],prep_property)))
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
                    str_lst.append(_formated_string(getattr(nodes[i],prep_property)))
            
                # 环结束标记
                str_lst.append("^")
        return f"<class 'ListNodeKit'>: [{','.join(str_lst)}]"

    # 低级打印，仅显示本节点情况和左右子节点的id
    def __repr__(self) -> str:
        return self._format_repr(self, next=self.next)

# -------------------------- 树的遍历 ------------------------------
from libcpp.deque cimport deque as cpp_deque
from collections import deque as py_deque

cdef extern from "<algorithm>" namespace "std":
    T lower_bound[T](T first, T last, const T& value) nogil

cdef enum OpCode:
    OP_END = 0
    OP_L   = 1
    OP_R   = 2
    OP_C   = 4
    OP_SHIFT = 4
    OP_U   = 0x44444444   # 用于判断是否即时更新

cdef unsigned int str2OpCode(s: str):
    assert len(s) < 4
    cdef unsigned int res = 0
    for c in s.lower()[::-1]:
        res <<= OP_SHIFT
        if c == 'l':
            res |= OP_L
        elif c == 'r':
            res |= OP_R
        elif c == 'c':
            res |= OP_C
        else:
            raise ValueError(f"invalid op: {s}")
    return res

# ctypedef pair[PyObject*, bint] NodeStatus   # (node指针, 是否已检查过)
ctypedef struct NodeStatus:
    PyObject* node
    bint checked


cdef class TreeIterBase(SafeIterBase):
    """
    二叉树通用迭代器，支持前/中/后/层序遍历，通过操作字符串驱动。
    - use_queue=True 使用队列（层序），否则使用栈（深度优先）
    - ops: 操作编码，低4位为第一个操作，依次类推。每个操作可以是 L/R/C
    - early_stop: 遇到重复节点是否立即停止（True）或跳过重复继续（False）
    - max_depth: 最大深度（根深度1），超过则忽略该节点
    """
    cdef:
        bint use_queue
        cpp_deque[NodeStatus] queue_checked
        py_deque     queue_vid
        vector[NodeStatus]    stack_checked
        list stack_vid

        list vid_list               # 与 _revisit 同步的 visit_index
        vector[size_t] iter_out_uf_idx # 遍历输出节点（通过 next iter 调用的）对应在 _revisit 中的索引
        unsigned int _ops
        size_t _max_depth
        size_t detectable_depth
        bint _instant_updates

    def __cinit__(self):
        self.use_queue = False
        self._ops = 0
        self._max_depth=UPP_SIZE
        self.detectable_depth = 0
        self._instant_updates = False
        self.vid_list = []
        self.queue_vid = py_deque()
        self.stack_vid = list()

    def __init__(self, object root, unsigned int ops, bint use_queue,
                 bint early_stop=False, size_t max_depth=UPP_SIZE):
        super().__init__(early_stop)
        self._ops = ops
        self.use_queue = use_queue
        self._max_depth = max_depth
        self._instant_updates = (ops & OP_U) != 0   # OP_U 表示即时更新模式
        # 将根节点压入容器（未检查）
        root = KitBase.unwrap(root)
        if root is not None:
            self._push(root, 1, False)
        self._prepare_next()

    cdef void _push(self, node, size_t vid, bint checked):
        """压入节点，如果深度超过 max_depth 则忽略"""
        if node is None: return
        depth = vid.bit_length()
        if depth > self.detectable_depth:
            self.detectable_depth = <size_t>depth
            if depth > self._max_depth: return
        
        if self.use_queue:
            self.queue_vid.append(visit_index)
            self.queue_checked.push_back(<pair>(<PyObject*>node,checked))
        else:
            self.stack_vid.append(visit_index)
            self.stack_checked.push_back(<pair>(<PyObject*>node,checked))

    cdef size_t _pop(self, NodeStatus* out):
        """弹出节点，返回 vid，并通过 out 返回 NodeStatus"""
        if self.use_queue:
            out[0] = self.queue_checked.front()
            self.queue_checked.pop_front()
            return self.queue_vid.popleft()
        else:
            out[0] = self.stack_checked.back()
            self.stack_checked.pop_back()
            return self.stack_vid.pop()

    cdef bint _is_empty(self):
        if self.use_queue:
            if not self.queue_vid:
                assert self.queue_checked.empty()
                return True
        else:
            if not self.stack_vid:
                assert self.stack_checked.empty()
                return True
        return False

    def _prepare_next(self):
        cdef NodeStatus ele
        cdef bint checked
        cdef unsigned int ops
        cdef size_t uf_idx

        while True:
            if self._is_empty(): break

            vid = self._pop(&ele)
            node: object = <object>ele.node

            if not checked:
                self.vid_list.append(vid) # _check_safe 无论T/F，_revisit 的容量+1，同步保存 vid。将来改进静态链表大数可直接加入 revisit
                uf_idx = self._check_safe(ele.node)
                if <size_t>(-1) != uf_idx:
                    ops = self._ops   # ✅ 每个节点重新拷贝
                    while ops:
                        if ops&0xF == OP_L:
                            self._push(node.left,vid<<1, False)
                        elif ops&0xF == OP_R:
                            self._push(node.right,(vid<<1)|1, False)
                        else:
                            self._push(node,vid, True)
                        ops >>= OP_SHIFT
                    if not self._instant_updates: # 非即时更新当前节点，继续 POP
                        continue
                elif self._early_stop: break # 不安全且早停，置为空节点
                else: continue # 不安全，继续 POP
            # 已检查安全，或即时更新，设置 POP 节点为当前节点，跳出循环
            self._cur = ele.first
            self.iter_out_uf_idx.push_back(uf_idx) # 记录迭代节点在 _revisit 中的索引
            return
        # 容器空或早停，置为空节点
        self._cur = <PyObject*>None

    cdef list flatten_raw(self, size_t max_len=UPP_SIZE):
        """返回原生节点列表（按遍历顺序）"""
        return SafeIterBase._flatten(self, max_len)

    cdef tuple flatten(self, size_t max_len=UPP_SIZE):
        """
        返回 (节点列表, 重复信息列表)
        - 节点列表: [(visit_index, 原生节点), ...]
        - 重复信息列表: [(visit_index, 指向节点列表的索引), ...]
        - 重复索引列表与遍历列表的堆索引无交集
        - early_stop、max_depth 需在构造函数中指定
        :param max_len: 遍历最大节点数（-1表示不限制）
        """
        cdef size_t i, j = 0
        cdef RevisitEntry ele
        cdef vector[pair[size_t, size_t]].iterator it
        
        # 预分配容器，避免多次扩容
        cdef vector[pair[size_t, size_t]] nodes_uf_vec
        nodes_uf_vec.reserve(self.repeat_num)
        
        # 假设 nodes 已经由 _flatten 预生成
        nodes = SafeIterBase._flatten(self, max_len)
        repeat_indices = [] # 其容量必定不少于 repeat_num 但无法提前确定

        for i in range(self._revisit.size()):
            ele = self._revisit[i]
            
            # 优化分支逻辑：合并相同行为
            # 只有当 ele.uf_index 为 i 或 <size_t>(-1) 时，才执行插入 nodes[j]
            if i == ele.uf_index or ele.uf_index == <size_t>(-1):
                if i == ele.uf_index:
                    nodes_uf_vec.push_back(pair[size_t, size_t](i, j))
                
                nodes[j] = (self.vid_list[i], nodes[i])
                j += 1
            else:
                # 二分查找：nodes_uf_vec 是按 i 递增插入的，天然有序
                it = lower_bound(nodes_uf_vec.begin(), nodes_uf_vec.end(), 
                                pair[size_t, size_t](ele.uf_index, 0))

                assert it != nodes_uf_vec.end() and (*it).first == ele.uf_index
                repeat_indices.append((self.vid_list[i], (*it).second))
                
        return nodes[:j], repeat_indices

    # 仅为了测试验证代码所用，因此不需要高性能，依靠 self.revisit_nodes 的输出
    @property
    def rep_nodes_idx(self):
        """返回重复访问节点的堆索引列表"""
        return [self.vid_list[uf_idx] for uf_idx, node in self.revisit_nodes]
    
cdef class TreeIterKit(KitBase):
    """二叉树用户包装类，提供安全遍历、环检测、美观打印"""
    cdef readonly int heap_index
    def __cinit__(self):
        self.heap_index = 0
    def __init__(self, node=None, int heap_index=1):
        super().__init__(node)
        # 检查节点是否具有 left/right 属性（可选，不做强制）
        self.heap_index = heap_index # 注意 heap_index 是指数递增的堆索引，需要用大整数类（Python的 int 即可）

    cdef TreeIterKit get_heap(self, int heap_index, bint allowed_null=False):
        """按堆索引获取节点（从1开始），路径断裂或遇环时抛出 IndexError"""
        if heap_index < 1:
            raise IndexError("Heap index cannot be less than 1.")
        cur = self.raw
        seen = set()
        # 将 heap_index 转换为二进制路径（去掉最高位的1）
        bits = bin(heap_index)[3:]  # 例如 6 -> '110' -> 去掉 '0b1' 得 '10'
        for bit in bits:
            if cur is None:
                if allowed_null:
                    return None
                raise IndexError(f"Node does not exist at heap index {heap_index}")
            if id(cur) in seen:
                raise IndexError("Cycle detected while following heap path")
            seen.add(id(cur))
            if bit == '0':
                cur = getattr(cur, 'left', None)
            else:
                cur = getattr(cur, 'right', None)
        # 返回包装类
        return TreeIterKit(cur, heap_index)

    def __getitem__(self, Py_ssize_t index):
        if index < 0:
            raise IndexError("The index should not be negative.") # 索引应当非负
        it = self.layer_iter(early_stop=False)
        node = SafeIterBase._get_next(it, index, False)
        if node is None:
            raise IndexError(f"Index {index} out of range")
        uf_idx = it.iter_out_uf_idx[index]
        return TreeIterKit(node, it.vid_list[uf_idx])   # visit_index 在遍历时由迭代器维护，这里暂时设为0

    # ---------- 各种遍历迭代器 ----------
    def layer_iter(self, bint early_stop=False, size_t max_depth=UPP_SIZE):
        """层序遍历迭代器 (操作字符串 "LR")"""
        return TreeIterBase(self.raw, str2OpCode("LR"), use_queue=True,
                            early_stop=early_stop, max_depth=max_depth)

    def NLR_iter(self, bint early_stop=False, size_t max_depth=UPP_SIZE):
        """前序遍历迭代器 (NLR) -> 操作字符串 "RL"（先压右再压左）"""
        return TreeIterBase(self.raw, str2OpCode("RL"), use_queue=False,
                            early_stop=early_stop, max_depth=max_depth)

    def LNR_iter(self, bint early_stop=False, size_t max_depth=UPP_SIZE):
        """中序遍历迭代器 (LNR) -> 操作字符串 "RCL" """
        return TreeIterBase(self.raw, str2OpCode("RCL"), use_queue=False,
                            early_stop=early_stop, max_depth=max_depth)

    def LRN_iter(self, bint early_stop=False, size_t max_depth=UPP_SIZE):
        """后序遍历迭代器 (LRN) -> 操作字符串 "CRL" """
        return TreeIterBase(self.raw, str2OpCode("CRL"), use_queue=False,
                            early_stop=early_stop, max_depth=max_depth)

    def __iter__(self):
        return self.layer_iter()

    # ---------- flatten 方法 ----------
    def flatten(self, bint early_stop=False, size_t max_depth=UPP_SIZE, size_t max_len=UPP_SIZE):
        """层序遍历，返回 (节点列表, 迭代器)"""
        it = self.layer_iter(early_stop=early_stop, max_depth=max_depth)
        nodes = SafeIterBase._flatten(it, max_len)
        # 将节点包装为 TreeIterKit（保持原有 visit_index 信息？nodes 中已是原生节点，我们需要包装）
        wrapped_nodes = [TreeIterKit(node, getattr(node, 'visit_index', 0)) for node in nodes]
        return wrapped_nodes, it

    def flatten_raw(self, bint early_stop=False, size_t max_depth=UPP_SIZE, size_t max_len=UPP_SIZE):
        """返回原生节点列表和迭代器"""
        it = self.layer_iter(early_stop=early_stop, max_depth=max_depth)
        nodes = SafeIterBase._flatten(it, max_len)
        return nodes, it

    # 低级打印，仅显示本节点情况和左右子节点的id
    def __repr__(self) -> str:
        return self._format_repr(self, left=self.left, right=self.right)

    @staticmethod
    cdef str _to_string(object root, str prep_property="val",
                        size_t max_depth=10, size_t max_node_len=UPP_SIZE,
                        bint full_traversal=False):
        """静态方法，实现树形图生成"""
        cdef TreeIterBase it = TreeIterBase(
            root, str2OpCode("LR"), use_queue=True,
            early_stop= not full_traversal,
            max_depth=max_depth
        )
        nodes, repeat_indices = it.flatten(max_len=max_node_len)
        if not nodes:
            return "<class 'TreeNodeKit'>: empty"

        # 构建重复标记
        repeat_mark = {}
        for revisit_vid, pos in repeat_indices:
            orig_vid = nodes[pos][0]
            repeat_mark[orig_vid] = f"*{orig_vid}"
            repeat_mark[revisit_vid] = f"^{orig_vid}"

        # 收集索引->值映射
        idx_val = {}
        for vid, node in nodes:
            if node is not None:
                val = getattr(node, prep_property, None)
                idx_val[vid] = val

        if not idx_val:
            return "<class 'TreeNodeKit'>: empty"

        max_idx = max(max(idx_val.keys()), max(repeat_mark.keys()) if repeat_mark else 0)
        # 构建层序列表
        level_list = [""] * max_idx
        for idx, val in idx_val.items():
            level_list[idx-1] = str(idx)
        for idx, mark in repeat_mark.items():
            level_list[idx-1] = mark

        # 生成树形图
        try:
            from binarytree import build
            bt = build(level_list)
            tree_str = str(bt) if bt else "null"
        except Exception:
            tree_str = "Error: binarytree build failed"

        parts = []
        # 获取重复节点列表（visit_index）
        repeat_vids = it.rep_nodes_idx
        if full_traversal:
            if repeat_vids:
                parts.append(f'  "warning_duplicate_idx": {repeat_vids}')
        else:
            if repeat_vids:
                parts.append(f'  "stop_by_duplicate_idx": {repeat_vids[0]}')

        tree_part = '  "tree_by_idx": """{}{}"""'.format(
            tree_str,
            '...\n' if (it.detectable_depth > max_depth or it._cur != <PyObject*>None) else ''
        )
        parts.append(tree_part)
        parts.append(f'  "idx:val": {idx_val}')
        body = ",\n".join(parts)
        return f"<class 'TreeNodeKit'>: {{\n{body}\n}}"

    # ------------ 兼容测试程序 -----------------
    @property
    def visit_index(self) -> int:
        """完全二叉树索引（从1开始）"""
        return self.heap_index # object.__getattribute__(self,"heap_index")

    @property
    def depth(self) -> int:
        """节点深度（根深度为1）"""
        if not self.raw:
            return 0
        return self.heap_index.bit_length()

    @property
    def left(self) -> 'TreeIterKit':
        node = self.raw
        if node is None:
            raise AttributeError("Empty tree nodes cannot use `.left` property")
        return self.__class__(node.left if node else None, self.heap_index << 1)

    @left.setter
    def left(self, value: 'TreeIterKit | T_LR | None'):
        node = self.raw
        if node is None:
            raise AttributeError("Empty tree nodes cannot set `.left` property")
        node.left = self.unwrap(value)

    @property
    def right(self) -> 'TreeIterKit':
        node = self.raw
        if node is None:
            raise AttributeError("Empty tree nodes cannot use `.right` property")
        return self.__class__(node.right if node else None, (self.heap_index << 1) | 1)

    @right.setter
    def right(self, value: 'TreeIterKit | object | None'):
        node = self.raw
        if node is None:
            raise AttributeError("Empty tree nodes cannot set `.right` property")
        node.right = self.unwrap(value)
