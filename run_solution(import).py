from typing import List, Tuple, Dict, Set, Optional, Any, Union, Callable, Iterable
# run_solution.py

# ====== 重要：提前注入全局类 ======
from tools.custom_init import ListNode, TreeNode, input_parser_registry

# 将类注入到全局命名空间（确保 P82_V0.py 能找到）
globals()['ListNode'] = ListNode
globals()['TreeNode'] = TreeNode

# ====== 正常导入 Solution ======
from P82_V0 import Solution

# run = SolutionRunner(Solution)
# cases = run.read_test_case("P82q1.txt")
# print(cases)
# results = run.run(cases,log_suffix= "_V0")
# print(results)
obj = Solution()
res = obj.deleteDuplicates(input_parser_registry[(ListNode, list)]([1, 2, 3, 4, 5]))
print( res)