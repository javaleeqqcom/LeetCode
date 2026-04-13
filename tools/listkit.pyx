# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False

from cpython.ref cimport PyObject
from libc.stdint cimport uintptr_t
from cpython.object cimport PyObject_GetAttrString
from libc.stdlib cimport malloc, free, realloc
from libc.string cimport memcpy


# =========================
# 工具函数
# =========================
ctypedef struct Array:
    char* data
    Py_ssize_t size
    Py_ssize_t capacity
    Py_ssize_t item_size

cdef void array_init(Array* arr, Py_ssize_t item_size):
    arr.size = 0
    arr.capacity = 8
    arr.item_size = item_size
    arr.data = <char*>malloc(arr.capacity * item_size)


cdef void array_append(Array* arr, void* value):
    if arr.size == arr.capacity:
        arr.capacity *= 2
        arr.data = <char*>realloc(arr.data, arr.capacity * arr.item_size)

    memcpy(arr.data + arr.size * arr.item_size, value, arr.item_size)
    arr.size += 1

cdef void* array_get(Array* arr, Py_ssize_t idx):
    return <void*>(arr.data + idx * arr.item_size)

# =========================
# Struct 定义
# =========================

cdef struct BaseIterStruct:
    PyObject* raw
    Py_ssize_t revisit_idx

cdef struct LinkIterStruct:
    BaseIterStruct base
    Py_ssize_t visit_index

cdef inline uintptr_t get_node_id(PyObject* obj):
    return <uintptr_t>obj

cdef PyObject* get_attr_obj(PyObject* obj, const char* attr):
    if obj == NULL:
        return NULL
    return PyObject_GetAttrString(obj, attr)  # 返回新引用

cdef inline LinkIterStruct make_null():
    cdef LinkIterStruct s
    s.base.raw = NULL
    s.base.revisit_idx = -1
    s.visit_index = -1
    return s

cdef inline LinkIterStruct make_node(PyObject* raw, Py_ssize_t vid):
    cdef LinkIterStruct s
    s.base.raw = raw
    s.base.revisit_idx = -1
    s.visit_index = vid
    return s

cdef LinkIterStruct get_next(LinkIterStruct cur):
    cdef LinkIterStruct nxt

    if cur.base.raw == NULL:
        nxt.base.raw = NULL
        return nxt

    nxt.base.raw = get_attr_obj(cur.base.raw, "next")
    nxt.visit_index = cur.visit_index + 1
    nxt.base.revisit_idx = -1

    return nxt

# =========================
# SafeIterBase (Cython)
# =========================

cdef class SafeIterBase:

    cdef LinkIterStruct cur
    cdef dict seen                # uintptr_t -> index
    cdef Array revisit
    cdef Py_ssize_t repeat_num
    cdef bint early_stop

    def __cinit__(self, bint early_stop=True):
        self.seen = {}
        self.repeat_num = 0
        self.early_stop = early_stop
        array_init(&self.revisit, sizeof(LinkIterStruct))

    cdef bint _check_safe(self, LinkIterStruct* node):
        cdef uintptr_t rid

        if node.base.raw == NULL:
            return False

        rid = get_node_id(node.base.raw)

        if rid in self.seen:
            node.base.revisit_idx = self.seen[rid]
            self.repeat_num += 1
            return False
        else:
            node.base.revisit_idx = -1
            self.seen[rid] = self.revisit.size
            array_append(&self.revisit, <void*>&node)
            return True

    def __dealloc__(self):
        if self.revisit.data != NULL:
            free(self.revisit.data)

    cpdef tuple flatten(self, Py_ssize_t max_len=-1):
        cdef list result = []
        cdef LinkIterStruct cur = self.cur
        cdef Py_ssize_t i = 0
        cdef uintptr_t rid

        if max_len == 0:
            return result, 0

        while cur.base.raw != NULL:

            result.append(<object>cur.base.raw)

            if max_len >= 0 and i + 1 == max_len:
                return result, max_len

            cur = get_next(cur)

            if cur.base.raw == NULL:
                return result, -1

            if not self._check_safe(&cur):
                rid = get_node_id(cur.base.raw)
                return result, self.seen[rid]

            i += 1

        return result, -1

# =========================
# Python 包装层
# =========================

cdef class ListNodeKitBase:

    cdef object _raw   # 原生 ListNode

    def __cinit__(self, object head):
        self._raw = head

    @property
    def raw(self):
        return self._raw

    def __bool__(self):
        return self._raw is not None

    # =========================
    # flatten（核心接口）
    # =========================
    cpdef tuple flatten_raw(self, Py_ssize_t max_len=-1):
        """
        直接返回 raw 节点列表（最快路径）
        """
        cdef SafeIterBase it = SafeIterBase(self._raw)
        return it.flatten_raw(max_len)

    cpdef tuple flatten(self, Py_ssize_t max_len=-1):
        """
        返回 Python 包装节点（兼容旧接口）
        """
        cdef list raws
        cdef Py_ssize_t stop

        raws, stop = self.flatten_raw(max_len)

        # 包装为 Python 对象（只有这里有开销）
        return [ListNodeKitBase(node) for node in raws], stop

    # =========================
    # 索引访问（安全）
    # =========================
    def __getitem__(self, Py_ssize_t idx):
        if idx < 0:
            raise IndexError("negative index not supported")

        cdef SafeIterBase it = SafeIterBase(self._raw)
        cdef list raws
        cdef Py_ssize_t stop

        raws, stop = it.flatten_raw(idx + 1)

        if idx < len(raws):
            return ListNodeKitBase(raws[idx])

        # idx == len(raws) → 返回空节点（你原语义）
        if idx == len(raws):
            return ListNodeKitBase(None)

        raise IndexError("index out of range")

    # =========================
    # next（关键：必须保持 raw 语义）
    # =========================
    @property
    def next(self):
        if self._raw is None:
            raise AttributeError("None has no next")

        cdef object nxt = (<object>self._raw).next
        return ListNodeKitBase(nxt)

    @next.setter
    def next(self, value):
        if self._raw is None:
            raise AttributeError("None has no next")

        # 允许传 raw 或 kit
        if isinstance(value, ListNodeKitBase):
            (<object>self._raw).next = value._raw
        else:
            (<object>self._raw).next = value

    # =========================
    # val
    # =========================
    @property
    def val(self):
        if self._raw is None:
            raise AttributeError("None has no val")
        return (<object>self._raw).val

    @val.setter
    def val(self, v):
        if self._raw is None:
            raise AttributeError("None has no val")
        (<object>self._raw).val = v

    # =========================
    # repr（可选）
    # =========================
    def __repr__(self):
        cdef list raws
        cdef Py_ssize_t stop

        raws, stop = self.flatten_raw(20)

        cdef list vals = []
        for node in raws:
            vals.append((<object>node).val)

        return f"<ListNodeKitBase>: {vals}"