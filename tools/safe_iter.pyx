# distutils: language = c
# ===============================
# 基础导入
# ===============================
from cpython.ref cimport PyObject, Py_INCREF, Py_DECREF
from libc.stdint cimport SIZE_MAX
from libc.stdlib cimport free
from cpython.list cimport PyList_New, PyList_SET_ITEM
from typing import List, Tuple
from args_parser_tools import _formated_string, _format_repr

__DEBUG__ = True

cdef extern from "utarray.h":
    ctypedef struct UT_array:
        pass

cdef extern from "bigint_vid.h":
    cdef struct BigInt:
        size_t small
        Py_ssize_t pre
        unsigned short bitLen
    BigInt bigint_new(size_t num)
    void bigint_lshift(UT_array* arr, Py_ssize_t index)
    BigInt bigint_or1(BigInt cur)

cdef extern from "safe_iter_base.h":
    # ========== 必须完整声明 SafeIter 的所有成员 ==========
    ctypedef struct SeenEntry:
        pass

    ctypedef struct RevisitEntry:
        PyObject* node
        Py_ssize_t c_index # -1 表示无重复，>=0 表示指向重复节点的最早索引

    ctypedef struct SafeIter:
        SeenEntry* seen
        UT_array* check_record
        Py_ssize_t repeat_num
        RevisitEntry cur
        void* ctx
        prepare_next_fn prepare

    # ✅ 函数指针签名必须与 C 一致
    ctypedef void (*prepare_next_fn)(SafeIter*, void*)

    ctypedef struct UT_icd:
        size_t sz
        void (*init)(void*)
        void (*copy)(void*, const void*)
        void (*dtor)(void*)

    # 检查是否安全，返回 -1 表示安全，返回 i 表示与 _revist[i] 节点重复。注意该函数不进行PyObject引用计数管理，需手动计数
    void safe_iter_init(SafeIter* it, UT_icd* icd)
    void safe_iter_free(SafeIter* it)
    
    # 检查是否安全，返回 -1 表示安全，返回 i 表示与 _revist[i] 节点重复。注意该函数不进行PyObject引用计数管理，需手动计数
    Py_ssize_t safe_iter_check_safe(SafeIter* it, const RevisitEntry* entry_ele)
    # 获取 check_record 数组元素个数
    Py_ssize_t safe_iter_size(const SafeIter* it)
    # 获取第 idx 个元素的指针
    const RevisitEntry* safe_iter_get_revisit(const SafeIter* it, Py_ssize_t idx)
    # 消费迭代器展开 [(revisit索引，节点指针),...]
    UT_array* safe_iter_flatten_entrys(SafeIter* it, Py_ssize_t max_len)
    RevisitEntry* safe_iter_revisit_nodes(const SafeIter* it, Py_ssize_t* out_len)
    RevisitEntry safe_iter_next(SafeIter* it)                     # ✅ 只传一个参数
    RevisitEntry safe_iter_skip_next(SafeIter* it, Py_ssize_t index)  # ✅ 只传两个参数
    bint _is_null(PyObject* node)
    const Py_ssize_t _limit_size(Py_ssize_t size)

# --------------------- UT_array 容器方法 ------------------
cdef extern from "container.h":

    ctypedef struct UT_ArrayIter:
        UT_array* arr
        void* p
        Py_ssize_t i

    ctypedef struct IterResult:
        Py_ssize_t index
        void* obj

    UT_ArrayIter utarray_iter_make(UT_array* arr)
    unsigned char utarray_iter_next(UT_ArrayIter* iter, IterResult* out)
    void utarray_free_arr(UT_array* arr)
    void* utarray_getitem(UT_array* arr, Py_ssize_t index)
    Py_ssize_t utarray_get_len(const UT_array* arr)

