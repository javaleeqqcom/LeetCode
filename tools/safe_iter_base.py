from typing import Any, Callable, Dict, List, Tuple, Union, Optional,Iterator
from collections import deque,defaultdict

class SafeIterBase:
    def __init__(
        self,
        init_node: Any = None,
        init_idx: int = 0,
        early_stop: bool = False,
        getitem_null_end: bool = False
    ):
        """
        安全收集迭代结果，避免访问重复节点（支持BFS、DFS遍历）。
        :param init_node: 初始节点，可以是 KitBase 包装的对象，也可以是原生节点对象，还可以为空
        :param init_idx: 初始索引，默认为 0
        :param early_stop: 是否提前停止（为 True 时遇到重复节点马上停止，为 False 时则跳过重复节点直到无非重复节点为止）
        :param getitem_null_end: 使用 __getitem__ 访问索引 i 时，若没有遇到重复节点，且 0..i-1 的索引非空，是否允许 None 作为索引 i 的返回值（默认 False）
        """

        self._seen: Dict[int, List[int]] = defaultdict(list)
        self._revisit = list()

        self._current_node = init_node
        self._current_idx = init_idx
        self._early_stop = early_stop 
        self._getitem_null_end = getitem_null_end

        if init_node is not None:
            self._seen[id(init_node)].append(init_idx)

    def _check_safe(self, assigned_idx: int, node: Any) -> bool:
        if node is None:
            return False

        nid = id(node)

        if nid in self._seen:
            if 1 ==  len(self._seen[nid]):
                self._revisit.append(nid)
            return False

        self._seen[nid].append(assigned_idx)

        return True

    # ==================== 新增 __getitem__ ====================
    def __getitem__(self, idx: int) -> Any:
        if idx < 0:
            raise IndexError("Negative index not supported")

        # ⭐ 关键：让子类提供“重建入口”
        it = self._clone_from_start()
        i = 0
        for i,(_, node) in enumerate(it):
            if i==idx:
                return node
        if it.repeat_indices:
            raise IndexError("出现重复节点")
        # 允许 None 作为合法索引，但仅限于末端
        if self._getitem_null_end and i+1 == idx:
            return None
        raise IndexError("索引超出范围")
    
    def _clone_from_start(self):
        raise NotImplementedError("子类必须实现 _clone_from_start")
    
    # ==================== next ====================
    def __next__(self) -> Tuple[int, T]:
        if self._current_node is None:
            raise StopIteration

        # 1. 准备当前要返回的结果 POP
        res = (self._current_idx, self._current_node)

        # 2. 由子类实现寻找后继节点 PUSH
        self._prepare_next()

        # 如果开启了 early_stop 且刚刚探测到了环
        if self._early_stop and self._revisit:
            self._current_node = None

        return res

    @property
    def repeat_indices(self) -> List[int]:
        """返回所有重复节点的首次索引，顺序与重复检测到顺序一致"""
        res = [self._seen[nid][0] for nid in self._revisit]
        return res

    @property
    def first_repeat(self) -> Optional[int]:
        """返回第一个检测到的重复节点的首次索引"""
        return self._seen[self._revisit[0]][0] if self._revisit else None

    def _prepare_next(self):
        """抽象方法：由子类实现，内部必须使用 _check_safe 控制入栈/入队"""
        raise NotImplementedError
    
    def __iter__(self):
        return self

    @classmethod
    def _flatten(cls, it: "SafeIterBase", max_idx: Optional[int] = None)->Tuple[List[Tuple[int,T]],List[int]]:
        """
        安全收集迭代结果，可选限制最大索引。

        :param iterable: 产生 (索引, 节点) 对的迭代器
        :param max_idx:   最大索引（包含），若提供则仅收集 idx < max_idx 的元素，并提前停止迭代
        :return 停止索引列表: 遍历时遇到的“重复节点索引”或“超过max_idx的索引（强制停止）”的列表
        :return: ([(索引, 节点),...], 停止索引列表)
        """
        items = []
        for idx, node in it:
            if max_idx is not None and idx > max_idx:
                return items, it.repeat_indices + [idx]
            items.append((idx, node))
        return items, it.repeat_indices
