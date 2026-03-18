from typing import Any, Dict, Tuple, Callable ,Union,List ,Optional
from collections import deque
import math,os,random # leetcode 平台会自动嵌入一些常用库，学生无需导入也能执行

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
        return "<ListNode>:\n[" + ",".join(vals) + "]"

# ====== 转换函数 ======
def List2ListNode(lst: List[Any]) -> Optional[ListNode]:
    head = ListNode(lst[0])
    cur = head
    for val in lst[1:]:
        cur.next = ListNode(val)
        cur = cur.next
    return head

# 若方法需要返回一个 ListNode，则必须实现 ListNode2List ，以便测试结果的对比
def ListNode2List(node: Optional[ListNode]) -> List[Any]:
    res = []
    while node is not None:
        res.append(node.val)
        node = node.next
    return res

# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        # 用于 log / repr：返回完全二叉树层序列表表示（含 null）
        lst = TreeNode2List(self)
        return f"<TreeNode>: {lst}"

    def print(self) -> str:
        """返回美观的树形字符串（仅限前几层，适合人类阅读）"""
        if not self:
            return "<empty tree>"
        
        # 第一步：按层收集节点（保留 None 占位，但叶子层之后不再扩展）
        levels = []
        q = deque([self])
        max_levels = 5  # 最多打印5层以防过长
        
        while q and len(levels) < max_levels:
            level_size = len(q)
            current_level = []
            has_non_null = False
            
            for _ in range(level_size):
                node = q.popleft()
                current_level.append(node)
                if node is not None:
                    q.append(node.left)
                    q.append(node.right)
                    if node.left or node.right:
                        has_non_null = True
                else:
                    q.append(None)
                    q.append(None)
            
            levels.append(current_level)
            # 如果本层全是 None 或已到最大层数，则停止
            if not has_non_null or len(levels) >= max_levels:
                break
        
        # 第二步：从最后一层开始向上构建字符串（自底向上对齐）
        # 先将每层转为字符串
        str_levels = []
        for level in levels:
            str_level = []
            for node in level:
                if node is None:
                    str_level.append("null")
                else:
                    str_level.append(str(node.val))
            str_levels.append(str_level)
        
        # 第三步：计算每层所需宽度并居中对齐
        # 从最底层开始，确定每个节点占据的宽度
        spacing = 4  # 叶子节点间的最小间隔
        lines = []
        n = len(str_levels)
        # 最底层宽度决定整体布局
        bottom_widths = [len(s) for s in str_levels[-1]]
        # 每个位置的起始坐标（字符列）
        pos = [(sum(bottom_widths[:i]) + i * spacing) for i in range(len(bottom_widths))]
        
        # 自底向上生成每一行
        for i in reversed(range(n)):
            level_strs = str_levels[i]
            # 当前层节点数
            num_nodes = len(level_strs)
            # 计算当前层每个节点在底层对应的中心位置
            centers = []
            step = len(pos) // num_nodes if num_nodes > 0 else 1
            for j in range(num_nodes):
                start_idx = j * step
                end_idx = (j + 1) * step
                if start_idx < len(pos):
                    center_pos = (pos[start_idx] + (pos[end_idx - 1] if end_idx <= len(pos) else pos[-1])) // 2
                    centers.append(center_pos)
                else:
                    centers.append(0)
            
            # 构建当前行字符串
            line_len = max(centers) + max(len(s) for s in level_strs) if centers else 0
            line = [' '] * (line_len + 1)
            for j, s in enumerate(level_strs):
                if j < len(centers):
                    start = centers[j]
                    for k, char in enumerate(s):
                        if start + k < len(line):
                            line[start + k] = char
            lines.append(''.join(line).rstrip())
        
        # 反转回从根到叶的顺序
        return '\n'.join(reversed(lines))
    
def TreeNode2List(root: Optional[TreeNode]) -> List[Any]:
    """将 TreeNode 转换为完全二叉树层序列表（含 None 占位）"""
    if not root:
        return []
    
    result = []
    q = deque([root])
    while q:
        node = q.popleft()
        if node is None:
            result.append(None)
        else:
            result.append(node.val)
            q.append(node.left)
            q.append(node.right)
    
    # 去除尾部多余的 None（保持与输入格式一致）
    while result and result[-1] is None:
        result.pop()
    
    return result

def List2TreeNode(level_order: List[Any]) -> Optional[TreeNode]:
    if not level_order or level_order[0] is None:
        return None
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
input_parser_registry: Dict[Tuple[type, type], Callable] = {
    (list, ListNode): List2ListNode,
    (list, TreeNode): List2TreeNode,
    # 可按需求扩展
}

output_parser_registry: Dict[type,Callable] = {
    ListNode : ListNode2List,
    TreeNode : TreeNode2List
}