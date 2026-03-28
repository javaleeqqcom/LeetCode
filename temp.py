# --- 测试用例 ---
from tools.args_parser_tools import *
from tools.args_parser import *

@ListNodeKitDecorator(prep_property="val")
class ListNodeKit(ListNode):
    pass

# 1. 构造模式
pk2 = ListNodeKit(2, None)
print(f"构造模式: {pk2.val}") # 2

# 2. 包装模式
p1 = ListNode(1, None)
pk1 = ListNodeKit(p1)
print(f"包装模式: {pk1.val}") # 1

# 3. 链式操作与环检测
pk1.next = pk2
pk2.next = pk1 # 成环
print(pk1) # <ListNodeKit>:[>,1,2,^]

# 4. 索引访问
print(f"Index 1 val: {pk1[1].val}") # 2