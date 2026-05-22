# rag/retriever.py

from __future__ import annotations

import requests
import chromadb

from typing import List, Dict, Any


EMBED_MODEL = "qwen3-embed-0.6b:q8"


# =========================================================
# embedding
# =========================================================

class OllamaEmbedding:
    def __init__(self, model=EMBED_MODEL):
        self.model = model

    def embed(self, text: str) -> List[float]:
        res = requests.post(
            "http://localhost:11434/api/embeddings",
            json={
                "model": self.model,
                "prompt": text,
            },
        )

        if res.status_code != 200:
            raise RuntimeError(res.text)

        data = res.json()

        if "embedding" not in data:
            raise RuntimeError(data)

        return data["embedding"]


# =========================================================
# retriever
# =========================================================

class RAGRetriever:
    """
    通用 Retriever

    支持：
    - semantic rag
    - ast rag
    - 多 collection
    - metadata
    - future rerank
    """

    def __init__(
        self,
        db_root: str = "./rag_db",
    ):
        self.db_root = db_root
        self.embedder = OllamaEmbedding()

        self.clients: Dict[str, chromadb.PersistentClient] = {}
        self.collections = {}

    # =====================================================
    # lazy load collection
    # =====================================================

    def get_collection(self, collection_name: str):

        if collection_name in self.collections:
            return self.collections[collection_name]

        db_path = f"{self.db_root}/{collection_name}"

        client = chromadb.PersistentClient(
            path=db_path
        )

        collection = client.get_collection(
            name=collection_name
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

        vec = self.embedder.embed(query)

        res = collection.query(
            query_embeddings=[vec],
            n_results=topk,
            where=where,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        results = []

        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]

        for doc, meta, dist in zip(
            docs,
            metas,
            dists,
        ):

            score = 1.0 - dist

            results.append({
                "score": score,
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