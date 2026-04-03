from typing import Any, Callable, Dict, List, Tuple, Union, Optional, get_type_hints, get_args, get_origin,Generic,TypeVar,Iterator,Hashable,Deque,Iterable,Protocol, runtime_checkable ,cast
from collections import deque,defaultdict
from itertools import chain
from typing_extensions import Self
from binarytree import build
import json
import numpy as np
import cython

__DEBUG__ = False

def _is_base_type(sig_type) -> bool:
    """
    判断类型是否属于 _BASE_TYPE 范畴
    _BASE_TYPE = Union[
        _BASE_TYPE,  # int, float, bool, None, str
        List["_BASE_TYPE"], 
        Dict[Union[str, int], "_BASE_TYPE"]
    ]
    """
    # 处理 Optional/Union 类型
    origin = get_origin(sig_type)
    
    if origin is Union:
        args = get_args(sig_type)
        # 过滤掉 NoneType，检查所有非 None 类型
        non_none_args = [arg for arg in args if arg is not type(None)]
        # 所有非 None 类型都必须是标准类型
        return all(_is_base_type(arg) for arg in non_none_args)
    
    # 基础类型检查
    if sig_type in (int, float, bool, str, type(None)):
        return True
    
    # List 类型检查
    if origin is list or sig_type is list:
        args = get_args(sig_type)
        if not args:  # 裸 list
            return True
        # 检查元素类型
        return all(_is_base_type(arg) for arg in args)
    
    # Dict 类型检查
    if origin is dict or sig_type is dict:
        args = get_args(sig_type)
        if not args:  # 裸 dict
            return True
        # 检查键类型（必须是 str 或 int）和值类型
        key_type, value_type = args[0], args[1] if len(args) > 1 else Any
        key_ok = key_type in (str, int) or get_origin(key_type) is Union
        value_ok = _is_base_type(value_type)
        return key_ok and value_ok
    
    # 其他类型（如 ListNode, TreeNode 等自定义类型）
    return False

def _extract_actual_type(sig_type):
    """
    从类型注解中提取实际类型，用于注册表匹配
    """
    origin = get_origin(sig_type)
    
    if origin is not None:
        # 处理 Union/Optional 情况
        if origin is Union:
            args = get_args(sig_type)
            # 过滤掉 NoneType，返回第一个非 None 类型
            non_none_args = [arg for arg in args if arg is not type(None)]
            if len(non_none_args) == 1:
                return _extract_actual_type(non_none_args[0])
            elif len(non_none_args) > 1:
                # 多个非 None 类型，返回第一个（Union 情况）
                return _extract_actual_type(non_none_args[0])
        else:
            return origin
    
    # 非泛型类型，直接返回
    return sig_type

def _formated_string(val):
    # 处理字符串类型：转义单引号并包裹在 '' 中
    if isinstance(val, str):
        escaped = val.replace("'", "\\'")
        return f"'{escaped}'"
    
    # 递归处理列表
    elif isinstance(val, list):
        return "[" + ", ".join(_formated_string(item) for item in val) + "]"
    
    # 递归处理字典
    elif isinstance(val, dict):
        items = [f"{_formated_string(k)}: {_formated_string(_formated_string(v))}" for k, v in val.items()]
        # 注意：这里根据需求，如果是嵌套处理，只需对内部值再次调用即可
        return "{" + ", ".join(f"{_formated_string(k)}: {_formated_string(v)}" for k, v in val.items()) + "}"
    
    # 递归处理元组
    elif isinstance(val, tuple):
        return "(" + ", ".join(_formated_string(item) for item in val) + ")"
    
    # 其他基本类型（int, float, bool 等）直接返回其字符串表示
    else:
        return str(val)

# 定义支持 .next 属性的协议（泛型约束）
T = TypeVar("T")