# --------------------- UT_array 迭代器 --------------------
cdef class UTArrayIterator:
    cdef:
        UT_ArrayIter iter
        IterResult res
        readonly bint active

    @staticmethod
    cdef UTArrayIterator from_ptr(UT_array* arr):
        cdef UTArrayIterator it = UTArrayIterator.__new__(UTArrayIterator)
        it.iter = utarray_iter_make(arr)
        it.active = True
        return it

    def __iter__(self):
        return self

    def __next__(self):
        """为了高效迭代，不返回元组，需要从 res.index 中提取索引 .index 和元素 .obj"""
        if not self.active:
            raise StopIteration

        if not utarray_iter_next(&self.iter, &self.res):
            self.active = False
            raise StopIteration

        return self.res 

# --------------------- UT_array 访问器 ---------------------
cdef class UTArray:
    cdef UT_array* arr
    
    def __cinit__(self, size_t arr_ptr):
        self.arr = <UT_array*>arr_ptr

    @staticmethod
    cdef UTArray from_ptr(UT_array* arr):
        cdef UTArray it = UTArray.__new__(UTArray)
        it.arr = arr
        return it

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.arr != NULL:
            utarray_free_arr(self.arr)
            self.arr = NULL

    def __iter__(self):
        if self.arr == NULL:
            raise ValueError("UTArray already freed")
        return UTArrayIterator.from_ptr(self.arr)

    cdef inline void* get(self, Py_ssize_t index):
        cdef Py_ssize_t size = utarray_get_len(self.arr)
        # 处理负索引
        if index < 0:
            index += size
        # 边界检查
        if index < 0 or index >= size:
            raise IndexError("UTArray index out of range")
        return utarray_getitem(self.arr, index)

    cdef Py_ssize_t size(self):
        return utarray_get_len(self.arr) # 自带空检测
    def __len__(self):
        return <int>utarray_get_len(self.arr)

# ===============================
# ✅ 全局 bridge 函数（不能放在 class 内部）
# ===============================
cdef void _prepare_bridge(SafeIter* it, void* ctx) with gil:
    cdef SafeIterBase self = <SafeIterBase>ctx
    self._prepare_next()


# ===============================
# SafeIterBase
# ===============================
cdef class SafeIterBase:
    cdef SafeIter _it

    def __cinit__(self, size_t entry_size):
        cdef UT_icd icd
        icd.sz = entry_size
        icd.init = NULL
        icd.copy = NULL
        icd.dtor = NULL
        safe_iter_init(&self._it, &icd)
        self._it.ctx = <void*>self
        self._it.prepare = _prepare_bridge

    def __dealloc__(self):
        safe_iter_free(&self._it)

    # 检查是否安全，返回 -1 表示安全，返回 i 表示与 _revist[i] 节点重复。注意该函数不进行PyObject引用计数管理，需手动计数
    cdef inline Py_ssize_t _check_safe(self, const RevisitEntry* ele):
        return safe_iter_check_safe(&self._it, ele)

    @property
    def cur_node(self):
        return <object>self._it.cur.node

    def __iter__(self):
        return self

    def __next__(self):
        cdef RevisitEntry res = safe_iter_next(&self._it)
        if _is_null(res.node):
            raise StopIteration
        return <object>res.node

    cdef void _prepare_next(self):
        """子类必须实现"""
        raise NotImplementedError("_prepare_next must be implemented by subclass")

    cdef UTArray get_revisit(self):
        return UTArray.from_ptr(self._it.check_record)

    # ===== flatten =====
    cdef inline UTArray flatten_entrys(self, Py_ssize_t max_len=-1):
        return UTArray.from_ptr(
            safe_iter_flatten_entrys(self._it, _limit_size(max_len))
        )

    def flatten_raw(self, Py_ssize_t max_len=-1):
        cdef UTArray entrys_arr = self.flatten_entrys(max_len)
        cdef const RevisitEntry* entry
        cdef list result = PyList_New(<Py_ssize_t>len(entrys_arr))

        with entrys_arr:
            for ele in entrys_arr:
                entry = <const RevisitEntry*>ele.obj
                PyList_SET_ITEM(result, ele.index, <object>entry.node)

        return result

    @property
    cpdef Py_ssize_t repeat_num(self):
        return self._it.repeat_num

    # ===== get_next / skip =====
    cpdef inline object _skip_next(self, Py_ssize_t index, bint early_stop, bint allowed_null):
        if index < 0:
            raise IndexError(f"SafeIterBase._skip_next: index {index} cannot be negative")
        cdef RevisitEntry res = safe_iter_skip_next(&self._it, index)
        if not _is_null(res.node):
            return <object>res.node
        if early_stop and self.repeat_num > 0:
            raise IndexError("SafeIterBase._skip_next: Repeated reference detected")
        if allowed_null:
            return None
        raise IndexError(f"SafeIterBase._skip_next: index {index} out of range")

    @property
    def revisit_nodes(self):
        """
        返回重复节点的 （revisit 索引，节点）列表 待润色
        :return ...
        """
        # 直接使用 repeat_num 作为长度
        cdef Py_ssize_t size = <Py_ssize_t>self._it.repeat_num 
        cdef const RevisitEntry* entry
        # 1. 直接创建一个固定长度的列表，避免动态扩容
        cdef list result = PyList_New(size)
        for i in range(size):
            entry = safe_iter_get_revisit(&self._it, i)
            if entry.c_index == i:
                PyList_SET_ITEM(result, i, (i, <object>entry.node))
        return result


