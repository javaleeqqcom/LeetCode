
from typing import Any, Optional, List, Tuple, Dict, Iterator, TypeVar, Protocol, runtime_checkable, cast
from collections import deque
from args_parser import ListNode
import sys

# 导入辅助函数（避免重复实现）
from .args_parser_tools import _formated_string, KitBase

class KitBase2(KitBase):
    def __hash__(self) -> int:
        """基于原生节点内存地址的哈希，用于环检测"""
        return id(self._node)

    def __eq__(self, other: Any) -> bool:
        """比较两个包装节点是否包装同一个原生节点"""
        other_raw = self.unwrap(other)
        return self._node is other_raw

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)
    
if __name__ == "__main__":
    D = dict()
    a = ListNode(17)
    b = ListNode(31)
    A1 = KitBase2(a)
    A2 = KitBase2(a)
    D[A1] = [1]
    print(D[A1])
    L1 = D[A1]
    L1.append(2)
    print(D[A2])

    A2._node = b
    print(A2.val)
    print(D[A2])