# distutils: language = c++
# ===============================
# 基础导入
# ===============================
from cpython.ref cimport PyObject
from libcpp.vector cimport vector
from libcpp.deque cimport deque
from libcpp.pair cimport pair
from libc.stdint cimport SIZE_MAX


__DEBUG__ = True
cdef extern from "safe_iter_base.h":
    ctypedef struct SafeIter:
        pass

    void safe_iter_init(SafeIter* it, int early_stop)
    void safe_iter_cleanup(SafeIter* it)
    size_t safe_iter_check_safe(SafeIter* it, PyObject* node)

cdef class SafeIterBase:
    cdef SafeIter _it

    def __cinit__(self, bint early_stop):
        safe_iter_init(&self._it, <int>early_stop)

    def __dealloc__(self):
        safe_iter_cleanup(&self._it)

    cdef size_t _check_safe(self, object node):
        return safe_iter_check_safe(&self._it, <PyObject*>node)