# ===============================
# KitBase（轻量代理，保持不变）
# ===============================
cdef class KitBase:
    cdef readonly object raw
    def __cinit__(self):
        self.raw = None
    def __init__(self, object node):
        self.raw = KitBase.unwrap(node)
    @classmethod
    def unwrap(cls, other):
        if isinstance(other, KitBase):
            return other.raw
        return other
    def __getattr__(self, name: str):
        attr = getattr(type(self), name, None)
        if hasattr(attr, "__get__"):
            return attr.__get__(self)
        node = self.raw
        return getattr(node, name)
    def __setattr__(self, name: str, value):
        attr = getattr(type(self), name, None)
        if hasattr(attr, "__set__"):
            attr.__set__(self, value)
            return
        node = self.raw
        if node is None:
            raise AttributeError(f"Can't set attribute '{name}' on empty node")
        setattr(node, name, KitBase.unwrap(value))
    def __eq__(self, other):
        if not isinstance(other, KitBase):
            return False
        return self.raw is other.raw
    def __ne__(self, other):
        return not self.__eq__(other)
    def __bool__(self):
        return self.raw is not None
    def __repr__(self):
        return _format_repr(self, "raw")


# 基础类型就是用于链表的
ctypedef RevisitEntry RevisitLinkEntry 

cdef struct IterTreeELE:
    PyObject* node
    bint checked  # 与 RevisitEntry 的内存结构保持一致
    BigInt vid

cdef struct RevisitTreeEntry:
    PyObject* node
    Py_ssize_t c_index 
    BigInt vid  # vid 必须在末尾，不影响 safe_iter_get_entry

# ===============================
# ✅ 链表迭代器（新增完整实现）
# ===============================
cdef class LinkIterBase(SafeIterBase):
    def __cinit__(self):
        super().__cinit__(<size_t>sizeof(RevisitLinkEntry))
    
    def __init__(self, object head) -> None:
        super().__init__()
        # 提取原生节点
        head = KitBase.unwrap(head)
        if head is not None:
            self._it.cur.node = <PyObject*>head
            if -1 == self._check_safe(&self._it.cur): # LinkIterBase：意外的错误，无法初始化头结点
                raise Exception("LinkIterBase: Unexpected error, unable to initialize head node") 

    cdef void _prepare_next(self):
        # if _cur 非空: 不需要,因为基类已判非空
        cdef object next_node = getattr(self.cur_node, "next", None) # 而本方法一开始的 next_node 就维持节点的引用计数
        self._it.cur.node = <PyObject*>next_node
        # _check_safe 含有增加 next_node 对象的引用计数，无需重复处理
        self._it.cur.c_index = self._check_safe(&self._it.cur)
        # 必须确保早停，__next__ 才会检测重复 _cur 不重复
        if <Py_ssize_t>(-1) != self._it.cur.c_index: 
            self._it.cur.node = NULL
            
    @property
    cpdef inline Py_ssize_t circle_index(self):
        """环节点索引（最后一个 check_record 的 uf_index）"""
        if self.repeat_num > 0:
            with self.get_revisit() as check_record:
                return (<const RevisitEntry*>check_record.get(-1)).c_index
        return -1

