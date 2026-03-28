from tools.args_parser import *
head = List2ListNode([1,2,3,4,5])
ListNodeKit(head)[4].next = head  # 创建环

# 安全检测
nodes, cycle_idx = ListNodeKit(head).flatten()
assert cycle_idx == 0  # 环起点在索引0

# 验证链表未被篡改
student_result = solve(head)
after_nodes, _ = ListNodeKit(student_result).flatten()
assert after_nodes == nodes  # 确保学生未修改链表结构