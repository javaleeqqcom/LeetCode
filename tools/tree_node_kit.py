from typing import Any, Callable, Dict, List, Tuple, Union, Optional, get_type_hints, get_args, get_origin,Generic,TypeVar,Iterator,Hashable,Deque,Iterable,Protocol, runtime_checkable ,cast
from abc import ABC, abstractmethod
from collections import deque,defaultdict
from itertools import chain
from typing_extensions import Self
from binarytree import build
import json
import numpy as np
import cython
from args_parser_tools import KitBase
from safe_iter_base import SafeIterBase

__DEBUG__ = False

@runtime_checkable
class HasLR(Protocol):
    left: Optional[Any]
    right: Optional[Any]
# 定义支持 .left , .right 属性的协议（泛型约束）
T_LR = TypeVar("T_LR",bound=HasLR)

class HeapRoute(SafeIterBase):
    """仅防止堆索引路由过程中重复访问祖先节点的错误"""
    def __init__(self, init_node: KitBase[T_LR]|T_LR, heap_index: int):
        # init_node 是堆索引 1 的節點
        super().__init__(KitBase.unwrap(init_node), 1, early_stop=True, 
                        getitem_null_end=True)
        self._heap_index = heap_index # 用于还原堆索引的路径操作列表
        # 將 '101' 轉為 [False, True] (0=左, 1=右)
        self.route_ops = [op == '1' for op in bin(heap_index)[3:]]

    def _prepare_next(self):
        if not self.route_ops:
            self._current_node = None
            return

        is_right = self.route_ops.pop(0)
        
        if self._current_node:
            next_idx = self._current_idx * 2 + int(is_right)
            next_node = getattr(self._current_node, 'right' if is_right else 'left', None)

            # 恰好是最後一跳到達空節點，允許更新，但如果後面還有指令則會中斷
            if (not next_node) or self._check_safe(next_idx, next_node):
                self._current_node = KitBase.unwrap(next_node) # 防御性编程，防止混淆包装节点
                self._current_idx = next_idx
            # early_stop=True 会将 self._current_node = None

    def _clone_from_start(self):
        if not self._current_node:
            raise IndexError("空树不能使用堆索引")
        return self.__class__(self._current_node, self._heap_index)

class TreeIter(SafeIterBase):
    def __init__(self, root: KitBase[T_LR]|T_LR|None, operation:str, use_queue: bool,  early_stop: bool = False):
        super().__init__(None, 1, early_stop)
        _operation_funs = {
            "l": self._push_left,
            "r": self._push_right,
            "c": self._push_current,
            "u": self._update_current
        }
        self._operation = operation
        self._operation_funs:Tuple[Callable] = tuple(_operation_funs[c] for c in operation.lower())
        self._instant_updates = "u" in operation.lower()
        
        if use_queue:
            self._container = deque()
            self._pop = self._container.popleft
        else:
            self._container = list()
            self._pop = self._container.pop

        if self._push(1, root, False):
            self._prepare_next()

    def _push(self, idx: int, node: KitBase[T_LR]|T_LR|None, *extra) -> bool:
        node = KitBase.unwrap(node) # 防御性编程，防止混淆包装节点
        if node:
            self._container.append((idx, node, *extra))
            return True
        return False
    
    def _push_left(self, idx: int, node: KitBase[T_LR]|T_LR)->None:
        self._push(2*idx, node.left, False)
    
    def _push_right(self, idx: int, node: KitBase[T_LR]|T_LR)->None:
        self._push(2*idx +1, node.right, False)
    
    def _push_current(self, idx: int, node: KitBase[T_LR]|T_LR) ->None:
        self._push(idx, node, True)

    def _update_current(self, idx: int, node: KitBase[T_LR]|T_LR) ->None:
        self._current_idx, self._current_node = idx, node
      
    def _prepare_next(self) -> None:
        """默认实现：适用于栈容器（DFS）的通用迭代逻辑"""
        while self._container:
            # 弹出栈顶元素，检查是否已安全
            idx, node, checked = self._pop()
            if checked: # 检查过已安全，设置为当前节点
                self._update_current(idx, node)
                return
            elif self._check_safe(idx, node): # 未检查过，则进行查重
                for op_fun in self._operation_funs:
                    op_fun(idx,node)
                if self._instant_updates:
                    return # 已经更新 _current_node，马上返回
            elif self._early_stop: # 不安全（重复）节点，若早停则跳出循环，按无后继处理
                break
        # 无后继
        self._current_node = None

    def flatten(self, max_depth: Optional[int] = None):
        limit = None if max_depth is None else (2 ** (max_depth + 1))
        return SafeIterBase._flatten(self, limit)

    def _clone_from_start(self):
        # 调用 init（root, 是否为队列，是否早停）
        return self.__class__(
            self._current_node, 
            self._operation, 
            isinstance(self._container, deque),
            early_stop=self._early_stop
            )

