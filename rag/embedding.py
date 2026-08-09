# rag/embedding.py
# 更新于 RAG V0.2.1
# 2026-5-22

from __future__ import annotations

from typing import Any, List
import os

import chromadb
import requests
import json

from chromadb.api.types import (
    EmbeddingFunction,
    Documents,
    Embeddings,
)

EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "qwen3-embed-0.6b:q8")


# =========================================================
# Ollama embedding function
# =========================================================
class VectorStore:
    _client = None   # 类级共享 PersistentClient

    def __init__(self, db_path="./rag_db", collection_name="default"):
        if VectorStore._client is None:
            VectorStore._client = chromadb.PersistentClient(path=db_path)
        self.client = VectorStore._client
        self.embedding_function = OllamaEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
        )

    # typing error: 未定义“CodeChunk”
    def add_chunks(self, chunks: List[Any]):
        """
        将 CodeChunk 列表写入 ChromaDB 向量数据库。

        -----------------------------
        📌 数据映射关系（非常重要）
        -----------------------------
        每一个 CodeChunk 会被拆成三部分存入数据库：

        1️⃣ documents（向量化主体）
            - 内容：c.source（原始代码文本）
            - 用途：用于 embedding → 相似度检索
            - ⚠️ 这是语义搜索的核心字段

        2️⃣ ids（唯一标识）
            - 内容：c.id
            - 要求：
                - 全局唯一（建议：file_path + symbol）
                - 稳定（同一代码不要变化）
            - 用途：
                - 防重复
                - 精确定位 chunk

        3️⃣ metadatas（结构信息 / 可过滤信息）
            - 内容：结构化字典
            - 用途：
                - 检索后补充上下文
                - 过滤（如只查 function / class）
                - Debug / 溯源

            当前字段：
                {
                    "type": c.type,        # class / method / function
                    "name": c.name,        # 名称
                    "start": c.start_line,# 起始行
                    "end": c.end_line,     # 结束行
                    "file": c.file_path,     # 追溯文件来源
                    "parent": c.parent,      # ⭐ Graph RAG关键
                }

        -----------------------------
        📌 为什么要这样设计？
        -----------------------------
        ChromaDB 内部结构：

            embedding ← documents
                │
                ├── ids（索引）
                └── metadatas（附加信息）

        👉 也就是说：
            - documents 决定“能不能被搜到”
            - metadatas 决定“搜到之后能不能用”

        -----------------------------
        📌 使用注意事项
        -----------------------------
        1. documents / ids / metadatas 必须等长
        2. ids 不可重复（否则会报错或覆盖）
        3. documents 不要太大（建议 < 2~4KB）
        4. embedding 在 add 时自动完成（由 embedding_function）

        -----------------------------
        📌 调用流程
        -----------------------------
        chunk → embedding → 存储

        实际执行：
            self.collection.add(...)
            → 自动调用 embedding_function
            → 写入向量数据库
        """
        Warning("old version!")

        docs = []
        ids = []
        metadatas = []

        for c in chunks:
            docs.append(c.source)
            ids.append(c.id)
            metadatas.append({
                "type": c.type,
                "name": c.name,
                "start": c.start_line,
                "end": c.end_line,
                "file": c.file_path,     # ⭐ 核心
                "parent": json.dumps(c.parent)      # ⭐ Graph RAG关键
            })

        self.collection.add(
            documents=docs,
            ids=ids,
            metadatas=metadatas
        )

    def add_documents(self, docs: List[dict]):
        """semantic chunk 不再采用 add_chunks 而改用 document"""

        if not docs:
            return

        self.collection.add(
            documents=[
                d["document"]
                for d in docs
            ],
            ids=[
                d["id"]
                for d in docs
            ],
            metadatas=[
                d["metadata"]
                for d in docs
            ]
        )

class OllamaEmbeddingFunction(
    EmbeddingFunction[Documents]
):

    def __init__(
        self,
        model: str = EMBED_MODEL,
    ):
        self.model = model

    def __call__(
        self,
        input: Documents,
    ) -> Embeddings:

        res = requests.post(
            os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/") + "/api/embed",
            json={
                "model": self.model,
                "input": list(input),
                "options": {
                    "num_thread": max(
                        1, min(int(os.getenv("OLLAMA_NUM_THREAD", "8")), 8)
                    ),
                    "num_ctx": max(
                        2_048, min(int(os.getenv("OLLAMA_EMBED_NUM_CTX", "8192")), 8_192)
                    ),
                },
                "keep_alive": os.getenv("OLLAMA_EMBED_KEEP_ALIVE", "2m"),
            },
            timeout=max(10, int(os.getenv("OLLAMA_EMBED_TIMEOUT", "120"))),
        )
        res.raise_for_status()

        data = res.json()

        if "embeddings" not in data:
            raise RuntimeError(data)

        return data["embeddings"]
