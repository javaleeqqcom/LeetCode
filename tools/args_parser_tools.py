from typing import Any, Callable, Dict, List, Tuple, Union, Optional, get_type_hints, get_args, get_origin,Generic,TypeVar,Iterator,Hashable,Deque,Iterable,Protocol, runtime_checkable ,cast
from collections import deque,defaultdict
from binarytree import build
import json

__DEBUG__ = True

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

T = TypeVar('T')
class SafeIterBase(Iterator[Tuple[int, T]]):
    def __init__(self, init_node: Optional[T] = None, init_idx: int = 0, early_stop: bool = not __DEBUG__):
        # nid -> 访问过该节点的 idx 列表
        self._seen: Dict[int, List[int]] = defaultdict(list)
        # 记录所有导致冲突的【原始节点索引】
        self._repeat_indices: List[int] = []  
        
        self._current_node = init_node
        self._current_idx = init_idx
        self._early_stop = early_stop

        if init_node is not None:
            self._seen[id(init_node)].append(init_idx)

    def _check_safe(self, assigned_idx: int, node: Optional[T]) -> bool:
        """
        核心逻辑：
        1. 发现重复：记录目标节点的原始索引，返回 False（阻止子类入栈/入队该节点）。
        2. 正常：登记并返回 True。
        """
        if node is None: return False
        nid = id(node)
        
        if nid in self._seen:
            # 记录被指向的那个“前辈”的第一个索引
            self._repeat_indices.append(self._seen[nid][0])
            # 记录本次非法指向发生的当前索引，用于路径追溯
            self._seen[nid].append(assigned_idx)
            return False # 物理阻断，防止死循环
            
        self._seen[nid].append(assigned_idx)
        return True

    def __next__(self) -> Tuple[int, T]:
        if self._current_node is None:
            raise StopIteration
            
        # 1. 准备当前要返回的结果
        res = (self._current_idx, self._current_node)
        
        # 2. 尝试寻找后继节点
        self._prepare_next()

        # 3. 策略处理：
        # 如果开启了 early_stop 且刚刚探测到了环
        if self._early_stop and self._repeat_indices:
            # 强制将下一个节点设为 None，使得下一次调用 next 时 StopIteration
            self._current_node = None
            
        return res

    @property
    def repeat_idx(self) -> List[int]:
        """返回所有触发重复的节点的原始索引列表"""
        return self._repeat_indices

    @property
    def first_repeat(self) -> Optional[int]:
        """返回第一个检测到的重复节点的原始索引"""
        return self._repeat_indices[0] if self._repeat_indices else None

    def _prepare_next(self):
        """抽象方法：由子类实现，内部必须使用 _check_safe 控制入栈/入队"""
        raise NotImplementedError
    
    @classmethod
    def _flatten(cls, it: SafeIterBase, max_idx: Optional[int] = None):
        """
        安全收集迭代结果，可选限制最大索引。

        :param iterable: 产生 (索引, 节点) 对的迭代器
        :param max_idx:   最大索引（包含），若提供则仅收集 idx < max_idx 的元素，并提前停止迭代
        :return 终止索引: 当正常结束时为 None；超出 max_idx 而提前终止时为 max_idx；出现重复节点时为该节点的索引
        :return: ([(索引, 节点),...], 终止索引)
        """
        # 注意：这里 items = list(it) 会自动触发 __next__
        items = []
        for idx, node in it:
            if max_idx is not None and idx > max_idx:
                return items, max_idx
            items.append((idx, node))
        return items, it.first_repeat

@runtime_checkable
class HasNext(Protocol):
    next: Optional[Any]
# 定义支持 .next 属性的协议（泛型约束）
T_NEXT = TypeVar("T_NEXT",bound=HasNext)

