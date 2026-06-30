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

template_text = fr"""

已按你说的修改了代码：
{retriever}
需要修改：
{debug_retriever}
以验证合并库后DB 可以检索到正确的内容。
顺便注意一下路径：
{AIC(r"rag\__init__.py")}
避免出现 ModuleNotFoundError: No module named 'rag' 的情况。
但是要注意从 leetcode 根目录也要能直接调用 rag/ 下的 .py
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