class KitBase(Generic[T]): # 泛型
    """调试增强基类（代理模式）"""
    
    def __init__(self, node: Optional[T]):
        object.__setattr__(self, '_node', node)

    def __bool__(self) -> bool:
        return self._node is not None

    @classmethod
    def unwrap(cls, other: 'KitBase[T] | T | None') -> T | None:
        """
        提取包装类内部的原始节点。
        - 如果 other 是 KitBase 子类实例，返回其内部 _node。
        - 否则直接返回 other 本身（可能为 None）。
        """
        if isinstance(other, KitBase):
            # other._node 的类型理论上为 T_Node，但类型检查器无法自动收窄，使用 cast
            return cast(T, other._node)
        return other
        
    def __getattr__(self, name: str) -> T:
        node = object.__getattribute__(self, '_node')
        if name in ['_node']:
            return node
        
        if __DEBUG__: print(f"KitBase.__getattr__({name})")

        if node is None:
            raise AttributeError(f"Empty node has no attribute '{name}'")
        return getattr(node, name)

    def __setattr__(self, name: str, value: Any) -> None:
        value = KitBase.unwrap(value) # 关键：若 value 是 KitBase 包装对象，必须用 KitBase.unwrap(value) 解包
        if name == '_node':
            object.__setattr__(self,'_node',value)
        else: # 其余属性视为给 self.node 赋值

            if __DEBUG__: print(f"KitBase.__setattr__({name})")

            node = object.__getattribute__(self, '_node')
            if node is None:
                raise AttributeError(f"Can't set attribute '{name}' on empty node")
            setattr(node, name, value)

    def __eq__(self, other: Any) -> bool:
        return id(self._node) == id(self.unwrap(other))
    
    def __ne__(self, other: Any) -> bool:
        return id(self._node) != id(self.unwrap(other))
    
class SafeIterBase(Iterator[Tuple[int, T]]):
    def __init__(
        self,
        init_node: KitBase[T]|T|None = None,
        init_idx: int = 0,
        early_stop: bool = not __DEBUG__,
        getitem_null_end: bool = False
    ):
        """
        安全收集迭代结果，避免访问重复节点（支持BFS、DFS遍历）。
        :param init_node: 初始节点，可以是 KitBase 包装的对象，也可以是原生节点对象，还可以为空
        :param init_idx: 初始索引，默认为 0
        :param early_stop: 是否提前停止（为 True 时遇到重复节点马上停止，为 False 时则跳过重复节点直到无非重复节点为止）
        :param getitem_null_end: 使用 __getitem__ 访问索引 i 时，若没有遇到重复节点，且 0..i-1 的索引非空，是否允许 None 作为索引 i 的返回值（默认 False）
        """
        # ⚠️ 核心：统一 unwrap
        init_node = KitBase.unwrap(init_node)

        self._seen: Dict[int, int] = {}
        self._repeat_indices = defaultdict(list)

        self._current_node = init_node
        self._current_idx = init_idx
        self._early_stop = early_stop 
        self._getitem_null_end = getitem_null_end

        # ⭐ 新增缓存：idx -> node
        self._cache: Dict[int, T] = {}

        if init_node is not None:
            self._seen[id(init_node)] = init_idx
            self._cache[init_idx] = init_node

    # ==================== 核心安全检查（统一 unwrap） ====================
    def _safe_id(self, node: Optional[T]) -> int:
        node = KitBase.unwrap(node)
        return id(node)

    def _check_safe(self, assigned_idx: int, node: Optional[T]) -> bool:
        if node is None:
            return False

        nid = self._safe_id(node)

        if nid in self._seen:
            first_idx = self._seen[nid]
            self._repeat_indices[first_idx].append(assigned_idx)
            return False

        self._seen[nid] = assigned_idx

        return True

    # ==================== 新增 __getitem__ ====================
    def __getitem__(self, idx: int) -> Optional[T]:
        if idx < 0:
            raise IndexError("Negative index not supported")

        # ⭐ 关键：让子类提供“重建入口”
        it = self._clone_from_start()
        i = 0
        for i,(_, node) in enumerate(it):
            if i==idx:
                return KitBase.unwrap(node)
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
        if self._early_stop and self._repeat_indices:
            self._current_node = None

        return res

    @property
    def repeat_indices(self) -> List[int]:
        """返回所有重复节点的首次索引（去重）"""
        return list(self._repeat_indices.keys())

    @property
    def first_repeat(self) -> Optional[int]:
        """返回第一个检测到的重复节点的首次索引"""
        return next(iter(self._repeat_indices.keys())) if self._repeat_indices else None

    def _prepare_next(self):
        """抽象方法：由子类实现，内部必须使用 _check_safe 控制入栈/入队"""
        raise NotImplementedError

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
    
