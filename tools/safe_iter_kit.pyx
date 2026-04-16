# distutils: language = c++
# ===============================
# 基础导入
# ===============================
from cpython.ref cimport PyObject
from libcpp.vector cimport vector
from libcpp.deque cimport deque
from libcpp.pair cimport pair

ALLOWED_NULL = True
# ===============================
# C struct（核心）
# ===============================
cdef struct RevisitEntry:
    int uf_index
    PyObject* node
cdef _is_null(PyObject* ptr):
    if ptr == NULL: # 防御性编程，虽然统一用 None 指针表达空节点，但以防意外判断 NULL
        return True
    obj = <object>ptr
    # ✅ 关键修复：拦住 None
    if obj is None:
        return True
    return False
# ===============================
# SafeIterBase
# ===============================
cdef class SafeIterBase:
    cdef dict _seen                 # node -> first_index
    cdef vector[RevisitEntry] _revisit
    cdef int _repeat_num
    cdef PyObject* _cur
    def __cinit__(self):
        self._seen = {}
        self._repeat_num = 0
        self._cur = <PyObject*>None
    @property
    def repeat_num(self):
        return self._repeat_num

    # ===== 核心：重复检测 =====
    cdef bint _check_safe(self, PyObject* node):
        cdef int first_idx
        cdef RevisitEntry entry
        if _is_null(node):
            return False
        key = <object>node # 关键！指针 -> PyObj
        if key in self._seen:
            first_idx = <int>self._seen[key]
            entry.uf_index = first_idx
            entry.node = node      # 存储指针，不增加引用计数
            self._revisit.push_back(entry)
            # 标记首次重复
            if self._revisit[first_idx].uf_index == -1:
                self._revisit[first_idx].uf_index = first_idx
                self._repeat_num += 1
            return False
        else:
            first_idx = self._revisit.size()
            self._seen[key] = first_idx # node 通过 _seen 的引用计数维持不在 SafeIterBase 析构前消亡
            entry.uf_index = -1
            entry.node = node
            self._revisit.push_back(entry)
            return True

    # ===== flatten =====
    @staticmethod
    cdef list _flatten(SafeIterBase it, int max_len=-1):
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
        if it._repeat_num > 0:
            raise IndexError("Repeated reference detected")
        if allowed_null:
            return None
        else: # 否则报错
            raise IndexError(f"Index: {index} out of range")
    
    def _prepare_next(self):
        raise NotImplementedError("_prepare_next method should be implemented by the SafeIterBase inheritance class.")
    
    def __iter__(self): return self
    def __next__(self):
        cdef PyObject* res
        if _is_null(self._cur):
            raise StopIteration
        res = self._cur
        # 获取 next（Python属性访问）
        next_node = self._prepare_next()
        if self._check_safe(<PyObject*>next_node):
            self._cur = <PyObject*>next_node    # 经过 _check_safe 后的 next_node 对象确保了引用计数安全
        else:
            self._cur = <PyObject*>None
        return <object>res

    @property
    def revisit_nodes(self):
        cdef list result = []
        cdef size_t i
        cdef RevisitEntry entry
        # 顯式使用 range，Cython 會優化為 C 循環
        for i in range(self._revisit.size()):
            entry = self._revisit[i]
            if i == <size_t>entry.uf_index:
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
        - 如果 other 是 KitBase2 子类实例，返回其内部 _node。
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
    
# ===============================
# LinkIterBase
# ===============================
cdef class LinkIterBase(SafeIterBase):
    def __init__(self, object head):
        super().__init__()
        head = KitBase.unwrap(head)
        if head is not None:
            self._cur = <PyObject*>head
            # ⚠️ 必须先登记 head
            self._check_safe(self._cur)
    # 覆盖 SafeIterBase 基类
    def _prepare_next(self):
        return getattr(<object>self._cur, "next") # next_node 必须赋值为 PyObject 类型否则会报错：`Storing unsafe C derivative of temporary Python reference`
    @property
    def circle_index(self):
        if self._repeat_num > 0:
            return self.revisit_nodes[0][0]
        return -1
    cpdef object get_next(self, Py_ssize_t index , bint allowed_null):
        return SafeIterBase._get_next(self, index, allowed_null)
    cpdef list iter_flatten_raw(self, int max_len=-1):
        return SafeIterBase._flatten(self, max_len)
