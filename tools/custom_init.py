from typing import Any, Dict, Tuple, Callable ,Union,List
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

    def __repr__(self) -> str:
        # 按完全二叉树生成字符串表示，空节点用 null 占位

# ====== 转换函数 ======
def List2ListNode(lst: List[Any]) -> Optional[ListNode]:
    head = ListNode(lst[0])
    cur = head
    for val in lst[1:]:
        cur.next = ListNode(val)
        cur = cur.next
    return head


def List2TreeNode(level_order: List[Any]) -> Optional[TreeNode]:
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
# 注册表：键 = (目标类型, 源类型)，值 = 转换函数
input_parser_registry: Dict[Tuple[Any, Any], Callable] = {
    (ListNode, list): List2ListNode,
    (TreeNode, list): List2TreeNode,
    # 可扩展，例如：
    # (Optional[ListNode], list): lambda x: List2ListNode(x) if x else None,
}