# rag/retriever.py
# 更新于 RAG V0.2.1
# 2026-5-22

from __future__ import annotations

import chromadb

from typing import List, Dict, Any

from rag.embedding import (
    OllamaEmbeddingFunction,
)


# =========================================================
# retriever
# =========================================================

class RAGRetriever:

    def __init__(
        self,
        db_root: str = "./rag_db",
    ):

        self.db_root = db_root

        self.embedding_function = (
            OllamaEmbeddingFunction()
        )

        self.clients = {}
        self.collections = {}

    # =====================================================
    # get collection
    # =====================================================

    def get_collection(
        self,
        collection_name: str,
    ):

        if collection_name in self.collections:
            return self.collections[collection_name]

        db_path = (
            f"{self.db_root}/{collection_name}"
        )

        client = chromadb.PersistentClient(
            path=db_path
        )

        collection = client.get_collection(
            name=collection_name,
            embedding_function=(
                self.embedding_function
            ),
        )

        self.clients[collection_name] = client
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

        collection = self.get_collection(
            collection_name
        )

        # ⭐⭐⭐ 不再手工 embedding
        res = collection.query(
            query_texts=[query],
            n_results=topk,
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