# rag/debug_retriever.py
import chromadb
import requests
from typing import List

# ===============================
# 配置
# ===============================
DB_PATH = "./chroma_db"
COLLECTION_NAME = "code_chunks"
EMBED_MODEL = "qwen3-embed-0.6b:q8"


# ===============================
# Embedding
# ===============================
class OllamaEmbedding:
    def __init__(self, model=EMBED_MODEL):
        self.model = model

    def embed(self, text: str) -> List[float]:
        res = requests.post(
            "http://localhost:11434/api/embeddings",
            json={
                "model": self.model,
                "prompt": text
            }
        )
        data = res.json()
        return data["embedding"]


# ===============================
# Retriever Debugger
# ===============================
class RetrieverDebugger:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=DB_PATH)

        # ⚠️ 注意：这里不再传 embedding_function（避免重复嵌入）
        self.collection = self.client.get_collection(
            name=COLLECTION_NAME
        )

        self.embedder = OllamaEmbedding()

    def search(self, query: str, topk: int = 5):
        q_vec = self.embedder.embed(query)

        results = self.collection.query(
            query_embeddings=[q_vec],
            n_results=topk,
            include=["documents", "metadatas", "distances"]
        )

        return results

    def pretty_print(self, results):
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        dists = results["distances"][0]

        for i, (doc, meta, dist) in enumerate(zip(docs, metas, dists)):
            print("\n" + "=" * 30)
            print(f"[Rank {i+1}] Score: {1 - dist:.4f}")
            print(f"ID: {meta.get('name')}")
            print(f"Type: {meta.get('type')}")
            print(f"Lines: {meta.get('start')} - {meta.get('end')}")
            print("-" * 30)
            print(doc[:800])  # 防止爆屏
            print("=" * 30)

    def loop(self):
        print("\n🚀 RAG Debug Console (Chroma Retriever)")
        print("输入 exit 退出\n")

        while True:
            q = input("🔍 Query > ").strip()
            if q in ("exit", "quit"):
                break

            if not q:
                continue

            results = self.search(q, topk=5)
            self.pretty_print(results)


# ===============================
# CLI
# ===============================
if __name__ == "__main__":
    debugger = RetrieverDebugger()
    debugger.loop()