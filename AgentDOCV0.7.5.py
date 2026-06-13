from tools.AIConsultation import AIConsultation as AIC

README = AIC(r"README.md")

debug_retriever = AIC(r"rag\debug_retriever.py")
RAG_DEBUG = AIC(r"RAG_DEBUG.txt")
embedding = AIC(r"rag\embedding.py")
retriever=AIC(r"rag\retriever.py")
index_builder = AIC(r"rag\index_builder.py")
RAG_DOC = AIC(r"rag\RAG_DOC.md")

agent_io = AIC(r"agents\agent_io.py")
analyze_agent = AIC(r"agents\analyze_agent.py")
build_graph = AIC(r"agents\build_graph.py")
case_generator_agent = AIC("agents\case_generator_agent.py")
complexity_analyzer = AIC(r"agents\complexity_analyzer.py")
graph_state = AIC(r"agents\graph_state.py")
reference_retriever = AIC(r"agents\reference_retriever.py")

报错 = AIC(r"V0.7.5报错.txt")

template_text = fr"""
{README}
现在请参考：
{RAG_DOC}
撰写 agents\AGENTS_DOC.md，要求总结 agents\ 目录下各类、函数功能，需要描述的代码如下：
{agent_io}
{analyze_agent}
{build_graph}
{case_generator_agent}
{complexity_analyzer}
{graph_state}
{reference_retriever}
令附一个调用案例（注意该代码不属于 AGENTS_DOC 归纳范围，仅作调用示例参考）
{AIC(r"V0.7.5版调用程序.py")}
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