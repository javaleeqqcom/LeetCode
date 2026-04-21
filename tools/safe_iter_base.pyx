# distutils: language = c
# ===============================
# 基础导入
# ===============================
from cpython.ref cimport PyObject
from libc.stdint cimport SIZE_MAX
from typing import List,Tuple

__DEBUG__ = True

cdef extern from "utarray.h":
    ctypedef struct UT_array:
        pass

cdef extern from "bigint_vid.h":
    cdef struct BigInt:
        size_t small
        size_t pre
        unsigned short bitLen

    BigInt bigint_new(size_t num)
    void bigint_lshift(UT_array* arr, size_t index)
    BigInt bigint_or1(BigInt cur)
    
cdef extern from "safe_iter_base.h":
    ctypedef struct SeenEntry:
        pass
    ctypedef struct SafeIter:
        SeenEntry* seen # "SeenEntry" is not defined
        UT_array* revisit # "UT_array" is not defined
        size_t repeat_num
        RevisitEntry cur
        
    ctypedef struct BaseEntry:
        PyObject* node
    
    ctypedef struct RevisitEntry:
        PyObject* node
        size_t uf_index

    # Cython 不接受 void* 当函数指针
    ctypedef void (*ut_init_f)(void*)
    ctypedef void (*ut_copy_f)(void*, const void*)
    ctypedef void (*ut_dtor_f)(void*)
    ctypedef struct UT_icd:
        size_t sz
        ut_init_f init
        ut_copy_f copy
        ut_dtor_f dtor

    void safe_iter_init(SafeIter* it, UT_icd *RevisitEntry_icd)
    void safe_iter_free(SafeIter* it)
    # 检查是否安全，返回 (-1)u 表示安全，返回 i 表示与 _revist[i] 节点重复。注意该函数不进行PyObject引用计数管理，需手动计数
    size_t safe_iter_check_safe(SafeIter* it, void* entry_ele)
    # 获取 revisit 数组元素个数
    size_t safe_iter_size(const SafeIter* it)
    # 获取第 idx 个元素的指针
    RevisitEntry* safe_iter_get_revisit(SafeIter* it, size_t idx)

    # 函数指针声明
    ctypedef void (*prepare_next_fn)(SafeIter*)
    RevisitEntry safe_iter_next(SafeIter* it, prepare_next_fn prepare_next)

    RevisitEntry safe_iter_skip_next(SafeIter* it,
                                    prepare_next_fn prepare_next,
                                    Py_ssize_t index)

    # 判断 node 是否为空节点
    bint _is_null(PyObject* node)
    # 避开 (-1)u（size_t 最大值）时可取得的上限与 size 取 max
    const size_t _limit_size(Py_ssize_t size)

# 基础类型就是用于链表的
ctypedef BaseEntry IterLinkELE
ctypedef RevisitEntry RevisitLinkEntry 

cdef struct IterTreeELE:
    PyObject* node
    bint checked  # 与 RevisitEntry 的内存结构保持一致
    BigInt vid

cdef struct RevisitTreeEntry:
    PyObject* node
    size_t uf_index # (-1)u 表示首次出现，>=0 表示重复指向的索引
    BigInt vid  # vid 必须在末尾，不影响 safe_iter_get_entry

cdef class SafeIterBase:
    cdef:
        SafeIter _it

    def __cinit__(self, size_t entry_size):
        cdef UT_icd icd
        icd.sz = entry_size
        icd.init = NULL
        icd.copy = NULL
        icd.dtor = NULL

        safe_iter_init(&self._it, &icd)

    def __dealloc__(self):
        safe_iter_free(&self._it)

    cdef inline size_t _check_safe(self, void* ele):
        return safe_iter_check_safe(&self._it, ele)

    def __iter__(self):
        return self

# Argument of type "() -> void" cannot be assigned to parameter "prepare_next" of type "(SafeIter*) -> void" in function "safe_iter_next"
# Type "() -> void" cannot be assigned to type "(SafeIter*) -> void"
# Function accepts too many positional parameters; expected 0 but received 1
    def __next__(self):
        cdef RevisitEntry res = safe_iter_next(&self._it, self._prepare_next)

        if _is_null(res.node):
            raise StopIteration

        return <object>res.node

    @staticmethod
    cdef void _prepare_next(SafeIter* self):
        """
        子类必须实现：用于准备下一个 self._cur ，需确保：
        - 不用检查 self._cur 非空，因为 __next__ 检查过了
        - 需自行调用 _check_safe 确保查重安全
        - 需要自行确保 self._cur 的 PyObject 引用计数安全
        """
        raise NotImplementedError("_prepare_next method should be implemented by the SafeIterBase inheritance class.")

    # ===== flatten =====

    @staticmethod
    cdef list _flatten_raw(SafeIterBase it, Py_ssize_t max_len=-1):
        cdef list out = []
        cdef RevisitEntry cur

        for i in range(_limit_size(max_len)):
            cur = safe_iter_next(&it._it, it._prepare_next)
            if _is_null(cur.node): break
            out.append(<object>cur.node)

        return out

    // 需要修复 或者在 .c 中实现
    @staticmethod
    cdef RevisitEntry* _flatten_revisit(SafeIterBase it, Py_ssize_t max_len=-1):
        cdef RevisitEntry* out = new(it._it.repeat_num)
        cdef RevisitEntry cur

        for i in range(_limit_size(max_len)):
            cur = safe_iter_next(&it._it, it._prepare_next)
            if _is_null(cur.node): break
            out.append?(cur)

        return out

    # ===== get_next =====
    @staticmethod
    cdef inline object _skip_next(SafeIterBase it, Py_ssize_t index, bint early_stop, bint allowed_null):
        cdef Py_ssize_t i = 0
        cdef RevisitEntry res
        if index < 0:
            raise IndexError("SafeIterBase._skip_next: {index} can not be negative")
        res = safe_iter_skip_next(&it._it, it._prepare_next, index)
        if not _is_null(res.node):
            return <object>res.node
        if(res): # 返回非空指针
            return <object>res
        # 如果迭代因环而停止，抛出异常
        if early_stop and it._it.repeat_num > 0:
            raise IndexError("SafeIterBase._skip_next: Repeated reference detected")
        if allowed_null:
            return None
        else: # 否则报错
            raise IndexError(f"SafeIterBase._skip_next: {index} out of range")
    
    # 也可以搞个 C 版的 revisit_nodes，因为其容量确定为 repeat_num，无需动态增长
    @property
    def revisit_nodes(self):
        cdef list result = []
        cdef size_t n = safe_iter_size(&self._it)
        cdef size_t i
        cdef RevisitEntry* entry

        for i in range(n):
            entry = safe_iter_get_revisit(&self._it, i)
            if entry.uf_index == i:
                result.append((i, <object>entry.node))

        return result
