# rag/retriever.py
# 更新于 RAG V0.2.1
# 2026-5-22

from __future__ import annotations

import chromadb
from pathlib import Path

from typing import List, Dict, Any

from .embedding import (
    OllamaEmbeddingFunction,
)


# =========================================================
# retriever
# =========================================================
class RAGRetriever:
    _clients = {}

    def __init__(self, db_root: str = "./rag_db"):
        db_root = str(Path(db_root).resolve())
        if db_root not in RAGRetriever._clients:
            RAGRetriever._clients[db_root] = chromadb.PersistentClient(path=db_root)
        self.client = RAGRetriever._clients[db_root]
        self.embedding_function = OllamaEmbeddingFunction()
        self.collections = {}

    def get_collection(self, collection_name: str):
        if collection_name in self.collections:
            return self.collections[collection_name]
        collection = self.client.get_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
        )
        self.collections[collection_name] = collection
        return collection

    # =====================================================
    # search
    # =====================================================

    def search(
        self,
        query: str,
        collection_name: str,
        topk: int = 5,
        where: dict | None = None,
    ) -> List[Dict[str, Any]]:

        if not isinstance(query, str) or not query.strip():
            raise ValueError("RAG query 不能为空")
        if not isinstance(topk, int) or topk <= 0:
            raise ValueError("topk 必须为正整数")
        collection = self.get_collection(collection_name)
        count = collection.count()
        if count == 0:
            return []

        # ⭐⭐⭐ 不再手工 embedding
        res = collection.query(
            query_texts=[query],
            n_results=min(topk, count),
            where=where,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        results = []

        docs = res["documents"][0]
        metas = res["metadatas"][0]
        dists = res["distances"][0]

        for doc, meta, dist in zip(
            docs,
            metas,
            dists,
        ):

            results.append({
                "score": 1.0 - dist,
                "document": doc,
                "metadata": meta,
            })

        return results
    

    # =====================================================
    # build context
    # =====================================================

    def build_context(
        self,
        query: str,
        collection_name: str,
        topk: int = 5,
    ) -> str:

        docs = self.search(
            query=query,
            collection_name=collection_name,
            topk=topk,
        )

        return self.format_context(docs)

    @staticmethod
    def format_context(docs: List[Dict[str, Any]]) -> str:
        """Format already-retrieved results without issuing another query."""
        blocks = []

        for i, d in enumerate(docs):

            meta = d["metadata"]

            block = f"""
# Chunk {i + 1}

Score:
{d["score"]:.4f}

File:
{meta.get("file_path", meta.get("file", ""))}

Type:
{meta.get("type", "")}

Name:
{meta.get("module_name", meta.get("name", ""))}

Content:
{d["document"]}
"""

            blocks.append(block)

        return "\n\n".join(blocks)
