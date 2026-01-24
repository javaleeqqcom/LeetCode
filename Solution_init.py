# Solution_init.py
from typing import *
from math import inf, isinf, isnan
from collections import deque, defaultdict, Counter

# 示例：LeetCode 常见结构（学生可按题追加）
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

    def __repr__(self):
        vals = []
        cur = self
        while cur:
            vals.append(str(cur.val))
            cur = cur.next
            if len(vals) > 20:  # 防止无限循环
                vals.append("...")
                break
        return "ListNode[" + ",".join(vals) + "]"

# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

# ====== 转换函数 ======
def List2ListNode(lst: List[int]) -> Optional[ListNode]:
    if not lst:
        return None
    head = ListNode(lst[0])
    cur = head
    for val in lst[1:]:
        cur.next = ListNode(val)
        cur = cur.next
    return head


def List2TreeNode(level_order: List[Optional[int]]) -> Optional[TreeNode]:
    if not level_order or level_order[0] is None:
        return None
    from collections import deque
    root = TreeNode(level_order[0])
    q = deque([root])
    i = 1
    while q and i < len(level_order):
        node = q.popleft()
        if i < len(level_order) and level_order[i] is not None:
            node.left = TreeNode(level_order[i])
            q.append(node.left)
        i += 1
        if i < len(level_order) and level_order[i] is not None:
            node.right = TreeNode(level_order[i])
            q.append(node.right)
        i += 1
    return root


def build_graph(n: int, edges: List[List[int]]) -> Any:
    # 示例：返回邻接表
    graph = [[] for _ in range(n)]
    for u, v in edges:
        graph[u].append(v)
        graph[v].append(u)
    return graph


# ====== 【核心】注册转换规则 ======
# 键：(目标类型名, 输入类型签名...)
# 值：转换函数
input_parser_registry = {
    ("ListNode",): lambda args: List2ListNode(args[0]),
    ("TreeNode",): lambda args: List2TreeNode(args[0]),
    ("Graph", int, list): lambda args: build_graph(args[0], args[1]),
    # 可继续添加：
    # ("MyClass", str, int, list): lambda args: MyClass(args[0], args[1], args[2]),
}