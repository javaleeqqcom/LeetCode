from typing import List, Dict
import chromadb
import requests
import json
from chunker import CodeChunk

# ===============================
# 配置
# ===============================

COLLECTION_NAME = "code_chunks"
EMBED_MODEL = "qwen3-embed-0.6b:q8"  # ollama embedding
CHUNK_OUTPUT_PATH = "./rag_chunk"

# ===============================
# Chroma 向量库
# ===============================

class VectorStore:

    def __init__(
        self,
        db_path="./rag_db/default",
        collection_name="default",
    ):

        self.client = chromadb.PersistentClient(
            path=db_path
        )

        self.collection = (
            self.client.get_or_create_collection(
                collection_name
            )
        )

    def add_chunks(self, chunks: List[CodeChunk]):
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

# ===============================
# Ollama Embedding 封装
# ===============================

class OllamaEmbeddingFunction:
    def __init__(self, model=EMBED_MODEL):
        self.model = model

    def __call__(self, input: List[str]) -> List[List[float]]:
        return self.embed_documents(input)

    def name(self) -> str:
        return f"ollama-{self.model}"

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for t in texts:
            res = requests.post(
                "http://localhost:11434/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": t
                }
            )
            if res.status_code != 200:
                raise RuntimeError(f"HTTP错误: {res.status_code}, {res.text}")

            data = res.json()

            # ✅ 防御性检查
            if "embedding" not in data:
                raise RuntimeError(f"Ollama返回异常: {data}")

            embeddings.append(data["embedding"])

        return embeddings

    def embed_query(self, query: str) -> List[float]:
        return self.embed_documents([query])[0]

    # ===== 可选（防未来版本爆炸）=====
    def embed_with_retries(self, input: List[str]) -> List[List[float]]:
        return self.embed_documents(input)

    def default_space(self) -> str:
        return "cosine"

    def supported_spaces(self) -> List[str]:
        return ["cosine", "l2"]

    @classmethod
    def build_from_config(cls, config: dict):
        return cls(**config)
