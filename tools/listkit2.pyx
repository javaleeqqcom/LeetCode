# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False

from cpython.ref cimport PyObject
from libc.stdint cimport uintptr_t
from cpython.object cimport PyObject_GetAttrString
from libc.stdlib cimport malloc, free, realloc
from libc.string cimport memcpy

# ------------------- 动态数组 ------------------
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

cdef void array_free(Array* arr):
    if arr.data != NULL:
        free(arr.data)

# =========================
# Struct 定义
# =========================

cdef struct BaseIterStruct:
    PyObject* raw
    Py_ssize_t revisit_idx

cdef struct LinkIterStruct:
    BaseIterStruct base
    Py_ssize_t visit_index

cdef struct TreeIterStruct:
    BaseIterStruct base
    Array visit_index # 小端存储，方便 <<1 大概率仅需修改 long_visit_index[0]

# =========================
# 工具函数
# =========================

cdef inline uintptr_t get_node_id(PyObject* obj):
    return <uintptr_t>obj

cdef PyObject* get_attr_obj(PyObject* obj, const char* attr):
    if obj == NULL:
        return NULL
    return PyObject_GetAttrString(obj, attr)  # 返回新引用

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
            array_append(&self.revisit, node)
            return True

    def __next__(self):
        if self.cur is None:
            raise StopIteration

        # 调用子类实现的 _prepare_next
        res = self._prepare_next()

        if self._early_stop and self.revisit.size: # 出现重复且早停
            self.cur = None

        return res

    def _prepare_next(self):
        raise ImplementedError

    def __dealloc__(self):
        array_free(self.revisit)

    def __iter__(self):
        return self
    
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
