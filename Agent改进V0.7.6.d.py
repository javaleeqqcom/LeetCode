from tools.AIConsultation import AIConsultation as AIC

README = AIC(r"README.md")

debug_retriever = AIC(r"rag\debug_retriever.py")
RAG_DEBUG = AIC(r"RAG_DEBUG.txt")
embedding = AIC(r"rag\embedding.py")
retriever=AIC(r"rag\retriever.py")
index_builder = AIC(r"rag\index_builder.py")
RAG_DOC = AIC(r"rag\RAG_DOC.md")

AGENTS_DOC = AIC(r"agents\AGENTS_DOC.md")
agent_io = AIC(r"agents\agent_io.py")
analyze_agent = AIC(r"agents\analyze_agent.py")
build_graph = AIC(r"agents\build_graph.py")
case_generator_agent = AIC("agents\case_generator_agent.py")
graph_state = AIC(r"agents\graph_state.py")

solution_runner = AIC(r"tools\solution_runner.py")
cases_generator = AIC(r"tools\cases_generator.py")


# {README}
# {AGENTS_DOC}
# {RAG_DOC}
# 参考代码：
# {solution_runner}
# {cases_generator}
template_text = fr"""
执行：
{AIC(r"V0.7.6版调用程序.py")}
明明设置了 timeout_s=2 但还是死循环
{AIC(r"V0.7.6报错.txt")}
原因 DeepSeek 已经找到，是因为 单线程 timeout_s 没有生效，但是 DeepSeek 给出的建议是采用 ThreadPoolExecutor 实现超时停止，但是那样不就会使得单线程额外增加开销吗？既然都要增加开销，不如应用：
{AIC(r"tools\沙箱技术.md")}
对单线程、多线程都使用。
为了提高多线程效率，Python的多进程非常垃圾。拟改为采用 C++ 调用拼接后的 Python 程序：
- C++ 启动沙箱，多少 thread 就启动 thread 个沙箱。注意！不是多少个 cases 启动多少个沙箱，那样及其低效。
- C++ 分配 JSON 测试样例
- 沙箱子线程，根据作答语言如 Python，解析输入的 JSON 字符，转换为 Python对象输入，带入 Solution 执行结果并输出。注意！用 while 循环get JSON 输入，直到EOF。
- 对每个子线程若累积WA早停或超时（可能是死循环），则通知所有进程不再执行新输入。
请先分析上述可行性，并代码架构。
"""



# 可以参考GPT联网搜索下的建议：
# {AIC(r"GPT的改进方案V0.7.6.a.md")}

# 使用示例
line_count = template_text.count('\n')
print(f"待合并文本共 {line_count} 行")

if AIC.copy_to_clipboard(template_text):
  print("✅ 已成功复制到剪贴板。")
else:
  print("❌ 复制失败，请检查系统环境。")


# - 原 safe_iter_kit.pyx 有一个风险点，对于树，其 stack 和 queue 并没有持有原生节点的引用计数
# - 因此需要修改为入 stack（queue） 就增加引用，而 check_safe 仅当为重复（in _seen 为真）时减少引用计数，销毁时按 _seen 减少引用计数