@runtime_checkable
class HasNext(Protocol):
    next: Optional[Any]

# 定义支持 .next 属性的协议（泛型约束）
T_NEXT = TypeVar("T_NEXT",bound=HasNext)

# 用于 ListNodeKit
class IterNext(SafeIterBase[T_NEXT]):
    """安全链表迭代器，继承 SafeIterBase 实现环检测，自动解包包装类。"""
    def __init__(self, head: KitBase[T_NEXT]|T_NEXT|None,getitem_null_end=True):
        super().__init__(init_node=head, init_idx=0, early_stop=False,getitem_null_end=getitem_null_end)

    def _clone_from_start(self):
        return IterNext(self._current_node)

    def _prepare_next(self) -> None:
        """移动到下一个节点，并自动解包包装类。"""
        if self._current_node is None:
            return
        self._current_idx += 1
        nxt = self._current_node.next

        # 防御性编程：如果下一个节点是包装类，提取原始节点
        if __DEBUG__ and hasattr(nxt, '_node'):
            nxt = nxt._node

        self._current_node = nxt
        if self._current_node and (not self._check_safe(self._current_idx, self._current_node)):
            self._current_node = None

class ListNodeKitBase(KitBase[T_NEXT]):
    """ 链表调试增强工具，使用代理模式（安全实现） 用法: link = ListNodeKit(head_node) """
    @property
    def next(self)->'ListNodeKitBase[T_NEXT]':
        node = object.__getattribute__(self,"_node")
        if node is None:
            raise AttributeError(f"空链表不能使用 next 属性")
        
        if __DEBUG__:
            assert hasattr(node,"val")
            print(f"调用了 ListNodeKitBase.next , .val={self.val}")

        # 关键：返回当前类的实例，保持装饰器效果延续
        return self.__class__(node.next)
    
    @next.setter
    def next(self, value) -> None:
        raise NotImplementedError("ListNodeKitBase.next.setter 本该仅用于声明，但却被调用了")
        
    def flatten(self: 'ListNodeKitBase[T_NEXT] | T_NEXT | None', max_len: Optional[int] = None) -> Tuple[List[T_NEXT], int | None]:
        """
        安全展开链表，返回节点列表和停止索引。

        支持两种调用方式：
        - 实例调用：`kit.flatten()` 或 `kit.flatten(max_len)`
        - 类/静态风格：`ListNodeKitBase.flatten(head [,max_len])`

        Args:
            max_len: 最大收集节点数，超出则提前终止。

        Returns:
            (nodes, stop_index)
            - nodes: 节点列表（原始节点对象）。
            - stop_index:
                - 检测到环 → 环起始索引
                - 达到 max_len → max_len
                - 正常结束 → None
        """

        if __DEBUG__:
            self =  ListNodeKitBase.unwrap(self)
            assert not hasattr(self,"_node"), "节点被二次包装（double wrap）"

        it = IterNext[T_NEXT](self)

        items, stop_idx = SafeIterBase._flatten(it, None if max_len is None else max_len-1)

        if __DEBUG__:
            assert len(stop_idx)<=1

        return [node for idx, node in items], stop_idx[0] if stop_idx else None

    def __iter__(self):
        """返回安全链表迭代器"""
        return IterNext[T_NEXT](KitBase.unwrap(self))
    
    def __getitem__(self, key)->ListNodeKitBase[T_NEXT]:
        """根据索引获取链表节点，返回的是 ListNodeKitBase 包装类对象，允许最后一个节点恰为空节点返回，但若中途遇到重复节点或空节点则抛出异常"""
        return self.__class__(IterNext(self._node)[key])        
    
    @classmethod
    def _to_string(cls, head: Optional[T_NEXT], prep_property: str = "val" , max_len:int = 10**5) -> str:
        """安全打印链表，自动标记环（> 和 ^）"""
        # 注意要用 unwrap 去包装节点
        nodes, stop_index = ListNodeKitBase[T_NEXT].flatten( KitBase.unwrap(head) ,max_len = max_len)       

        str_lst = []
        
        # 环之前的节点（若无环则全部节点）
        for i in range(stop_index if stop_index else len(nodes)):
            str_lst.append(_formated_string(getattr(nodes[i],prep_property)))
        
        # 有异常终止索引
        if stop_index is not None:
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
    
