from tools.AIConsultation import AIConsultation as AIC

README = AIC(r"README.md")

debug_retriever = AIC(r"rag\debug_retriever.py")
RAG_DEBUG = AIC(r"RAG_DEBUG.txt")
embedding = AIC(r"rag\embedding.py")
retriever=AIC(r"rag\retriever.py")
index_builder = AIC(r"rag\index_builder.py")
rag_knowledge_update = AIC(r"rag\rag_knowledge_update.py")
RAG_DOC = AIC(r"rag\RAG_DOC.md")
semantic_chunker = AIC(r"rag\semantic_chunker.py")

analyze_agent = AIC(r"agents\analyze_agent.py")
build_graph = AIC(r"agents\build_graph.py")
case_generator_agent = AIC("agents\case_generator_agent.py")
graph_state = AIC(r"agents\graph_state.py")

template_text = fr"""
{README}
我已经初步构建了 RAG 系统，DOC如下：
{RAG_DOC}
尝试提取如下：
{RAG_DEBUG}
发现 case_generator 仅录入函数声明，没有录入函数体，因为我的 query 是如下原文：
{AIC(r"rag_knowledge\case_generator\unique_call.array.leetcode_3660.py")}
但是却未找到，而且可以通过：
{AIC(r"rag_chunk\rag_knowledge.case_generator.unique_call.array.leetcode_3660.py.semantic.json")}
发现 segmented 的只有函数头，请检查：
{embedding}
{semantic_chunker}
{index_builder}
{rag_knowledge_update}
是哪里出了问题。
我将上述问题向ChatGPT5反馈后，得到如下建议：
{AIC(r"V0.7.6~0.7.7 的修改建议.md")}
请参考该建议进行修改，只需说明要修改的文件的相关函数，我会替换修过过的函数。
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