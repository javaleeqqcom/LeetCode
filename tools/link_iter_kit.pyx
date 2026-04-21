# distutils: language = c
# ===============================
# 基础导入
# ===============================
from cpython.ref cimport PyObject
from libc.stdint cimport SIZE_MAX
# 报错： Import "(cython)[pxd] safe_iter_base" could not be resolved
from safe_iter_base cimport SafeIterBase 

cdef struct IterLinkELE:
    PyObject* node

cdef class LinkIterBase(SafeIterBase):

    def __init__(self, head):
        super().__init__(sizeof(RevisitLinkEntry), True)

        cdef IterLinkELE ele
        ele.node = <PyObject*>head

        self._check_safe(&ele)

        self._cur = head
