# run_solution.py
import types
from charset_normalizer import from_bytes  # 自动检测编码（支持中文注释/变量）
from tools.custom_init import ListNode, TreeNode, input_parser_registry

# ========== 1. 安全读取学生代码（自动识别编码） ==========
with open('P82_V0.py', 'rb') as f:
    raw = f.read()
    # 智能检测编码（UTF-8/GBK/BOM等），失败时回退
    result = from_bytes(raw).best()
    student_code = str(result) if result else raw.decode('utf-8', errors='ignore')

# ========== 2. 创建隔离执行环境（关键！） ==========
mod = types.ModuleType('student_solution')
# 注入LeetCode环境必备类型（与input_parser_registry完全一致）
mod.__dict__.update({
    'ListNode': ListNode,
    'TreeNode': TreeNode,
    # 可选：注入常用typing类型避免学生代码import失败
    'Optional': __import__('typing').Optional,
    'List': __import__('typing').List,
    'Dict': __import__('typing').Dict,
})
# 保留标准库导入能力
mod.__dict__['__builtins__'] = __builtins__

# ========== 3. 执行学生代码（在隔离环境中） ==========
exec(student_code, mod.__dict__)
Solution = mod.Solution  # 获取Solution类（其内部ListNode指向custom_init.ListNode）

# ========== 4. 测试验证 ==========
obj = Solution()
# 自动转换：list → ListNode（registry匹配成功）
head = input_parser_registry[(ListNode, list)]([1, 2, 3, 3, 4, 4, 5])
result = obj.deleteDuplicates(head)
print("转换后类型:", type(head))  # 应为 <class 'tools.custom_init.ListNode'>
print("结果:", result)