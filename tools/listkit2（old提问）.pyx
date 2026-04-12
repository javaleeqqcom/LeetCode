# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False

from cpython.ref cimport PyObject
from libc.stdint cimport uintptr_t
from cpython.object cimport PyObject_GetAttrString
from libc.stdlib cimport malloc, free, realloc
from libc.string cimport memcpy

# =========================
# Struct 定义
# =========================

cdef struct BaseIterStruct:
    PyObject* raw
    Py_ssize_t revisit_idx


cdef struct LinkIterStruct:
    BaseIterStruct base
    Py_ssize_t visit_index

cdef struct Array:
    Py_ssize_t capacity
    Py_ssize_t size
    void* array

cpdef append_array(Array* arr, void* value ,Py_ssize_t sizeof_val):
    ...

cpdef get_array(Array* arr, Py_ssize_t index ,Py_ssize_t sizeof_val):
    ...

cdef struct TreeIterStruct:
    BaseIterStruct base
    Array visit_index # 小端存储，方便 <<1 大概率仅需修改 long_visit_index[0]

# =========================
# 工具函数
# =========================

cdef inline uintptr_t get_ptr(BaseIterStruct* iter_struct):
    return <uintptr_t>iter_struct.raw

cdef PyObject* get_attr_obj(BaseIterStruct* iter_struct, str? attr):
    if iter_struct.raw == NULL:
        return NULL

    cdef object tmp = PyObject_GetAttrString(<object>iter_struct.raw, attr)
    return <PyObject*>tmp

cdef inline LinkIterStruct get_next(LinkIterStruct cur):
    cdef LinkIterStruct nxt

    if cur.base.raw == NULL:
        return make_null()

    nxt.base.raw = get_attr_obj(cur.base, "next")
    nxt.visit_index = cur.visit_index + 1
    nxt.base.revisit_idx = -1

    return nxt

# =========================
# SafeIterBase (Cython)
# =========================

cdef class SafeIterBase:

    cdef void* cur
    cdef dict seen              # uintptr_t -> index
    cdef Array revisit #
    Py_ssize_t sizeof_revisit # 根据 TreeIterStruct 和 LinkIterStruct 选择 sizeof
    cdef Py_ssize_t repeat_num # 注意与 revisit.cap 不等价，仅算 revisit[p] 中 revisit_idx == p 的数量

    cdef cbool early_stop

    def __cinit__(self,  early_stop): # SafeIterBase 不再初始化 cur，由子类实现
        self.seen = {}
        self.repeat_num = 0
        self.revisit # 注意根据 sizeof_revisit

    cdef bint _check_safe(self, void* node):
        cdef uintptr_t rid
        node = <BaseIterStruct>node  # 只关心公共的 BaseIterStruct 部分

        if node.base.raw == NULL:
            return False

        rid = get_ptr(node.base.raw)

        if rid in self.seen:
            node.base.revisit_idx = self.seen[rid]
            self.repeat_num += 1
            return False
        else:
            node.base.revisit_idx = -1
            self.seen[rid] = self.revisit_size
            self._revisit_append(node[0])
            return True

    def get_next(self):
        if self.cur is None:
            raise StopIteration

        # 调用子类实现的 _prepare_next
        res = self._prepare_next()

        if self._early_stop and self.revisit.size: # 出现重复且早停
            self.cur = None

        return res

    def __dealloc__(self):
        if self.revisit != NULL:
            free(self.revisit)

    cpdef tuple flatten(self, Py_ssize_t max_len=-1 , cfun *parse_fun=None):
        """
        返回 (list[node], stop_index)
        """

        cdef list result = []
        cdef BaseIterStruct *cur = self.cur # 遍历时只关心 BaseIterStruct 部分
        cdef Py_ssize_t i = 0
        cdef uintptr_t rid

        if max_len == 0:
            return result, 0

        while cur.base.raw != NULL:
            # 由子类代入的函数，将当前节点转换为最终结果，可以实现：1. 返回原生节点；2. 返回包装后的节点（注意Tree和LInk大小不一样）
            result.append(parse_fun(cur))

            if max_len >= 0 and i + 1 == max_len:
                return result, max_len

            cur = get_next(cur)

            if cur.base.raw == NULL:
                return result, -1

            if not self._check_safe(&cur):
                rid = get_ptr(cur.base.raw)
                return result, self.seen[rid]

            i += 1

        return result, -1