class TreeNodeKitBase(KitBase[T_LR]):
    """
    二叉树调试增强工具基类，使用代理模式。
    提供安全的扁平化（层序遍历）和重复节点检测，避免因错误的树结构导致死循环。
    """
    @property
    def left(self) -> 'TreeNodeKitBase[T_LR]':
        if self._node is None:
            raise AttributeError("空树节点不能使用 left 属性")
        return self.__class__(self._node.left)

    @left.setter
    def left(self, value: 'TreeNodeKitBase[T_LR] | T_LR | None'):
        if self._node is None:
            raise AttributeError("空树节点不能设置 left 属性")
        self._node.left = self.unwrap(value)   # 使用 unwrap 简化

    @property
    def right(self) -> 'TreeNodeKitBase[T_LR]':
        if self._node is None:
            raise AttributeError("空树节点不能使用 right 属性")
        return self.__class__(self._node.right)

    @right.setter
    def right(self, value: 'TreeNodeKitBase[T_LR] | T_LR | None'):
        if self._node is None:
            raise AttributeError("空树节点不能设置 right 属性")
        self._node.right = self.unwrap(value)

    def get_heap(self, heap_index: int) -> 'TreeNodeKitBase[T_LR]':
        """
        按從1開始的堆索引獲取節點。
        邏輯：
        - 正常路徑：返回該節點的 Kit 包裝。
        - 路徑中途斷裂：拋出 IndexError("堆索引超出範圍")。
        - 遇到重複的祖先節點（環）：由 SafeIterBase 攔截並拋出 IndexError。
        - 注意仅防止堆索引路由过程中重复访问祖先节点的错误，对于树中非祖先路径的重复节点，无法检测到重复节点的错误。
        """
        if heap_index < 1:
            raise IndexError("堆索引不能小於1")
        
        # 這裡 early_stop 設為 True，保證一撞環就停止
        it = HeapRoute(self._node, heap_index)
        return self.__class__(it[len(it.route_ops)])

    def __getitem__(self, index: int) -> 'TreeNodeKitBase[T_LR]':
        """按层序遍历顺序索引，跳过重复节点和空节点，若超出树的有效节点，则报错"""
        it = TreeIter(self._node, "ULR", True, early_stop=False)
        return self.__class__(it[index])
    
    def flatten(self,max_depth:int|None = None ,early_stop:bool=False) -> Tuple[List[Tuple[int, T_LR]], List[int]]:
        """层序遍历树，返回 (<完全二叉树索引键，节点>列表, 重复节点的索引列表)。"""
        limit = None if max_depth is None else (2 ** (max_depth + 1))
        it = TreeIter(self._node, "ULR", True, early_stop=early_stop)
        return SafeIterBase._flatten(it,limit)

    def layer_iter(self,early_stop:bool=False) -> TreeIter[T_LR]:
        """调用 SafeIter 安全地层序遍历，遍历完毕或出现重复节点时停止"""
        return TreeIter(self._node, "ULR", True, early_stop=early_stop)
    
    def NLR_iter(self, early_stop:bool=False) -> TreeIter[T_LR]:
        """前序遍历迭代器 (NLR)"""
        return TreeIter(self._node, "RLU", False, early_stop=early_stop)

    def LNR_iter(self, early_stop:bool=False) -> TreeIter[T_LR]:
        """中序遍历迭代器 (LNR)"""
        return TreeIter(self._node, "RCL", False, early_stop=early_stop)

    def LRN_iter(self, early_stop:bool=False) -> TreeIter[T_LR]:
        """后序遍历迭代器 (LRN)"""
        return TreeIter(self._node, "CRL", False, early_stop=early_stop)
    
    def __iter__(self):
        """默认返回层序遍历迭代器"""
        return self.layer_iter()
    
    @classmethod
    def _to_string(cls, root: TreeNodeKitBase[T_LR] | T_LR | None,
                  prep_property: str = "val", max_depth: int = 10,
                  full_traversal: bool = False) -> str:
        """
        生成树的字符串表示，包含：
        - 树形结构（使用 binarytree 库）
        - 完全二叉树索引与节点值的映射
        - 重复节点键（若存在环）

        Args:
            root: 根节点
            prep_property: 节点取值属性名
            max_depth: 最大深度
            full_traversal: 是否完整遍历所有节点（跳过重复节点），并展示所有非法链接。
                           若为 False，则遇到第一个重复节点即停止。
        """
        node: Optional[T_LR] = cls.unwrap(root)
        if node is None:
            return "<class 'TreeNodeKit'>: empty"

        # 根据 full_traversal 决定 early_stop 行为
        it = TreeIter(node, "ULR", True, early_stop = not full_traversal)
        max_index = 2 ** max_depth

        # 收集所有可达节点和索引
        idx_node = []
        for idx, n in it:
            if max_index is not None and idx > max_index:
                break
            idx_node.append((idx, n))

        repeat_idx_dict = {}
        for nid in it._revisit:
            revisit_idx = it._seen[nid]
            first_idx = revisit_idx[0]
            repeat_idx_dict[first_idx] = f"*{first_idx}"
            for dup_idx in revisit_idx[1:]:
                if dup_idx not in repeat_idx_dict:
                    repeat_idx_dict[dup_idx] = f"^{first_idx}"

        # 构建索引到节点值的映射
        idx_val = {idx: getattr(n, prep_property) for idx, n in idx_node}

        idx_max = max(chain(idx_val.keys(),repeat_idx_dict.keys()))
        print_size = min(idx_max, max_index)
        print_bit_map = [None] * print_size   # 索引从 1 开始，列表长度为 max_idx'

        for idx in idx_val.keys():
            if idx <= print_size:
                print_bit_map[idx-1] = str(idx)
            
        for idx,s in repeat_idx_dict.items():
            if idx <= print_size:
                print_bit_map[idx-1] = s
        
        # 构建用于 binarytree.build 的层序列表
        try:
            bt = build(print_bit_map)
            tree_str = str(bt) if bt else "null"
        except Exception:
            tree_str = "Error: binarytree build failed"

        # 构建输出部分
        parts = []
        irepeat_indices = it.repeat_indices
        if full_traversal:
            if irepeat_indices:
                parts.append(f'  "warning_duplicate_idx": {irepeat_indices}')
        else:
            # assert 1 == len(repeat_idxs),"使用了早停，理应只有1个重复索引" # 无法通过验证
            if it.first_repeat is not None:
                parts.append(f'  "stop_by_duplicate_idx": {it.first_repeat}')

        tree_part = '  "tree_by_idx": """{}{}"""'.format(
            tree_str,
            '...\n' if (max_index is not None and idx_max >= max_index) else ''
        )
        parts.append(tree_part)
        parts.append(f'  "idx:val": {idx_val}')

        body = ",\n".join(parts)
        return f"<class 'TreeNodeKit'>: {{\n{body}\n}}"
    