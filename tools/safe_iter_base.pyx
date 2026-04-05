# cython: language_level=3
from libc.stdint cimport uintptr_t

cdef class SafeIterBase:
    cdef:
        public dict _seen            # {uintptr_t: [assigned_idx, ...]}
        public list _revisit         # [uintptr_t, ...]
        public object _current_node
        public object _current_idx
        public bint _early_stop
        public bint _getitem_null_end

    def __init__(self, init_node=None, init_idx=0, bint early_stop=False, bint getitem_null_end=False):
        self._seen = {}
        self._revisit = []
        self._current_node = init_node
        self._current_idx = init_idx
        self._early_stop = early_stop
        self._getitem_null_end = getitem_null_end

        if init_node is not None:
            nid = <uintptr_t><void*>init_node
            self._seen[nid] = [init_idx]

    cpdef bint _check_safe(self, object assigned_idx, object node):
        if node is None:
            return False

        cdef uintptr_t nid = <uintptr_t><void*>node

        if nid in self._seen:
            indices = self._seen[nid]
            if len(indices) == 1:
                self._revisit.append(nid)
            indices.append(assigned_idx)
            return False

        self._seen[nid] = [assigned_idx]
        return True

    def __next__(self):
        if self._current_node is None:
            raise StopIteration

        res = (self._current_idx, self._current_node)
        
        # 调用子类实现的 _prepare_next
        self._prepare_next()

        if self._early_stop and self._revisit:
            self._current_node = None

        return res

    def __getitem__(self, object idx):
        if idx < 0:
            raise IndexError("Negative index not supported")

        # 让子类提供重建入口
        it = self._clone_from_start()
        cdef long i = 0
        
        # 遍历迭代器进行模拟索引
        for i, res in enumerate(it):
            _, node = res
            if i == idx:
                return node
        
        if it.repeat_indices:
            raise IndexError("出现重复节点")
            
        if self._getitem_null_end and (i + 1) == idx:
            return None
            
        raise IndexError("索引超出范围")

    @property
    def repeat_indices(self):
        """返回所有重复节点的首次索引列表"""
        return [self._seen[nid][0] for nid in self._revisit]

    @property
    def first_repeat(self):
        """返回第一个检测到的重复节点的首次索引"""
        if not self._revisit:
            return None
        cdef uintptr_t first_nid = self._revisit[0]
        return self._seen[first_nid][0]

    def _prepare_next(self):
        raise NotImplementedError("子类必须实现 _prepare_next")

    def _clone_from_start(self):
        raise NotImplementedError("子类必须实现 _clone_from_start")

    def __iter__(self):
        return self

    @classmethod
    def _flatten(cls, it, object max_idx=None):
        items = []
        for idx, node in it:
            if max_idx is not None and idx > max_idx:
                return items, it.repeat_indices + [idx]
            items.append((idx, node))
        return items, it.repeat_indices
