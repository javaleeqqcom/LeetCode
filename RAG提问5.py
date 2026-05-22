from tools.AIConsultation import AIConsultation as AIC

debug_retriever = AIC(r"rag\debug_retriever.py")
RAG执行失败 = AIC(r"RAG执行失败.txt")
embedding = AIC(r"rag\embedding.py")
retriever=AIC(r"rag\retriever.py")
index_builder = AIC(r"rag\index_builder.py")

template_text = fr"""
我已经按你的建议修改了 retriever.py，但是进行测试
{debug_retriever}
执行结果如下：
{RAG执行失败}
查了资料说是要用 from chromadb.api.types import EmbeddingFunction 等类继承来构造统一的嵌入模型接口，我尝试修改：
{embedding}
{retriever}
但是发现：
{index_builder}
执行报错：
```
(py314) PS D:\Users\java_lee\Documents\GitHub\LeetCode> & C:/Users/john/anaconda3/envs/py314/python.exe d:/Users/java_lee/Documents/GitHub/LeetCode/rag/rag_knowledge_update.py

============================================================
🚀 更新 case_generator semantic RAG
============================================================

✅ 已保存: ./rag_docs\docs_inclusion_1779460777.json
[INFO] 全量构建文件数: 1

📄 Semantic处理: rag_knowledge/case_generator\unique_call.array.leetcode_3660.py
❌ Semantic失败: rag_knowledge/case_generator\unique_call.array.leetcode_3660.py
'VectorStore' object has no attribute 'add_documents'

✅ Semantic完成，总 modules: 0

============================================================
🚀 更新 conversion AST RAG
============================================================

✅ 已保存: ./rag_docs\docs_inclusion_1779460777.json
[INFO] 全量构建: 2

📄 处理: rag_knowledge/conversion\python\defalut_args.py
[INFO] JSON已保存: ./rag_chunk/rag_knowledge.conversion.python.defalut_args.py.json
❌ 失败: rag_knowledge/conversion\python\defalut_args.py
'VectorStore' object has no attribute 'add_chunks'

📄 处理: rag_knowledge/conversion\python\defalut_kwargs.py
[INFO] JSON已保存: ./rag_chunk/rag_knowledge.conversion.python.defalut_kwargs.py.json
❌ 失败: rag_knowledge/conversion\python\defalut_kwargs.py
'VectorStore' object has no attribute 'add_chunks'

✅ 完成，总 chunks: 0

🎉 全部 RAG 更新完成
```
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