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
{README}
{solution_runner}
{cases_generator}
执行：
{AIC(r"V0.7.6版调用程序.py")}
{AIC(r"V0.7.6报错.txt")}
solution_runner 虽然可以刹停TLE程序，无法为调试提供有效信息：
因此需要修改为：
- 出现运行错误如超时，则kill 出错的进程。但是不kill其他进程，而是设置 early_stop_event.set() 通知其他进程不再消费 cases。
- 最好。能够用类似 Ctrl+C 软终止Python进程，获得DEBUG信息
- 如果能实现上一条，则最好能够找出具体哪个 case 出现超时，但是注意不能牺牲效率。
- 注意利用 cid 信息定位错误样例，可以考虑用 multiprocessing.Manager().Value 保存上一次执行的 cid
- 尽量合并状态量，如每个进程的上一次开始测试的时间戳，和样例的 cid 合并为元组，减少全局变量开销
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