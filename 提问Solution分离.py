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

solution_runner = AIC(r"tools\solution_runner.py")

template_text = fr"""
{AIC(r"README.md")}
现在该框架有缺陷：
1. AI 与执行框架耦合方向反了
2. 难以实现多语言扩展（目前仅Python,将来要能C++）
我已实现：
{RAG_DOC}
现在需要根据GPT5的架构建议：
{AIC(r"GPT5改进建议(V0.7~V0.8).md")}
进行修改。
将如下代码弃置：
{AIC(r"tools\ai_prompts.py")}
请先实现：
- solution_runner 是绑定执行代码的，目前仅设计了 Python，因为要先解析 Solution 类的结构，才能自动检查代入的参数是否出错。 一个比较简单的去藕盒方法是设计一个统一的 Solution_struct data.class，兼容 Python/ C++ 等，在 原 solution_runner 基础上可以导出。 然后 AI-agent 基于导出结构（包含代码信息），来设计 case_generator，因为测试样例的设计要考虑算法的复杂度，否则设计一个实际执行需要一万分钟以上的程序毫无意义，学生早就放假了…… 因此要最小侵入式设计，将 solution_runner 的 get_cases_generator 删除，新增Solution_struct@data.class 类，solution_runner 在一开始就围绕构造该类服务，注意该类是 Python /C++（以后新增）/Java（可能新增） 是能够共用的。 现在请设计 Solution_struct.py 的代码，并说明 solution_runner.py 需要修改的函数。 为下一步实现 case_generator 做准备。
参考GPT5的：
{AIC(r"GPT5的修改建议V0.7.4.md")}
进行修改，原有部分代码如下：
{solution_runner}
只需回复新增的代码文件，和要修改的函数部分。
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