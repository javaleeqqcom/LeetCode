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
DOC：{{
{README}
{RAG_DOC}
{AGENTS_DOC}
}}
我的提问:{{
非常好，已按你的提醒修复了切片和新增栈嵌套的功能。执行成功如下：
{AIC(r"RAG召回测试结果.txt")}
在已经确定RAG录入正常的情况下，执行：
{AIC(r"V0.7.6版调用程序.py")}
输出的提示词如下,显然没有包含RAG样例：
{AIC(r"Question\Q1. Maximum Total Sum of K Selected Elements©leetcode\agent_logs\AI_prompt_000.log")}
因为RAG更新在LangChain的代码更新后，显然不会自动用上RAG的数据库，请分析如何使用RAG的 case_generation 数据库参考。
可能相关的问题代码如下，若还有缺失的关键代码，请根据 DOC 补充说明：
{retriever}
{reference_retriever}
{case_generator_agent}
{AIC(r"prompts\case_generator.prompt.md")}
}}
GPT5的建议:{{
{AIC(r"GPT的改进方案V0.7.7.a.md")}
}}
优化目标:{{
- 先实现RAG的构建和应用功能，将不同库合并为一个文件夹。
```
请先合并两个文件夹（现在数据量不大，重新建库无多大代价）
(py314) PS D:\Users\java_lee\Documents\GitHub\LeetCode> dir rag_db


    目录: D:\Users\java_lee\Documents\GitHub\LeetCode\rag_db


Mode                 LastWriteTime         Length Name                                                                                                                                                                                                                           
----                 -------------         ------ ----                                                                                                                                                                                                                           
d-----         2026/6/27     14:05                case_generator                                                                                                                                                                                                                 
d-----         2026/6/28     12:06                conversion
```
- 修改 reference_retriever 使得 case_generator_agent 能匹配参考代码。
- 只需回复需要修改的文件和函数，以函数为单位，我会替换源文件中响应函数。
}}
相关代码:{{
{embedding}
{index_builder}
}}
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