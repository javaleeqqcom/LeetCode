from tools.AIConsultation import AIConsultation as AIC

README = AIC(r"README.md")
RAG_DOC = AIC(r"rag\RAG_DOC.md")
AGENTS_DOC = AIC(r"agents\AGENTS_DOC.md")

debug_retriever = AIC(r"rag\debug_retriever.py")
embedding = AIC(r"rag\embedding.py")
retriever=AIC(r"rag\retriever.py")
index_builder = AIC(r"rag\index_builder.py")
RAG_DOC = AIC(r"rag\RAG_DOC.md")

analyze_agent = AIC(r"agents\analyze_agent.py")
build_graph = AIC(r"agents\build_graph.py")
case_generator_agent = AIC("agents\case_generator_agent.py")
graph_state = AIC(r"agents\graph_state.py")
reference_retriever = AIC(r"agents\reference_retriever.py")

solution_runner = AIC(r"tools\solution_runner.py")
solution_struct = AIC(r"tools\solution_struct.py")

template_text = fr"""
{README}
{AGENTS_DOC}
{AIC(r"tools\沙箱技术.md")}
{solution_runner}
{solution_struct}
原有开启12个线程执行1s的Python代码效率加速比仅有 200%~300%，
现在需要改进多线程的方式：
- 采用 Python 实现 Agent，但是调用 C++ 管理多线程调度
- C++ 多线程调度实现：
  - 将测试任务分配到不同线程，使得各线程busy率尽可能逼近100%
  - 每个线程调用不同编程语言执行OJ答题任务，C++ 调用 Python、C、C++、Java等，各任务内部采用 while 循环通过管道通信获取测试样例，并反馈状态。
  - 架构设计要能兼容沙箱安全技术（可以暂不实现）
  - 架构设计要能高效执行代码，如 Python 采用 PyPy，有 m 个线程则只需编译 m 次等。
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