# distutils: language = c
# ===============================
# 基础导入
# ===============================
from cpython.ref cimport PyObject
from libc.stdint cimport SIZE_MAX
from typing import List,Tuple
from args_parser_tools import _formated_string,_format_repr # _to_string 需要

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
        pass
        
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
    RevisitEntry safe_iter_next(SafeIter* it)

    RevisitEntry safe_iter_skip_next(SafeIter* it,Py_ssize_t index)

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

# Cannot assign member "ctx" for type "SafeIter"
# Member "ctx" is unknown
# Cannot assign member "prepare" for type "SafeIter"
# Member "prepare" is unknown
        self._it.ctx = <void*>self
        self._it.prepare = _prepare_bridge

    def __dealloc__(self):
        safe_iter_free(&self._it)

    cdef inline size_t _check_safe(self, void* ele):
        return safe_iter_check_safe(&self._it, ele)

    def __iter__(self):
        return self

    # 定义一个兼容 C 的全局/静态函数作为桥梁，将 _prepare_next 桥接到 SafeIterBase.c 的 prepare 方法中
    cdef void _prepare_bridge(SafeIter* it, void* ctx) with gil:
        cdef SafeIterBase self = <SafeIterBase>ctx
        self._prepare_next()

    def __next__(self):
        cdef RevisitEntry res = safe_iter_next(&self._it)

        if _is_null(res.node):
            raise StopIteration

        return <object>res.node

    cdef void _prepare_next(self):
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


# ===============================
# KitBase（轻量代理）
# ===============================
cdef class KitBase:
    cdef readonly object raw
    def __cinit__(self):
        self.raw= None
    def __init__(self, object node) -> None:
        self.raw = KitBase.unwrap(node)
    @classmethod
    def unwrap(cls, other):
        """
        提取包装类内部的原始节点。
        - 如果 other 是 KitBase 子类实例，返回其内部 _node。
        - 否则直接返回 other 本身（可能为 None）。
        """
        if isinstance(other, KitBase):
            return other.raw
        return other
    def __getattr__(self, name: str):
        """代理属性访问到原生节点"""
        # 1️⃣ 先查类属性
        attr = getattr(type(self), name, None)
        # 2️⃣ 如果是 data descriptor（有 __set__）
        if hasattr(attr, "__get__"):
            # ✅ 调用 property
            return attr.__get__(self)
        # 3️⃣ 否则走你原来的逻辑
        node = self.raw
        return getattr(node, name)
    def __setattr__(self, name: str, value) -> None:
        # 1️⃣ 先查类属性
        attr = getattr(type(self), name, None)
        # 2️⃣ 如果是 data descriptor（有 __set__）
        if hasattr(attr, "__set__"):
            attr.__set__(self, value)   # ✅ 调用 property setter
            return
        # 3️⃣ 否则走你原来的逻辑
        node = self.raw
        if node is None:
            raise AttributeError(f"Can't set attribute '{name}' on empty node")
        setattr(node, name, KitBase.unwrap(value))
    def __eq__(self, other) -> bool:
        """比较两个包装节点是否包装同一个原生节点"""
        if not isinstance(other,KitBase): return False
        return self.raw is other.raw
    def __ne__(self, other) -> bool:
        return not self.__eq__(other)
    def __bool__(self) -> bool:
        return self.raw is not None

    # 低级打印，仅显示本节点情况
    def __repr__(self) -> str:
        return _format_repr(self,"raw")

cdef class LinkIterBase(SafeIterBase):

    def __cinit__(self, object head):
        super().__cinit__(<size_t>sizeof(BaseEntry))
        head = KitBase.unwrap(head) # 提取原生节点

        if head is None:
            # 初始化 cur
# Cannot access member "cur" for type "SafeIter"
# Member "cur" is unknown
            self._check_safe(&self._it.cur) # 先向 _seen 注册并持有引用
            self._it.cur.node = <PyObject*>head # 不需要持有引用，因为由 _seen 持有 
            # self._it.cur.uf_index = -1 不需要基类已赋值

    def __dealloc__(self):
        super().__dealloc__()

    cdef void _prepare_next(self):
        cdef PyObject* next_node

        # if _cur == NULL: 不需要因为基类 已判非空

        # Python 属性访问
        next_node = <PyObject*>getattr(<object>self._cur, "next", None)

        # 更新 cur
        self._it.cur.node = next_node

        # 不需要引用管理，因为 _check_safe 实现了
        if self._cur != NULL:
            self._check_safe(&self._it.cur)

    
    cdef void _prepare_next(self): # 调用前已确保 self._cur 非空
        cdef object next_node = getattr(<object>self._it.cur.node, "next") # next_node 必须赋值为 PyObject 类型否则会报错：`Storing unsafe C derivative of temporary Python reference`
        self._it.cur.node = <PyObject*>next_node
        # 必须确保早停，__next__ 才会检测重复 _cur 不重复
        if <size_t>(-1) == self._check_safe(self._it.cur.node): # 经过 _check_safe 后的 next_node 对象确保了引用计数安全
            self._it.cur.node = NULL