@runtime_checkable
class HasLR(Protocol):
    left: Optional[Any]
    right: Optional[Any]
# 定义支持 .left , .right 属性的协议（泛型约束）
T_LR = TypeVar("T_LR",bound=HasLR)

class TreeIterBase(SafeIterBase[T_LR]):
    def __init__(self, root: Optional[T_LR], use_queue: bool = False, early_stop: bool = False):
        root = KitBase.unwrap(root)

        super().__init__(root, 1, early_stop)

        self._use_queue = use_queue
        self._container: Deque|List = deque() if use_queue else []
        self._pop = self._container.popleft if use_queue else self._container.pop

    # ==================== 容器统一 ====================
    def _push(self, item):
        self._container.append(item)

    # ==================== 安全 push ====================
    def _push_safe(self, idx: int, node: Optional[T_LR], *extra)->bool:
        node = KitBase.unwrap(node)
        if node and self._check_safe(idx, node):
            self._push((idx, node, *extra))
            return True
        return False

    # ==================== flatten ====================
    def flatten(self, max_depth: Optional[int] = None):
        limit = None if max_depth is None else (2 ** (max_depth + 1))
        return SafeIterBase._flatten(self, limit)

    def _clone_from_start(self):
        return self.__class__(self._current_node, early_stop=self._early_stop)
    
class LayeredTraversal(TreeIterBase[T_LR]):
    def __init__(self, root: Optional[T_LR], early_stop: bool = False):
        super().__init__(root, use_queue=True, early_stop=early_stop)

    def _prepare_next(self):
        if self._current_node is None:
            return

        l_idx = self._current_idx * 2

        self._push_safe(l_idx, self._current_node.left)
        self._push_safe(l_idx + 1, self._current_node.right)

        if self._container:
            self._current_idx, self._current_node, *_ = self._pop()
        else:
            self._current_node = None

class HeapRoute(SafeIterBase[T_LR]):
    """仅防止堆索引路由过程中重复访问祖先节点的错误"""
    def __init__(self, init_node: T_LR, heap_index: int):
        # init_node 是堆索引 1 的節點
        super().__init__(init_node, 1, early_stop=True, getitem_null_end=True)
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
                self._current_node = next_node
                self._current_idx = next_idx
            # early_stop=True 会将 self._current_node = None

    def _clone_from_start(self):
        if not self._current_node:
            raise IndexError("空树不能使用堆索引")
        return self.__class__(self._current_node, self._heap_index)

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
        it = LayeredTraversal(self._node, early_stop=False)
        return self.__class__(it[index])
    
    def flatten(self,max_depth:int|None = None ,early_stop:bool=False) -> Tuple[List[Tuple[int, T_LR]], List[int]]:
        """层序遍历树，返回 (<完全二叉树索引键，节点>列表, 重复节点的索引列表)。"""
        limit = None if max_depth is None else (2 ** (max_depth + 1))
        it = LayeredTraversal(self._node,early_stop) 
        return SafeIterBase._flatten(it,limit)

    def layer_iter(self,early_stop:bool=False) -> SafeIterBase[T_LR]:
        """调用 SafeIter 安全地层序遍历，遍历完毕或出现重复节点时停止"""
        return LayeredTraversal[T_LR](self._node,early_stop=early_stop)
    
    def NLR_iter(self, early_stop:bool=False) -> SafeIterBase[T_LR]:
        """前序遍历迭代器 (NLR)"""
        return PreorderTraversal[T_LR](self._node,early_stop=early_stop)

    def LNR_iter(self, early_stop:bool=False) -> SafeIterBase[T_LR]:
        """中序遍历迭代器 (LNR)"""
        return InorderTraversal[T_LR](self._node,early_stop=early_stop)

    def LRN_iter(self, early_stop:bool=False) -> SafeIterBase[T_LR]:
        """后序遍历迭代器 (LRN)"""
        return PostorderTraversal[T_LR](self._node,early_stop=early_stop)
    
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
        it = LayeredTraversal[T_LR](node, early_stop = not full_traversal)
        max_index = 2 ** max_depth

        # 收集所有可达节点和索引
        idx_node = []
        for idx, n in it:
            if max_index is not None and idx > max_index:
                break
            idx_node.append((idx, n))

        repeat_map = it._repeat_indices   # 直接使用内部字典，或通过新属性暴露
        repeat_idx_dict = {}
        for first_idx, dup_idxs in repeat_map.items():
            if first_idx not in repeat_idx_dict:
                repeat_idx_dict[first_idx] = f"*{first_idx}"
            for dup_idx in dup_idxs:
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
    
    # ===================== 新增三个遍历迭代器 =====================

