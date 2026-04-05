from typing import Any, Callable, Dict, List, Tuple, Union, Optional, get_type_hints, get_args, get_origin,Generic,TypeVar,Iterator,Hashable,Deque,Iterable,Protocol, runtime_checkable ,cast
from collections import deque,defaultdict
from itertools import chain
from typing_extensions import Self
from binarytree import build
import json
import numpy as np
import cython
from args_parser_tools import KitBase,_formated_string
from safe_iter_base import SafeIterBase

__DEBUG__ = False


@runtime_checkable
class HasNext(Protocol):
    next: Optional[Any]
# 定义支持 .next 属性的协议（泛型约束）
T_NEXT = TypeVar("T_NEXT",bound=HasNext)

# 用于 ListNodeKit
class IterNext(SafeIterBase):
    """安全链表迭代器，继承 SafeIterBase 实现环检测，自动解包包装类。"""
    def __init__(self, head: KitBase[T_NEXT]|T_NEXT|None,getitem_null_end=True):
        super().__init__(
            init_node= KitBase.unwrap(head) ,
            init_idx=0, early_stop=False, 
            getitem_null_end=getitem_null_end)

    def _clone_from_start(self):
        return IterNext(self._current_node)

    def _prepare_next(self) -> None:
        """移动到下一个节点，并自动解包包装类。"""
        if self._current_node is None:
            return
        self._current_idx += 1
        nxt = self._current_node.next

        # 防御性编程：如果下一个节点是包装类，提取原始节点
        nxt = KitBase.unwrap(nxt)

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

        it = IterNext(self)

        items, stop_idx = SafeIterBase._flatten(it, None if max_len is None else max_len-1)

        if __DEBUG__:
            assert len(stop_idx)<=1

        return [node for idx, node in items], stop_idx[0] if stop_idx else None

    def __iter__(self):
        """返回安全链表迭代器"""
        return IterNext(KitBase.unwrap(self))
    
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
    