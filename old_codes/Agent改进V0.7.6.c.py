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

# {README}
template_text = fr"""
执行
{AIC(r"V0.7.6版调用程序.py")}
明明输入的代码已经有`import random`，但还是
{AIC(r"V0.7.6报错.txt")}
其中执行到如下代码时报错：
`cases = build_test_cases(case_generator, scales)`
很可能是子环境没有屏蔽了`import random`关键代码：
{case_generator_agent}
{agent_io}
{AIC(r"tools\cases_generator.py")}
请排查原因
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