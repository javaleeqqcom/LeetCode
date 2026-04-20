# distutils: language = c++
# ===============================
# 基础导入
# ===============================
from cpython.ref cimport PyObject
from libcpp.vector cimport vector
from libcpp.deque cimport deque
from libcpp.pair cimport pair
from libc.stdint cimport SIZE_MAX
载入 bigint_vid.h 

__DEBUG__ = True
cdef extern from "safe_iter_base.h":
    ctypedef struct SafeIter:
        pass

    ctypedef struct RevisitEntry
        pass

    ctypedef struct UT_icd:
        size_t sz
        void* init
        void* copy
        void* dtor

    void safe_iter_init(SafeIter* it, UT_icd *RevisitEntry_icd)
    void safe_iter_cleanup(SafeIter* it)
    size_t safe_iter_check_safe(SafeIter* it, void* entry_ele)

cdef struct IterTreeELE:
    PyObject* node
    BigInt vid
    bint checked

cdef struct IterLinkELE:
    PyObject* node

ctypedef RevisitEntry RevisitLinkEntry # 基础类型就是用于链表的

cdef struct RevisitTreeEntry:
    size_t uf_index # (-1)u 表示首次出现，>=0 表示重复指向的索引
    PyObject* node
    BigInt vid  # vid 必须在末尾，不影响 safe_iter_get_entry

cdef class SafeIterBase:
    cdef:
        readonly SafeIter _it
        readonly bint early_stop

    def __cinit__(self, size_t entry_size ,bint early_stop):
        cdef UT_icd UT_icd
        UT_icd.sz = entry_size
        safe_iter_init(&self._it, UT_icd) # 实现链表、树的 _revisit 泛型
        self.early_stop = early_stop

    def __dealloc__(self):
        safe_iter_cleanup(&self._it)

    # ------------------- 函数指针实现链表、树泛型（是不是分别放到 LinkIterBase 、 TreeIterBase 更合适？节约编译成本） -------------------------

    cdef size_t _check_safe_tree(self, IterTreeELE* ele):
        return safe_iter_check_safe(&self._it, <void*>ele)

    cdef size_t _check_safe_link(self, IterLinkELE* ele):
        return safe_iter_check_safe(&self._it, <void*>ele)

    cdef PyObject* _get_tree_ptr(void* p):
        return (<IterTreeELE*>p).node

    cdef PyObject* _get_link_ptr(void* p):
        return (<IterLinkELE*>p).node

    # 还需要补充 push_revisit 分链表和树