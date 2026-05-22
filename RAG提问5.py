from tools.AIConsultation import AIConsultation

debug_retriever = AIConsultation(r"rag\debug_retriever.py")
RAG执行失败 = AIConsultation(r"RAG执行失败.txt")

template_text = f"""
我已经按你的建议修改了 retriever.py，但是进行测试
{debug_retriever}
执行结果如下：
{RAG执行失败}
"""

# 使用示例
line_count = template_text.count('\n')
print(f"待合并文本共 {line_count} 行")

if AIConsultation.copy_to_clipboard(template_text):
  print("✅ 已成功复制到剪贴板。")
else:
  print("❌ 复制失败，请检查系统环境。")


# - 原 safe_iter_kit.pyx 有一个风险点，对于树，其 stack 和 queue 并没有持有原生节点的引用计数
# - 因此需要修改为入 stack（queue） 就增加引用，而 check_safe 仅当为重复（in _seen 为真）时减少引用计数，销毁时按 _seen 减少引用计数