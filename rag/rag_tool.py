# rag/rag_tool.py
# 更新于 RAG V0.2.0
# 2026-5-22

from langchain_core.tools import tool

from rag.retriever import RAGRetriever


retriever = RAGRetriever()


# =========================================================
# case_generator semantic rag
# =========================================================

@tool
def search_case_knowledge(
    query: str,
) -> str:
    """
    搜索 case_generator 相关知识。

    用于：
    - testcase generation
    - edge case
    - special judge
    - conversion
    - normalization
    """

    return retriever.build_context(
        query=query,
        collection_name="case_generator",
        topk=4,
    )


# =========================================================
# conversion ast rag
# =========================================================

@tool
def search_conversion_code(
    query: str,
) -> str:
    """
    搜索 conversion 代码实现。

    用于：
    - 查找已有转换逻辑
    - AST转换
    - ListNode/tree 转换
    - parser
    """

    return retriever.build_context(
        query=query,
        collection_name="conversion",
        topk=4,
    )