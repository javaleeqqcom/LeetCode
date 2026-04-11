# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False

from cpython.ref cimport PyObject
from libc.stdint cimport uintptr_t


# =========================
# Struct 定义
# =========================

cdef struct BaseIterStruct:
    PyObject* raw
    Py_ssize_t revisit_idx


cdef struct LinkIterStruct:
    BaseIterStruct base
    Py_ssize_t visit_index


# =========================
# 工具函数
# =========================

cdef inline uintptr_t get_ptr(PyObject* obj):
    return <uintptr_t>obj


cdef inline PyObject* get_next_obj(PyObject* obj):
    """
    等价于 obj.next
    ⚠️ fallback 版本（通用）
    后续可替换为 struct 直取
    """
    if obj == NULL:
        return NULL
    return PyObject_GetAttrString(obj, "next")


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


cdef inline LinkIterStruct get_next(LinkIterStruct cur):
    cdef LinkIterStruct nxt

    if cur.base.raw == NULL:
        return make_null()

    nxt.base.raw = get_next_obj(cur.base.raw)
    nxt.visit_index = cur.visit_index + 1
    nxt.base.revisit_idx = -1

    return nxt


# =========================
# SafeIterBase (Cython)
# =========================

cdef class SafeIterBase:

    cdef dict seen              # uintptr_t -> index
    cdef list revisit           # 存 LinkIterStruct
    cdef Py_ssize_t repeat_num

    cdef LinkIterStruct cur


    def __cinit__(self, object head):
        self.seen = {}
        self.revisit = []
        self.repeat_num = 0

        if head is None:
            self.cur = make_null()
            return

        self.cur = make_node(<PyObject*>head, 0)

        cdef uintptr_t rid = get_ptr(self.cur.base.raw)
        self.seen[rid] = 0
        self.revisit.append(self.cur)


    cdef bint _check_safe(self, LinkIterStruct* node):
        cdef uintptr_t rid

        if node.base.raw == NULL:
            return False

        rid = get_ptr(node.base.raw)

        if rid in self.seen:
            node.base.revisit_idx = self.seen[rid]
            self.repeat_num += 1
            return False
        else:
            node.base.revisit_idx = -1
            self.seen[rid] = len(self.revisit)
            self.revisit.append(node[0])
            return True


    cpdef tuple flatten_raw(self, Py_ssize_t max_len=-1):
        """
        返回 (list[raw_node], stop_index)
        """

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
                rid = get_ptr(cur.base.raw)
                return result, self.seen[rid]

            i += 1

        return result, -1