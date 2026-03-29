from args_parser import TreeNode, TreeNodeKit

# 构建树:       1
#            /   \
#           2     3
#          / \   /
#         4   5 6
root = TreeNode(1)
root.left = TreeNode(2)
root.right = TreeNode(3)
root.left.left = TreeNode(4)
root.left.right = TreeNode(5)
root.right.left = TreeNode(6)

kit = TreeNodeKit(root)
print(kit)                     # <TreeNodeKit: [1,2,3,4,5,6]>
print(kit.left.right.val)      # 5
print(kit[4].val)              # 索引4对应节点5（层序遍历索引）
print(kit[2].val)              # 索引2对应节点3

# 空树处理
empty = TreeNodeKit(None)
print(bool(empty))             # False
try:
    empty.left
except AttributeError as e:
    print(e)                   # "空树节点不能使用 left 属性"

# 环检测（如右子树指向自身）
root.right = root
kit_cycle = TreeNodeKit(root)
nodes, cycle_idx = kit_cycle.flatten()
print(cycle_idx)               # 某个非None值，表示环起始位置