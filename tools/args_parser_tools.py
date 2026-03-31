from typing import Any, Callable, Dict, List, Tuple, Union, Optional, get_type_hints, get_args, get_origin,Generic,TypeVar,Iterator,Hashable,Deque,Iterable,Protocol, runtime_checkable ,cast
from collections import deque
from binarytree import build
import json

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
class SafeIterBase(Iterator[Tuple[int,T]]):
    def __init__(self, init_node: Optional[T] = None, init_idx: int = 0):
        self._seen: Dict[int, int] = {}  # id(node) -> index
        self._repeat_idx: Optional[int] = None  # 记录重复节点的索引
        self._current_node = init_node
        self._current_idx = init_idx

    def _check_safe(self, node: Optional[T]) -> bool:
        """
        子类在压栈/入队前调用此方法。
        仅当节点有效且未访问过，返回 True。
        如果发现重复，记录索引并返回 False。
        """
        if node is None:
            return False
        nid = id(node)
        if nid in self._seen:
            self._repeat_idx = self._seen[nid]
            return False
        return True

    # def __iter__(self): 已继承 Iterator 实现

    def __next__(self) -> Tuple[int, T]:
        # 1. 检查是否有环或结束
        if self._current_node is None or self._repeat_idx is not None:
            raise StopIteration
            
        # 2. 产出前正式登记 (此时才分配索引)
        node_id = id(self._current_node)
        self._seen[node_id] = self._current_idx
        
        res = (self._current_idx, self._current_node)
        
        # 3. 准备下一个
        self._prepare_next()
        return res

    def _prepare_next(self):
        """抽象方法：由子类实现，更新 _current_node"""
        raise NotImplementedError

    @property
    def repeat_idx(self) -> Optional[int]:
        """当迭代器检测到重复节点时，会赋值该属性为重复节点的索引，否则为 None"""
        return self._repeat_idx

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
        return items, it.repeat_idx

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
        # 初始化基类，当前节点设为 root
        # 注意：我们不立即把 root 放入队列，而是由基类管理 current_node
        super().__init__(init_node=root, init_idx=1)
        self._queue:Deque[Tuple[int,T_LR]] = deque() # 存储 (index, node) 元组

        # 如果根节点存在且安全，将其放入队列作为后续候选
        # current_node 将在第一次 __next__ 时被产出
        if self._check_safe(root):
            self._push()

    def _push(self):
        left_child = getattr(self._current_node, 'left')
        right_child = getattr(self._current_node, 'right')
        # 根节点索引通常为 1 (完全二叉树标准)
        if self._check_safe(left_child):
            self._queue.append((self._current_idx * 2, left_child))
        if self._check_safe(right_child):
            self._queue.append((self._current_idx * 2 + 1, right_child))
        
    def _prepare_next(self):
        if not self._queue:
            self._current_node = None
            return

        # 取出下一个节点
        self._current_idx, self._current_node = self._queue.popleft()
        self._push()

    def flatten(self, max_idx: Optional[int] = None):
        return super()._flatten(self, max_idx)

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

    def __getitem__(self, index: int) -> 'TreeNodeKitBase[T_LR]':
        """按层序遍历顺序索引...若树非法...节点可能出现重复，停止迭代并报错"""
        if index < 0:
            raise IndexError("索引不能为负数")
        safe_iter = LayeredTraversal(self._node)
        node_count = 0
        for i, (_, node) in enumerate(safe_iter):
            node_count += 1
            if i == index:
                return self.__class__(node)
        # 迭代提前终止，可能因为环或正常结束
        if safe_iter.repeat_idx is not None:
            raise IndexError(
                f"索引 {index} 访问时遇到环或重复节点，首次重复键为 {safe_iter.repeat_idx}。"
                f"已遍历 {node_count} 个节点后检测到重复。"
            )
        else:
            # 正常结束，节点总数 = node_count
            raise IndexError(
                f"索引 {index} 超出节点总数（共 {node_count} 个节点）。"
            )
    
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

class PreorderTraversal(SafeIterBase[T]):
    def __init__(self, root: Optional[T]):
        super().__init__(None, 0) # 初始 current_node 为 None，由 prepare_next 填充
        self._stack = []
        
        # 关键：在压栈前检查
        if root and self._check_safe(root):
            self._stack.append(root)
            self._prepare_next() # 初始化第一个节点

    def _prepare_next(self):
        """
        前序逻辑：弹出栈顶作为当前节点，并立即压入其右、左子节点（顺序保证左先被访问）
        """
        if not self._stack:
            self._current_node = None
            return

        # 弹出栈顶作为下一个产出的节点
        node = self._stack.pop()
        self._current_node = node
        self._current_idx += 1 # 简单递增索引

        # 反向压栈：先右后左，保证左子在栈顶先被处理
        # 压栈前必须检查安全
        # 注意：这里我们只检查是否入栈，实际产出在 __next__ 中登记
        right_child = getattr(node, 'right', None)
        left_child = getattr(node, 'left', None)

        # 压栈顺序决定了访问顺序
        if right_child and self._check_safe(right_child):
            self._stack.append(right_child)
        if left_child and self._check_safe(left_child):
            self._stack.append(left_child)

class InorderTraversal(SafeIterBase[T_LR]):
    def __init__(self, root: Optional[T_LR]):
        super().__init__(None, 0)
        self._stack = []
        if root and self._check_safe(root):
            self._push_left(root)
            if self._stack:
                self._current_node = self._stack[-1]

    def _push_left(self, node: T_LR):
        """下探左子树，带查重"""
        curr = node
        while curr.left:
            if not self._check_safe(curr.left): # 关键：下探即查重
                break
            self._stack.append(curr.left)
            curr = curr.left

    def _prepare_next(self):
        self._current_idx += 1
        # 1. 弹出已产出的当前节点
        old_node = self._stack.pop() if self._stack else None
        
        # 2. 尝试转向右子树
        if old_node and old_node.right:
            if self._check_safe(old_node.right):
                # 如果右子树安全，压入右子及其所有左子
                self._stack.append(old_node.right)
                self._push_left(old_node.right)
            else:
                # 发现环，终止
                self._current_node = None
                return

        self._current_node = self._stack[-1] if self._stack else None

class PostorderTraversal(SafeIterBase[T_LR]):
    def __init__(self, root: Optional[T_LR]):
        super().__init__(None, 0)
        self._stack = []
        if root and self._check_safe(root):
            self._stack.append((root, False))
            self._current_node = self._find_next_post_node()

    def _find_next_post_node(self) -> Optional[T_LR]:
        while self._stack:
            node, visited = self._stack[-1]
            if visited:
                return self._stack.pop()[0] # 真正返回节点
            else:
                # 标记为已访问，并尝试压入子节点
                self._stack[-1] = (node, True)
                # 后序压栈顺序：右、左（保证弹出顺序为左、右）
                for child in [node.right, node.left]:
                    if child:
                        if self._check_safe(child):
                            self._stack.append((child, False))
                        else:
                            # 发现环！停止下探并直接触发终止状态
                            # 这里返回 None 会让 _current_node 为 None，
                            # 随后基类 __next__ 会发现 repeat_idx 已被 _is_safe 设置
                            return None 
                # 压入子节点后，需要继续下探直到找到叶子
                # 逻辑会回到 while 循环顶部处理刚压入的 (left, False)
        return None

    def _prepare_next(self):
        self._current_idx += 1
        self._current_node = self._find_next_post_node()