class PreorderTraversal(TreeIterBase[T_LR]):
    def __init__(self, root: Optional[T_LR], early_stop: bool = False):
        super().__init__(root, use_queue=False,early_stop = early_stop)

        if root:
            self._push_children(1, root)

    def _push_children(self, idx, node):
        self._push_safe(idx * 2 + 1, node.right)
        self._push_safe(idx * 2, node.left)

    def _prepare_next(self):
        if self._container:
            self._current_idx, self._current_node, *_ = self._pop()
            self._push_children(self._current_idx, self._current_node)
        else:
            self._current_node = None
       
class InorderTraversal(TreeIterBase[T_LR]):
    """中序遍历迭代器 (LNR)，继承 TreeIterBase 使用栈容器。"""
    def __init__(self, root: Optional[T_LR], early_stop: bool = False):
        # 先以 None 初始化基类，手动构建栈
        super().__init__(None, use_queue=False, early_stop=early_stop)
        # 压入根节点的整个左链
        idx,node = 1,root # 若 root is None 则循环不会执行
        while self._push_safe(idx, node):
            node = getattr(node, 'left', None)
            idx *= 2

        # 栈顶即为最左节点，弹出作为第一个输出节点
        if self._container:
            self._current_idx, self._current_node = self._pop()

    def _prepare_next(self):
        # 当前节点（刚输出）的右子树处理
        right = getattr(self._current_node, 'right', None)
        if right:
            # 右子节点索引 = 当前索引 * 2 + 1
            r_idx = self._current_idx * 2 + 1
            # 压入右子节点的整个左链
            idx = r_idx
            node = right
            while self._push_safe(idx, node):
                node = getattr(node, 'left', None)
                idx *= 2

        # 从栈中弹出下一个待输出节点
        if self._container:
            self._current_idx, self._current_node, *_ = self._pop()
        else:
            self._current_node = None

class PostorderTraversal(TreeIterBase[T_LR]):
    """后序遍历迭代器 (LRN)，继承 TreeIterBase 使用栈容器，节点附带访问标志。"""
    def __init__(self, root: Optional[T_LR], early_stop: bool = False):
        super().__init__(None, use_queue=False, early_stop=early_stop)

        if self._push_safe(1, root, False): # 自带检查 root is not None
            # 找到第一个后序节点
            self._current_node = self._find_next_post_node()

    def _find_next_post_node(self) -> Optional[T_LR]:
        while self._container:
            idx, node, visited = self._container[-1]
            if visited:
                # 已访问过子节点，弹出并产出
                self._container.pop()
                self._current_idx = idx
                return node
            # 标记为已访问
            self._container[-1] = (idx, node, True)

            l_idx = idx * 2
            # 压入右子节点（先右后左，保证左先出栈）
            right = getattr(node, 'right', None)
            self._push_safe(l_idx + 1, right, False)
            # 再压入左子节点
            left = getattr(node, 'left', None)
            self._push_safe(l_idx, left, False)

        return None

    def _prepare_next(self):
        self._current_node = self._find_next_post_node()

def ReprDecorator(prep_property: str = "val"):
    """
    类装饰器：为 ToStringClass 注入指定的打印属性，调用 to_string(self,prep_property) 实现默认打印行为。
    用法: 
    @ReprDecorator("value")
    class HasReprClass(ToStringClass): pass
    """
    def wrapper(cls):
        # 在被装饰的类中定义 __repr__，利用闭包捕获 prep_property
        def __repr__(self):
            # 直接调用类方法 to_string，传入捕获的属性名
            return self._to_string(self._node, prep_property)
        
        cls.__repr__ = __repr__

        return cls
    return wrapper
