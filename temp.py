from tools.args_parser import *
head = List2ListNode([1,2,3,4,5])
ListNodeKit(head)[4].next = head  # 创建环

# 安全检测
nodes, cycle_idx = ListNodeKit(head).flatten()
assert cycle_idx == 0  # 环起点在索引0

# 访问 val
val2 = ListNodeKit(head)[2].val