# 待修订，用于 ListNodeKit
class IterNext(Generic[T_NEXT]):
    """迭代器，用于遍历链表（通过 next 属性获取下一个节点）"""
    def __init__(self, head: Optional[T_NEXT]):
        """初始化迭代器，从指定节点开始"""
        self.link = head
        self.idx = 0
    
    def __next__(self) -> Tuple[int,T_NEXT]:
        """返回当前节点并移动到下一个节点"""
        if not self.link:
            raise StopIteration
        node = self.link
        self.link = node.next  # 移动到下一个节点
        self.idx += 1
        return (self.idx - 1,node)
    
    def __iter__(self) -> 'IterNext':
        """返回自身，使对象可迭代"""
        return self

T_Node = TypeVar('T_Node', bound=Optional[Any]) # NodeType 必须包含 None 的情况
class KitBase(Generic[T_Node]): # 泛型
    """调试增强基类（代理模式）"""
    
    def __init__(self, node: Optional[T_Node]):
        object.__setattr__(self, '_node', node)

    @property
    def node(self) -> T_Node:
        return object.__getattribute__(self, '_node')

    @node.setter
    def node(self, value: T_Node) -> None:
        object.__setattr__(self, '_node', value)

    def __bool__(self) -> bool:
        return self.node is not None

    def __getattr__(self, name: str) -> T_Node:
        if name == '_node':
            return object.__getattribute__(self, name)
        if self.node is None:
            raise AttributeError(f"Empty node has no attribute '{name}'")
        return getattr(self.node, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == '_node':
            object.__setattr__(self, name, value)
        else:
            if self.node is None:
                raise AttributeError(f"Can't set attribute '{name}' on empty node")
            setattr(self.node, name, value)

    @classmethod
    def unwrap(cls: type['KitBase[T_Node]'], other: 'KitBase[T_Node] | T_Node | None') -> T_Node | None:
        """
        提取包装类内部的原始节点。
        - 如果 other 是 KitBase 子类实例，返回其内部 _node。
        - 否则直接返回 other 本身（可能为 None）。
        """
        if isinstance(other, KitBase):
            # other._node 的类型理论上为 T_Node，但类型检查器无法自动收窄，使用 cast
            return cast(T_Node, other._node)
        return other
        
    def __eq__(self, other: Any) -> bool:
        return id(self.node) == id(self.unwrap(other))

class ListNodeKitBase(KitBase[T_NEXT]):
    """ 链表调试增强工具，使用代理模式（安全实现） 用法: link = ListNodeKit(head_node) """
    @property
    def next(self)->'ListNodeKitBase[T_NEXT]':
        if self.node is None:
            raise AttributeError(f"空链表不能使用 next 属性")
        # 关键：返回当前类的实例，保持装饰器效果延续
        return self.__class__(self.node.next)
    
    @next.setter
    def next(self, value: 'ListNodeKitBase[T_NEXT]|T_NEXT') -> None:
        """
        显式定义 setter，支持 kit.next = node 或 kit.next = other_kit
        """
        if self.node is None:
            raise AttributeError("Can't set attribute on None (empty ListNodeKitBase)")
        
        # 如果赋值的是包装类，提取其内部节点
        self.node.next = self.unwrap(value)

    # 使ListNodeKit可以像列表一样索引
    def __getitem__(self, index: int) -> 'ListNodeKitBase[T_NEXT]':
        if index < 0:
            raise IndexError("Negative index not supported")
        cur = self
        for _ in range(index):
            if cur: # 非空链表
                cur = cur.next
            else:
                raise IndexError("Index out of range")
        return cur
    
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
        node = self.node if isinstance(self, ListNodeKitBase) else self
        it = IterNext[T_NEXT](node)
        Node_List, stop_index = SafeIter.flatten(it, max_idx=max_len)
        return [node for idx, node in Node_List], stop_index

    def __iter__(self):
        """调用 SafeIter 安全地遍历，遍历完毕或在链表环节点前停止"""
        it = IterNext[T_NEXT](self.node)  # 👈 从原始节点开始
        return SafeIter(it)
    
    @classmethod
    def to_string(cls, head: Optional[T_NEXT], prep_property: str = "val" , max_len:int = 10**5) -> str:
        """安全打印链表，自动标记环（> 和 ^）"""
        nodes, stop_index = ListNodeKitBase[T_NEXT].flatten(head,max_len = max_len)        

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
            return self.to_string(self._node, prep_property)
        
        cls.__repr__ = __repr__

        return cls
    return wrapper

@runtime_checkable
class HasLR(Protocol):
    left: Optional[Any]
    right: Optional[Any]
# 定义支持 .left , .right 属性的协议（泛型约束）
T_LR = TypeVar("T_LR",bound=HasLR)

class LayeredTraversal(SafeIterBase[T_LR]):
    def __init__(self, root: Optional[T_LR]):
        # 基类构造函数会处理 root 的登记 (id:1)
        super().__init__(init_node=root, init_idx=1)
        self._queue = deque()

    def _push_children(self):
        # 此时 current_node 就是刚刚产出的那个节点
        if self._current_node is None: return
        # 探测子节点并尝试登记
        l_idx = self._current_idx * 2
        if self._check_safe(l_idx, self._current_node.left):
            self._queue.append((l_idx, self._current_node.left))
            
        if self._check_safe(l_idx + 1, self._current_node.right):
            self._queue.append((l_idx + 1, self._current_node.right))

    def _prepare_next(self):
        # 1. 先把当前节点的子节点入队
        self._push_children()

        # 2. 从队列取下一个
        if not self._queue:
            self._current_node = None
        else:
            self._current_idx, self._current_node = self._queue.popleft()

    def flatten(self, max_idx: Optional[int] = None):
        return super()._flatten(self, max_idx)


class HeapRoute(SafeIterBase[T_LR]):
    def __init__(self, init_node: 'T_LR', heap_index: int):
        super().__init__(init_node,1,True) # 从1开始索引，早停
        self.route_r = [op=='1' for op in bin(heap_index)[3:]]

    def _prepare_next(self):
        if not self.route_r:
            raise StopIteration
        if self._check_safe(self._current_idx,self._current_node):
            if self.route_r[0]:
                self._current_node = self._current_node.right
                self._current_idx = 2*self._current_idx+1
            else:
                self._current_node = self._current_node.left
                self._current_idx = 2*self._current_idx
            del self.route_r[0]
        else:
            raise StopIteration

class TreeNodeKitBase(KitBase[T_LR]):
    """
    二叉树调试增强工具基类，使用代理模式。
    提供安全的扁平化（层序遍历）和重复节点检测，避免因错误的树结构导致死循环。
    """

    @property
    def left(self) -> 'TreeNodeKitBase[T_LR]':
        if self.node is None:
            raise AttributeError("空树节点不能使用 left 属性")
        return self.__class__(self._node.left)

    @left.setter
    def left(self, value: 'TreeNodeKitBase[T_LR] | T_LR | None'):
        if self._node is None:
            raise AttributeError("空树节点不能设置 left 属性")
        self.node.left = self.unwrap(value)   # 使用 unwrap 简化

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

    def get(self,heap_index:int)-> 'TreeNodeKitBase[T_LR]':
        """按从1开始的堆索引获取节点，若节点无法访问则报错，但是注意若其父节点存在，但访问到该节点恰为空则返回 TreeNodeKitBase[None]"""
        if heap_index<1:
            raise IndexError("堆索引不能小于1")
        it = HeapRoute(self.node, heap_index)
        cur = None
        for idx,cur in it:
            if not cur:
                if it.repeat_idx:
                    raise IndexError("堆索引发现环路")
                raise IndexError("堆索引超出范围")
        # cur = self.node
        # op_list = bin(heap_index)[3:]
        # for op in op_list:
        #     if not cur:
        #         raise IndexError("堆索引超出范围")
        #     if op == '0':
        #         cur = cur.left
        #     else:
        #         cur = cur.right
        return TreeNodeKitBase(cur)

    def __getitem__(self, heap_index: int) -> 'TreeNodeKitBase[T_LR]':
        """按从1开始的堆索引获取节点，若节点不存在返回 TreeNodeKitBase[None]"""
        return self.get(heap_index)
    
    def flatten(self,max_depth:int|None = None) -> Tuple[List[Tuple[int, T_LR]], Optional[int]]:
        """层序遍历树，返回 (<完全二叉树索引键，节点>列表, 首次出现重复节点的键)。"""
        limit = None if max_depth is None else (2 ** (max_depth + 1))
        it = LayeredTraversal(self._node) 
        return it.flatten(limit)

    def layer_iter(self) -> SafeIterBase[T_LR]:
        """调用 SafeIter 安全地层序遍历，遍历完毕或出现重复节点时停止"""
        return LayeredTraversal[T_LR](self._node)
    

    def NLR_iter(self) -> SafeIterBase[T_LR]:
        """前序遍历迭代器 (NLR)"""
        return PreorderTraversal[T_LR](self._node)

    def LNR_iter(self) -> SafeIterBase[T_LR]:
        """中序遍历迭代器 (LNR)"""
        return InorderTraversal[T_LR](self._node)

    def LRN_iter(self) -> SafeIterBase[T_LR]:
        """后序遍历迭代器 (LRN)"""
        return PostorderTraversal[T_LR](self._node)
    
    def __iter__(self):
        """默认返回层序遍历迭代器"""
        return self.layer_iter()
    
    @classmethod
    def to_string(cls, root: TreeNodeKitBase[T_LR]|T_LR|None, prep_property = "val", max_depth=10) -> str:
        """
        生成树的字符串表示，包含：
        - 树形结构（使用 binarytree 库）
        - 完全二叉树索引与节点值的映射
        - 重复节点键（若存在环）
        """
        node:Optional[T_LR] = TreeNodeKitBase.unwrap(root) # 兼容包装类成员函数和静态函数输入原生类两种方式
        if node is None:
            return "<class 'TreeNodeKit'>: empty"
        
        # 遍历展开并获取节点与索引的映射
        it = LayeredTraversal[T_LR](node)
        max_index = 2**max_depth
        idx_node, stop_idx = it.flatten(max_idx=max_index)

        # 构建索引到节点值的映射
        idx_val = {idx: getattr(n, prep_property) for idx, n in idx_node}

        # 构建用于 binarytree.build 的层序列表
        if idx_val:
            max_idx = max(idx_val.keys())
            level_list = [""] * max_idx          # 索引从 1 开始，列表长度 = 最大索引
            for idx, val in idx_val.items():
                # 转换为字符串供 build 使用
                level_list[idx - 1] = f"{'*'if idx == stop_idx else ''}{idx}"     
            try:
                bt = build(level_list)
                tree_str = str(bt) if bt else "null"
            except Exception:
                tree_str = "Error: binarytree build failed"
        else:
            tree_str = "null"
        
        # 构建各部分字符串
        parts = [
            f'  "stop_by_duplicate_idx": {stop_idx}'if stop_idx is not None and stop_idx<max_index else None,
            '  "tree_by_idx": """{}{}"""'.format(
                tree_str, 
                '...\n' if stop_idx == max_index else ''
            ),
            f'  "idx:val": {idx_val}'
        ]

        # 组合最终输出
        body = ",\n".join(filter(bool,parts))
        return f"<class 'TreeNodeKit'>: {{\n{body}\n}}"
    
    
    # ===================== 新增三个遍历迭代器 =====================

class PreorderTraversal(SafeIterBase[T_LR]):
    def __init__(self, root: Optional[T_LR]):
        super().__init__(root, 1) # 初始 current_node 为 None，由 prepare_next 填充
        self._stack:List[Tuple[int,T_LR]] = []
        
        # 2. 初始化时直接把 root 的子节点压栈（因为 root 已经准备好产出了）
        if root:
            self._push_children(1,root)

    def _push_children(self, node_idx ,node):
        """前序压栈：先右后左，保证左子先出"""
        left_idx = 2 * node_idx

        # 反向压栈：先右后左，保证左子在栈顶先被处理
        if self._check_safe(left_idx+1, node.right):
            self._stack.append((left_idx+1, node.right)) # type: ignore
        if self._check_safe(left_idx, node.left):
            self._stack.append((left_idx, node.left)) # type: ignore

    def _prepare_next(self):
        """
        前序逻辑：弹出栈顶作为当前节点，并立即压入其右、左子节点（顺序保证左先被访问）
        """
        if not self._stack:
            self._current_node = None
            return

        # 1. 取出下一个要产出的节点
        self._current_idx, self._current_node = self._stack.pop()
        
        # 2. 立即把这个新节点的子节点压栈，为下一次迭代做准备
        self._push_children(self._current_idx, self._current_node)

class InorderTraversal(SafeIterBase[T_LR]):
    """中序遍历迭代器 (LNR)"""
    def __init__(self, root: Optional[T_LR]):
        # 初始 current 设为 None，由下探逻辑确定第一个产出节点
        super().__init__(None, 0)
        self._stack: List[Tuple[int, T_LR]] = []
        
        if root and self._check_safe(1, root):
            self._stack.append((1, root))
            self._push_left(1, root)
            # 栈顶即为最左节点
            if self._stack:
                self._current_idx, self._current_node = self._stack[-1]

    def _push_left(self, idx: int, node: T_LR):
        """下探左子树，入栈即登记"""
        curr = node
        curr_idx = idx
        while curr.left:
            curr_idx *= 2
            if not self._check_safe(curr_idx, curr.left):
                # 发现环，记录后中断下探
                break
            self._stack.append((curr_idx, curr.left))
            curr = curr.left

    def _prepare_next(self):
        # 1. 弹出刚刚产出的节点
        if not self._stack:
            self._current_node = None
            return
        
        _, old_node = self._stack.pop()

        # 2. 尝试转向右子树
        if old_node.right:
            # 右子节点在完全二叉树中的索引
            r_idx = self._current_idx * 2 + 1
            if self._check_safe(r_idx, old_node.right):
                self._stack.append((r_idx, old_node.right))
                self._push_left(r_idx, old_node.right)
            else:
                # 右侧有环，记录 repeat_idx (在 _check_safe 内部已完成)
                # 关键：这里不要设为 None，保持现状，让下面的逻辑从栈中取父节点
                pass 
        
        # 3. 确定下一个产出目标（可能是刚才转向右树压入的，也可能是更上层的父节点）
        if self._stack:
            self._current_idx, self._current_node = self._stack[-1]
        else:
            self._current_node = None

class PostorderTraversal(SafeIterBase[T_LR]):
    """后序遍历迭代器 (LRN)"""
    def __init__(self, root: Optional[T_LR]):
        super().__init__(None, 0)
        # 栈存储 (索引, 节点, 是否已访问子节点)
        self._stack: List[Tuple[int, T_LR, bool]] = []
        
        if root and self._check_safe(1, root):
            self._stack.append((1, root, False))
            self._current_node = self._find_next_post_node()
        
    def _find_next_post_node(self) -> Optional[T_LR]:
        while self._stack:
            idx, node, visited = self._stack[-1]
            
            if visited:
                # 已经标记为 True，说明子节点都处理（或尝试处理）过了，弹出并产出
                self._stack.pop()
                self._current_idx = idx
                return node
            
            # 1. 标记当前节点为已访问
            self._stack[-1] = (idx, node, True)
            
            # 2. 尝试压入子节点。注意：即便这里 _repeat_idx 已经有值（之前的路径撞过环），
            # 只要当前的子节点是安全的，就应该压入。
            
            # 后序压栈顺序：右、左（保证弹出顺序为左、右）
            r_node = getattr(node, 'right', None)
            if r_node:
                # _check_safe 内部如果撞环会记录 repeat_idx，但我们依然要看左边
                if self._check_safe(idx * 2 + 1, r_node):
                    self._stack.append((idx * 2 + 1, r_node, False))
            
            l_node = getattr(node, 'left', None)
            if l_node:
                if self._check_safe(idx * 2, l_node):
                    self._stack.append((idx * 2, l_node, False))
                    
            # 3. 继续循环。如果刚才压入了 l_node，下一轮会去处理 l_node；
            # 如果左右都撞环或为空，下一轮会执行上面的 if visited 分支弹出当前节点。
        return None


    def _prepare_next(self):
        # 寻找下一个后序产出点
        self._current_node = self._find_next_post_node()