# ===============================
# LinkIterKit（用户层）
# ===============================
cdef class LinkIterKit(KitBase):
    cdef bint _allowed_null
    def __cinit__(self):
        self._allowed_null = True
    def __init__(self, object head, bint allowed_null=True):
        KitBase.__init__(self, head)
        self._allowed_null = allowed_null
    def __iter__(self):
        return LinkIterBase(self.raw)
    @property
    def next(self)->'LinkIterKit':
        node = self.raw
        if node is None:
            raise AttributeError("Empty node has no 'next' attribute")
        
        # 关键：返回当前类的实例，保持装饰器效果延续
        return self.__class__(head = node.next)
    @next.setter
    def next(self, value) -> None:
        node = self.raw # 提取原生节点
        if node is None:
            raise AttributeError("Empty node has no 'next' attribute")
        node.next = self.unwrap(value) # 对原生节点赋值需要去包装
    # ============================ flatten =============================
    cpdef list flatten(self):
        cdef LinkIterBase it = LinkIterBase(self.raw)
        return it.flatten_raw()
    # ===== flatten + stop index =====
    cpdef tuple flatten_stopIDX(self, Py_ssize_t max_len=-1):
        """待补充说明"""
        cdef LinkIterBase it = LinkIterBase(self.raw)
        cdef list nodes = it.flatten_raw(max_len)
        if it.cur_node:  # 迭代器还有非空节点，说明是因为 max_len 限制而停止的（出现环时会因早停而置空节点）
            return nodes, <int>max_len
        return nodes, it.circle_index # 若无环 circle_index 会置为 -1

    # ===== getitem =====
    def __getitem__(self, int idx):
        cdef LinkIterBase it = LinkIterBase(self.raw)
        return LinkIterKit(it._skip_next(
            index=<Py_ssize_t>idx, 
            early_stop=True,
            allowed_null=self._allowed_null
            ))

    # 待改进 _to_string 改为不依赖 Python 对象，完全走 Cython 提高性能
    @classmethod
    def _to_string(cls, head, prep_property: str = "val" , Py_ssize_t max_len=-2) -> str:
        """安全打印链表，自动标记环（> 和 ^）"""
        # 注意要用 unwrap 去包装节点
        nodes, stop_index = LinkIterKit(head).flatten_stopIDX( max_len)       
        str_lst = []
        
        # 环之前的节点（若无环则全部节点）
        for i in range(stop_index if -1 != stop_index else len(nodes)):
            try:
                str_lst.append(_formated_string(getattr(nodes[i],prep_property)))
            except:
                raise Exception(f"len(nodes)={len(nodes)}, stop_index={stop_index}, node={nodes[-1]}")
        
        # 有异常终止索引
        if stop_index >= 0:
            if stop_index == len(nodes):
                str_lst.append("...") # 说明链表长度超过最大限制，截断打印
            else: # 说明检测到链表环
                str_lst.append(">")
            
                # 环之后的节点
                for i in range(stop_index, len(nodes)):
                    assert len(nodes)>0,"len(nodes)==0"
                    str_lst.append(_formated_string(getattr(nodes[i],prep_property)))
            
                # 环结束标记
                str_lst.append("^")
        return f"<class 'ListNodeKit'>: [{','.join(str_lst)}]"

