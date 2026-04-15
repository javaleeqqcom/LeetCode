# distutils: language = c++

# ===============================
# 基础导入
# ===============================
from cpython.ref cimport PyObject
from libcpp.vector cimport vector

# ===============================
# C struct（核心）
# ===============================
cdef struct RevisitEntry:
    int uf_index
    PyObject* node


# ===============================
# SafeIterBase
# ===============================
cdef class SafeIterBase:
    cdef dict _seen                 # node -> first_index
    cdef vector[RevisitEntry] _revisit
    cdef int _repeat_num

    def __cinit__(self):
        self._seen = {}
        self._repeat_num = 0

    @property
    def repeat_num(self):
        return self._repeat_num

    # ===== 核心：重复检测 =====
    cdef bint _check_safe(self, PyObject* node):
        cdef PyObject* key
        cdef int first_idx
        cdef RevisitEntry entry

        if node is NULL:
            return False

        key = <PyObject*>node

        if key in self._seen:
            first_idx = <int>self._seen[key]

            entry.uf_index = first_idx
            entry.node = node
            self._revisit.push_back(entry)

            # 标记首次重复
            if self._revisit[first_idx].uf_index == -1:
                self._revisit[first_idx].uf_index = first_idx
                self._repeat_num += 1

            return False

        else:
            first_idx = self._revisit.size()
            self._seen[key] = first_idx

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
    cdef object _get_next(SafeIterBase it, int index, bint allowed_null):
        cdef int i = 0
        cdef object node

        if index < 0:
            raise IndexError()

        for node in it:
            if i == index:
                return node
            i += 1

        if it._repeat_num > 0:
            raise IndexError("Repeated reference detected")

        if allowed_null:
            return None

        raise IndexError()


# ===============================
# LinkIterBase
# ===============================
cdef class LinkIterBase(SafeIterBase):
    cdef PyObject* _cur
    cdef PyObject* _head
    cdef bint _allowed_null

    def __cinit__(self, object head, bint allowed_null=False):
        SafeIterBase.__cinit__(self)

        if head is None:
            self._head = NULL
        else:
            self._head = <PyObject*>head

        self._cur = self._head
        self._allowed_null = allowed_null

        # ⚠️ 必须先登记 head
        self._check_safe(self._head)

    def __iter__(self):
        return self

    def __next__(self):
        cdef PyObject* res
        cdef PyObject* next_node

        if self._cur is NULL:
            raise StopIteration

        res = self._cur

        # 获取 next（Python属性访问）
        next_node = <PyObject*>getattr(<object>self._cur, "next")

        if self._check_safe(next_node):
            self._cur = next_node
        else:
            self._cur = NULL

        return <object>res

    @property
    def circle_index(self):
        if self._repeat_num > 0:
            return self._revisit[0].uf_index
        return -1

    cpdef object get_next(self, int index):
        return SafeIterBase._get_next(self, index, self._allowed_null)

    cpdef list iter_flatten_raw(self, int max_len=-1):
        return SafeIterBase._flatten(self, max_len)


# ===============================
# KitBase（轻量代理）
# ===============================
cdef class KitBase:
    cdef PyObject* _node

    def __cinit__(self, object node):
        if isinstance(node, KitBase):
            self._node = (<KitBase>node)._node
        else:
            if node is None:
                self._node = NULL
            else:
                self._node = <PyObject*>node

    @property
    def raw(self):
        return <object>self._node

    def __getattr__(self, name):
        if self._node is NULL:
            raise AttributeError(name)
        return getattr(<object>self._node, name)

    def __setattr__(self, name, value):
        if name == "_node":
            object.__setattr__(self, name, value)
            return
        if self._node is NULL:
            raise AttributeError(name)
        setattr(<object>self._node, name, value)


# ===============================
# LinkIterKit（用户层）
# ===============================
cdef class LinkIterKit(KitBase):
    cdef bint _allowed_null

    def __cinit__(self, object node, bint allowed_null=False):
        KitBase.__cinit__(self, node)
        self._allowed_null = allowed_null

    def __iter__(self):
        return LinkIterBase(self.raw, self._allowed_null)

    @property
    def next(self):
        if self._node is NULL:
            raise AttributeError("None node")

        cdef object nxt = getattr(<object>self._node, "next")
        return LinkIterKit(nxt, self._allowed_null)

    @next.setter
    def next(self, value):
        if self._node is NULL:
            raise AttributeError("None node")

        setattr(<object>self._node, "next",
                value.raw if isinstance(value, KitBase) else value)

    # ===== flatten =====
    cpdef list flatten(self):
        cdef LinkIterBase it = LinkIterBase(self.raw, self._allowed_null)
        return it.iter_flatten_raw()

    # ===== flatten + stop index =====
    cpdef tuple flatten_stopIDX(self, int max_len=-1):
        cdef LinkIterBase it = LinkIterBase(self.raw, self._allowed_null)
        cdef list nodes = it.iter_flatten_raw(max_len)

        if it._cur is NULL:
            return nodes, it.circle_index
        else:
            return nodes, max_len

    # ===== getitem =====
    def __getitem__(self, int idx):
        cdef LinkIterBase it = LinkIterBase(self.raw, self._allowed_null)
        return LinkIterKit(it.get_next(idx), self._allowed_null)