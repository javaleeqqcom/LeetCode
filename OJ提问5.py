from tools.AIConsultation import AIConsultation as AIC

Question = AIC(r"Question\Q4. Maximum Sum of M Non-Overlapping Subarrays II\题目.txt")
AC_code = AIC(r"Question\Q4. Maximum Sum of M Non-Overlapping Subarrays II\V3.2.py")
WG_code = AIC(r"Question\Q4. Maximum Sum of M Non-Overlapping Subarrays II\V3.2.py")
ST_code = AIC(r"Question\Q4. Maximum Sum of M Non-Overlapping Subarrays II\standard.py")
Base = AIC(r"Question\Q4. Maximum Sum of M Non-Overlapping Subarrays II\ShowBase.py")

template_text = fr"""
非常棒，你写的代码正确，现在需要润色题解的第2章（附全文以便上下文通顺）
{AIC(r"Question\Q4. Maximum Sum of M Non-Overlapping Subarrays II\题解V2.2.md")}
其中第1章是新版本的，语言幽默风趣言简意赅，其余章节需要延续修改为符合第1章的定义和文风。
你只需回答第2章，并且要顺着我的草稿，尤其是2.4节中的插图都是用如上程序生成，你需要补全图例说明，上下文也需关联图例。
另外为了说明负收益的例子，2.4.2用如下程序来生成图例：
```py
# 样例输入（与 Key_Case0.py 一致）
nums = [-10,4,-6,5,-8,7,-8,6]
m = 3
l = 2
r = 2

base_obj = Base(nums, l, r)       # 用于 WQS，避免内部状态冲突
ans, record = base_obj.WQS(m)     # record: list of (profit, times, fee)

# 为了全面展示 WQS 过程，需要将 WQS 迭代出现的最大交易次数+1 作为交易次数上限
m_max = max(times for profit, times, fee in record) + 2
# 求 最大收益(交易次数) 函数表
f_vals = base_obj.get_f(m_max)          # 长度 m_max+1 的列表，索引 c 对应 dp[c][-1]

print("f(c):", f_vals)
print("最终答案:", ans)
print("WQS 迭代记录 (profit, 交易次数, fee):")
for item in record:
    print(item)
((0, 0)) <- f(-1≤7<16)
((0, 0)) <- f(-1≤3<7)
((0, 0)) <- f(-1≤1<3)
((0, 0)) <- f(-1≤0<1)
((0, 0)) <- f(-1≤-1<0)
f(c): [0, -1, -2]
最终答案: -1
WQS 迭代记录 (profit, 交易次数, fee):
(0, 0, 7)
(0, 0, 3)
(0, 0, 1)
(0, 0, 0)
(0, 0, -1)
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