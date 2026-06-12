from tools.AIConsultation import AIConsultation as AIC

Question = AIC(r"Question\Q4. Maximum Sum of M Non-Overlapping Subarrays II\题目.txt")
AC_code = AIC(r"Question\Q4. Maximum Sum of M Non-Overlapping Subarrays II\V3.2.py")
WG_code = AIC(r"Question\Q4. Maximum Sum of M Non-Overlapping Subarrays II\V3.2.py")
ST_code = AIC(r"Question\Q4. Maximum Sum of M Non-Overlapping Subarrays II\standard.py")
Base = AIC(r"Question\Q4. Maximum Sum of M Non-Overlapping Subarrays II\ShowBase.py")

template_text = fr"""
非常棒，你写的代码正确（TLE），现在需要作图，一共2类图：
图A： nums[round(x-0.5)] 柱状图正浅红、负浅绿在底层，叠加 presum[x]折线图，如此折线两端点的x范围恰好夹住柱状图的x范围，表示其累积和。
图B： 以 y = f(c) = dp[c][-1] 为折线图、WQS 二分所用的 y=f(c)-fee*c 切线为不同颜色虚线，一次展示迭代过程。
以如下样例输入为例，因为该输入出现了 WQS切线 与 y=f(c) 有重交点的情况：
{AIC(r"Question\Q4. Maximum Sum of M Non-Overlapping Subarrays II\Key_Case0.py")}
你需要调用如下基础库（已在平台验证不会WA），作为作图的函数调用基础：
{Base}
然后写 ipynb 调用 Base（同文件夹），作图打印字体不支持中文，请用英文表达，但是代码的注释保持中文。
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