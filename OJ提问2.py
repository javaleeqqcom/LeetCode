from tools.AIConsultation import AIConsultation as AIC

Question = AIC(r"Question\Q4. Maximum Sum of M Non-Overlapping Subarrays II\题目.txt")
AC_code = AIC(r"Question\Q4. Maximum Sum of M Non-Overlapping Subarrays II\V4.1.0.py")

template_text = fr"""
{Question}
我的 AC 代码
{AC_code}
现在需要写题解
{AIC(r"Question\Q4. Maximum Sum of M Non-Overlapping Subarrays II\题解V0.md")}
参考资料
{AIC(r"Question\Q4. Maximum Sum of M Non-Overlapping Subarrays II\手续费股票买卖贪心思路参考.txt")}
要求言简意赅！
```
输入
nums =
[8,5]
m =
1
l =
1
r =
1
标准输出
presum: [ 0  8 13]
dp[0]: (0, 0)
dp[1]: (2, -1)
dp[2]: (2, -1)
((2, 1)) <- f(0≤6<13)
dp[0]: (0, 0)
dp[1]: (5, -1)
dp[2]: (7, -2)
((7, 2)) <- f(0≤3<6)
dp[0]: (0, 0)
dp[1]: (3, -1)
dp[2]: (3, -1)
((3, 1)) <- f(4≤5<6)
dp[0]: (0, 0)
dp[1]: (4, -1)
dp[2]: (5, -2)
((5, 2)) <- f(4≤4<5)
收起
输出
10
预期结果
8
```
"""

# 使用示例
line_count = template_text.count('\n')
print(f"待合并文本共 {line_count} 行")

if AIC.copy_to_clipboard(template_text):
  print("✅ 已成功复制到剪贴板。")
else:
  print("❌ 复制失败，请检查系统环境。")


# - 原 safe_iter_kit.pyx 有一个风险点，对于树，其 stack 和 queue 并没有持有原生节点的引用计数
# - 因此需要修改为入 stack（queue） 就增加引用，而 check_safe 仅当为重复（in _seen 为真）时减少引用计数，销毁时按 _seen 减少引用计数