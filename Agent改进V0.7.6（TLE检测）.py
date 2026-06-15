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
参考代码：
{solution_runner}
{cases_generator}
{AIC(r"tools\solution_runner(modify).py")}
执行：
{AIC(r"V0.7.6版调用程序.py")}
{AIC(r"V0.7.6报错.txt")}
solution_runner 虽然可以刹停TLE程序，但是没有记录到log（无 'TLE_*'）。
GPT5分析原因如下：
- Windows 的 terminate()直接把进程砍掉。不会：signal.signal(SIGTERM,...)
- 即便是 Linux 的，traceback 只代表：当前栈帧不是完整 traceback。
因此修改意见：
- 放弃 signal(SIGTERM ，在主进程捕捉TLE的子进程最后保存信息（cid,时间戳）写 log（调用 _log_result 统一格式）
- 不要用 manager.list ，因为所有子线程都要抢占一个 manager.list 对象，应该改为 list(单个信号量) 如 manager.Value(tuple, ...)
- 保持原有的TLE视为早停，而早停只杀出错的进程，其余进程等待其该group产出并收集结果。
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