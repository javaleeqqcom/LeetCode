# distutils: language = c
# ===============================
# 基础导入
# ===============================
from cpython.ref cimport PyObject
from libc.stdint cimport SIZE_MAX
from typing import List,Tuple

__DEBUG__ = True

cdef extern from "bigint_vid.h":
    cdef struct BigInt:
        pass
    BigInt bigint_new(size_t num)
    # 需补全 UT_array 的定义
    # void bigint_lshift(UT_array* arr, size_t index)
    # ...
    
cdef extern from "safe_iter_base.h":
    ctypedef struct SafeIter:
    # 请修复声明
        SeenEntry* seen;
        UT_array* revisit;
        size_t repeat_num;
        RevisitEntry cur;

        // RevisitEntry 去耦合专用（链表、树 用不同的函数）由 pyx 提供
        PyObject* (*get_node_ptr)(void* entry_ele); // void 是 IterNode 及其派生类型
        void (*push_revisit)(struct SafeIter* it, void* entry_ele);

    ctypedef struct BaseEntry:
        pass
    
    ctypedef struct RevisitEntry:
        pass

    ctypedef struct UT_icd:
        size_t sz
        void* init
        void* copy
        void* dtor

    void safe_iter_init(SafeIter* it, UT_icd *RevisitEntry_icd)
    void safe_iter_free(SafeIter* it)
    # 检查是否安全，返回 (-1)u 表示安全，返回 i 表示与 _revist[i] 节点重复。注意该函数不进行PyObject引用计数管理，需手动计数
    size_t safe_iter_check_safe(SafeIter* it, void* entry_ele)
    # 获取 revisit 数组元素个数
    size_t safe_iter_size(const SafeIter* it)
    # 获取第 idx 个元素的指针（只读）
    const RevisitEntry* safe_iter_get_entry(const SafeIter* it, size_t idx)

# 请修复如下声明BEGIN
    # 子类实现 __next__ 所需要的函数
    PyObject* safe_iter_next(SafeIter* it, void* entry_ele,
                            void (*prepare_next)(SafeIter*))
    # 不持有 Python Object 的情况下高速迭代
    PyObject* safe_iter_skip_next(SafeIter* it,
                                void (*prepare_next)(SafeIter*),
                                Py_ssize_t index
                                )
# 请修复如下声明END

    # 判断 node 是否为空节点
    bint _is_null(PyObject* node)
    # 避开 (-1)u（size_t 最大值）时可取得的上限与 size 取 max
    const size_t _limit_size(Py_ssize_t size)

# 基础类型就是用于链表的
ctypedef BaseEntry IterLinkELE
ctypedef RevisitEntry RevisitLinkEntry 

cdef struct IterTreeELE:
    PyObject* node
    bint checked
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

    cdef _flatten_base(self, Py_ssize_t max_len):
        cdef size_t n = safe_iter_size(&self._it)
        cdef size_t i

        result = []
        repeat = []

        for i in range(n):
            entry = safe_iter_get_entry(&self._it, i)
            if entry.uf_index == i:
                repeat.append(i)
            result.append(<object>entry.node)

        return result, repeat

    def __iter__(self):
        return self

    def __next__(self):
        # 调用 safe_iter_next 转 object （因为是面向 Python）

    def _prepare_next(self):
        """
        子类必须实现：用于准备下一个 self._cur ，需确保：
        - 不用检查 self._cur 非空，因为 __next__ 检查过了
        - 需自行调用 _check_safe 确保查重安全
        - 需要自行确保 self._cur 的 PyObject 引用计数安全
        """
        raise NotImplementedError("_prepare_next method should be implemented by the SafeIterBase inheritance class.")
    # ===== flatten =====

    # 请修复如下函数：
    @staticmethod
    cdef list _flatten(SafeIterBase it, Py_ssize_t max_len=-2):
        cdef list out = []
        cdef int i = 0
        cdef object node
        cdef _max_len = _limit_size(max_len)
        # 改为调用 safe_iter_next 而不是用 for 以便高效处理
        for node in it:
            out.append(node)
            i += 1
            if _max_len >= 0 and i >= _max_len:
                break
        return out

    # ===== get_next =====
    @staticmethod
    cdef inline object _skip_next(SafeIterBase it, Py_ssize_t index, bint early_stop, bint allowed_null):
        cdef Py_ssize_t i = 0
        cdef PyObject* res
        if index < 0:
            raise IndexError("SafeIterBase._skip_next: {index} can not be negative")
        res = safe_iter_skip_next(...)
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
    def revisit_nodes(self)->List[Tuple[int,object]]:
        cdef list result = []
        cdef Py_ssize_t i
        cdef RevisitEntry entry
        # 顯式使用 range，Cython 會優化為 C 循環

        # 请修复
        # Cannot access member "_revisit" for type "SafeIterBase"
        # Member "_revisit" is unknown
        for i in range(self._revisit.size()):
            entry = self._revisit[i]
            if i == <Py_ssize_t>entry.uf_index:
                # 將 PyObject* 轉回 object
                result.append((entry.uf_index,<object>entry.node))
        return result
