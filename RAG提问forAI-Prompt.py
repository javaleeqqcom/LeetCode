from tools.AIConsultation import AIConsultation as AIC

debug_retriever = AIC(r"rag\debug_retriever.py")
RAG_DEBUG = AIC(r"RAG_DEBUG.txt")
embedding = AIC(r"rag\embedding.py")
retriever=AIC(r"rag\retriever.py")
index_builder = AIC(r"rag\index_builder.py")
RAG_DOC = AIC(r"rag\RAG_DOC.md")

analyze_agent = AIC(r"agents\analyze_agent.py")
build_graph = AIC(r"agents\build_graph.py")
case_generator_agent = AIC("agents\case_generator_agent.py")
graph_state = AIC(r"agents\graph_state.py")

template_text = fr"""
我已经初步构建了 RAG 系统，DOC如下：
{RAG_DOC}
LangChain的代码如下：
{analyze_agent}
{build_graph}
{case_generator_agent}
{graph_state}
但是执行：
{AIC(r"单用例调用版.py")}
输出的提问文本如下，显然没有包含RAG样例：
{AIC(r"Question\3943. Number of Pairs After Increment\测试样例提问.txt")}
因为：
{AIC(r"tools\ai_prompts.py")}
还在用传统的提示词生成方式，应修改使其调用智能体。
而且 ai_prompts 居然是由执行测试的程序：
{AIC(r"tools\solution_runner.py")}
来进行调用的，这架构不合理，将来要改为统一 AI-agent 生成 测试样例代码，并操作 solution_runner 执行。
请重新设计架构。
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