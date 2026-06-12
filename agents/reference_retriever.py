from typing import List
from rag.retriever import RAGRetriever
from tools.solution_struct import SolutionStruct

class ReferenceRetriever:
    def __init__(self, db_root="./rag_db"):
        self.retriever = RAGRetriever(db_root)

    def retrieve(self, knowledge_requirements: List[str], topk=5) -> List[SolutionStruct]:
        """根据 knowledge_requirements 检索相关题目的 SolutionStruct 列表"""
        # 拼接查询
        query = " ".join(knowledge_requirements)
        results = self.retriever.search(query, "conversion", topk=topk)
        refs = []
        for r in results:
            # 假设 metadata 中存储了 SolutionStruct 的 JSON
            meta = r.get("metadata", {})
            json_str = meta.get("solution_struct_json")
            if json_str:
                refs.append(SolutionStruct.from_json(json_str))
        return refs