from args_parser_tools import _formated_string # _to_string 需要
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
    cpdef tuple flatten_stopIDX(self, int max_len=-1):
        cdef LinkIterBase it = LinkIterBase(self.raw) if isinstance(self, LinkIterKit) else LinkIterBase(self, ALLOWED_NULL)
        cdef list nodes = it.iter_flatten_raw(max_len)
        if _is_null(it._cur):
            return nodes, it.circle_index
        else:
            return nodes, max_len
    # ===== getitem =====
    def __getitem__(self, int idx):
        cdef LinkIterBase it = LinkIterBase(self.raw)
        return LinkIterKit(it.get_next(<Py_ssize_t>idx, self._allowed_null))
    @classmethod
    def _to_string(cls, head, prep_property: str = "val" , max_len:int = -1) -> str:
        """安全打印链表，自动标记环（> 和 ^）"""
        cdef Py_ssize_t stop_index
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
  

cdef enum OpCode:
    OP_END = 0
    OP_L   = 1
    OP_R   = 2
    OP_C   = 4
    OP_SHIFT = 4
    OP_U   = 0x44444444

cdef unsigned int str2OpCode(s:str):
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

# -------------------------- 树的遍历 ------------------------------      
# 定義簡化名稱
ctypedef pair[PyObject*, bint] NodeStatus
cdef class TreeIterBase(SafeIterBase):
    cdef:
        vector[NodeStatus]    stack_checked   # 存储对应的 checked 标志
        deque[NodeStatus]     queue_checked
        list vid_list           # 存储 visit_index （暂时用 int 型代替）
        Py_ssize_t _ops
        bint _allowed_null

    def __cinit__(self):
        self.stack = []
        self.vid_list = []
        self._ops = 0
        self._allowed_null = True

    def __init__(self, object root, Py_ssize_t ops, bint allowed_null=True):
        super().__init__()
        self._ops = ops
        self._allowed_null = allowed_null

        root = KitBase.unwrap(root)
        if root is not None:
            self.stack.append((root, 1))

    def _prepare_next(self):
        cdef object node
        cdef int vid
        cdef int ops
        cdef int op

        while self.stack:
            node, vid = self.stack.pop()

            if node is None:
                continue

            if not self._check_safe(<PyObject*>node):
                self._cur = <PyObject*>None
                return

            ops = self._ops

            while ops:
                op = ops & 0xF

                if op == OP_L:
                    if node.left is not None:
                        self.stack.append((node.left, vid << 1))

                elif op == OP_R:
                    if node.right is not None:
                        self.stack.append((node.right, (vid << 1) | 1))

                else:  # OP_C
                    return node
                ops >>= 4
        return None

    cpdef list flatten_raw(self, int max_len=-1):
        cdef list out = []
        cdef int i = 0
        cdef object node

        for node in self:
            out.append(node)
            i += 1
            if max_len >= 0 and i >= max_len:
                break
        return out

    cdef class TreeIterKit(KitBase):
        cdef int _mode
        cdef bint _allowed_null

        def __cinit__(self):
            self._mode = 0
            self._allowed_null = True

        def __init__(self, object root, int mode=0, bint allowed_null=True):
            KitBase.__init__(self, root)
            self._mode = mode
            self._allowed_null = allowed_null

        def __iter__(self):
            return TreeIterBase(self.raw, self._mode, self._allowed_null)

        cpdef list flatten(self, int max_len=-1):
            cdef TreeIterBase it = TreeIterBase(self.raw, self._mode, self._allowed_null)
            return it.flatten_raw(max_len)

        cpdef object get_next(self, int idx):
            cdef TreeIterBase it = TreeIterBase(self.raw, self._mode, self._allowed_null)
            return TreeIterKit(it.get_next(idx), self._mode, self._allowed_null)

        def __getitem__(self, int idx):
            return self.get_next(idx)

cdef class TreeIterKit(KitBase):
    cdef int _mode
    cdef bint _allowed_null

    def __cinit__(self):
        self._mode = 0
        self._allowed_null = True

    def __init__(self, object root, int mode=0, bint allowed_null=True):
        KitBase.__init__(self, root)
        self._mode = mode
        self._allowed_null = allowed_null

    def __iter__(self):
        return TreeIterBase(self.raw, self._mode, self._allowed_null)

    cpdef list flatten(self, int max_len=-1):
        cdef TreeIterBase it = TreeIterBase(self.raw, self._mode, self._allowed_null)
        return it.flatten_raw(max_len)

    cpdef object get_next(self, int idx):
        cdef TreeIterBase it = TreeIterBase(self.raw, self._mode, self._allowed_null)
        return TreeIterKit(it.get_next(idx), self._mode, self._allowed_null)

    def __getitem__(self, int idx):
        return self.get_next(idx)