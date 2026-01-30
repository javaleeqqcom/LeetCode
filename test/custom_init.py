# Solution_init.py
from base_init import *

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
def List2ListNode(lst: list) -> Optional[ListNode]:
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


# ====== 【核心】注册转换规则 ======
# 键：(目标类型名, 输入类型签名...)
# 值：转换函数
input_parser_registry = {
    ("ListNode","list"): lambda args: List2ListNode(args[0]),
    # 要特别注意 TreeNode 的输入如： [1,2,null,4] 的 null 表示占位空节点，用于凑齐完全二叉树，因此其输入类型不是 List，而是应当为 str。
    ("TreeNode","str"): lambda args: List2TreeNode(args[0]), 
    # 可继续添加：
    # ("MyClass", int , str, List[int]): lambda args: MyClass(args[0], args[1], args[2]),
}