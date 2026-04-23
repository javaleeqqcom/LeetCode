from typing import List, Dict
import chromadb
import requests

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
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path="./chroma_db"   # 👈 存盘目录
        )
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=OllamaEmbeddingFunction()
        )

    def add_chunks(self, chunks: List[CodeChunk]):
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
                "end": c.end_line
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
