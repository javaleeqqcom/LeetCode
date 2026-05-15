import chromadb
import requests

from typing import List


DB_PATH = "./chroma_db"
COLLECTION_NAME = "code_chunks"
EMBED_MODEL = "qwen3-embed-0.6b:q8"


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

        return res.json()["embedding"]


class RAGRetriever:

    def __init__(self):

        self.client = chromadb.PersistentClient(path=DB_PATH)

        self.collection = self.client.get_collection(
            name=COLLECTION_NAME
        )

        self.embedder = OllamaEmbedding()

    def search(self, query: str, topk: int = 3):

        vec = self.embedder.embed(query)

        res = self.collection.query(
            query_embeddings=[vec],
            n_results=topk,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        docs = []

        for doc, meta, dist in zip(
            res["documents"][0],
            res["metadatas"][0],
            res["distances"][0],
        ):

            docs.append({
                "score": 1 - dist,
                "document": doc,
                "metadata": meta,
            })

        return docs