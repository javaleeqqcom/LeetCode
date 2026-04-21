# distutils: language = c

from cpython.ref cimport PyObject
# Import "(cython)[pxd] safe_iter_base" could not be resolved
# "_is_null" is not accessed
from safe_iter_base cimport SafeIterBase, BaseEntry, _is_null

cdef class LinkIterBase(SafeIterBase):

    def __cinit__(self, object head):
        super().__cinit__(sizeof(BaseEntry))
        需要绑定 _prepare_next

        if not _is_null(head):
            # 初始化 cur
            self._check_safe(&self._it.cur) # 先向 _seen 注册并持有引用
            self._it.cur.node = head # 不需要持有引用，因为由 _seen 持有 
            # self._it.cur.uf_index = -1 不需要基类已赋值

    def __dealloc__(self):
        super().__dealloc__()

    cdef void _prepare_next(self):
        cdef PyObject* next_node

        # if self._cur == NULL: 不需要因为基类 已判非空

        # Python 属性访问
        next_node = <PyObject*>getattr(<object>self._cur, "next", None)

        # 引用管理
        if next_node != NULL:
            Py_INCREF(next_node)

        if self._cur != NULL:
            Py_DECREF(self._cur)

        self._cur = next_node

        # 更新 cur
        self._it.cur.node = self._cur

        if self._cur != NULL:
            self._check_safe(&self._it.cur)