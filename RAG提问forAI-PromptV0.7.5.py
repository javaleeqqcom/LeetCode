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

报错 = AIC(r"V0.7.5报错.txt")

template_text = fr"""
我已按你说的修改了，并修复了一下报错，最后修改的代码如下：
{case_generator_agent}
可能需要参考的文档如下：
{AIC(r"prompts/case_generator.prompt.md")}
执行如下代码：
{AIC(r"V0.7.5版调用程序.py")}
形式上符合预期，现阶段禁止AI直接执行生成的代码。不过其生成的代码质量堪忧，如下：
{AIC(r"Question\2902. Count of Sub-Multisets With Bounded Sum\generated_case_generator.py")}
而该问题的一个优秀测试样例代码如下：
{AIC(r"Question\2902. Count of Sub-Multisets With Bounded Sum\case_generator.py")}
AI-Agent生成的结果有如下问题：
- 没有去掉 ('`'*3) 的Markdown代码框包裹
改进目标：
- 让 AI-Agent 以 LangChain 的格式生成无需Markdown代码框包裹的代码，或者用Python程序自动去包裹
- 需要保存向 LLM invoke 的台词，以便 LLM 未响应时，输出该文本路径，由学生手动复制到第三方AI提问。
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