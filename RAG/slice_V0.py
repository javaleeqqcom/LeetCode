# slice_V0.py

import ast
import os
from typing import List, Dict
import chromadb

# ===============================
# 配置
# ===============================

COLLECTION_NAME = "code_chunks"
EMBED_MODEL = "qwen3-embed-0.6b:q8"  # ollama embedding

# ===============================
# 数据结构
# ===============================

class CodeChunk:
    def __init__(self, cid, ctype, name, source, start_line, end_line):
        self.id = cid
        self.type = ctype
        self.name = name
        self.source = source
        self.start_line = start_line
        self.end_line = end_line

    def to_text(self):
        return f"""
# ===============================
# Chunk ID: {self.id}
# Type: {self.type}
# Lines: {self.start_line}-{self.end_line}
# ===============================

{self.source}
"""


# ===============================
# 切片核心
# ===============================

class CodeChunker:

    def __init__(self, code: str):
        self.code = code
        self.lines = code.splitlines()

    def _extend_up_comments(self, lineno: int) -> int:
        """向上扩展注释（无空行）"""
        i = lineno - 2  # 转0-index
        while i >= 0:
            line = self.lines[i].strip()
            if line.startswith("#"):
                i -= 1
                continue
            elif line == "":
                break
            else:
                break
        return i + 2  # 转回1-index

    def _get_source(self, node):
        """获取完整源码（含上下扩展）"""
        start = node.lineno
        end = node.end_lineno

        # 向上扩展注释
        new_start = self._extend_up_comments(start)

        source = "\n".join(self.lines[new_start-1:end])
        return source, new_start, end

    def chunk(self) -> List[CodeChunk]:
        tree = ast.parse(self.code)
        chunks = []

        for node in tree.body:

            # ---------- Class ----------
            if isinstance(node, ast.ClassDef):
                source, s, e = self._get_source(node)

                chunks.append(CodeChunk(
                    cid=node.name,
                    ctype="class",
                    name=node.name,
                    source=source,
                    start_line=s,
                    end_line=e
                ))

                # ---------- Methods ----------
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        source, s, e = self._get_source(item)

                        chunks.append(CodeChunk(
                            cid=f"{node.name}.{item.name}",
                            ctype="method",
                            name=item.name,
                            source=source,
                            start_line=s,
                            end_line=e
                        ))

            # ---------- Global Function ----------
            elif isinstance(node, ast.FunctionDef):
                source, s, e = self._get_source(node)

                chunks.append(CodeChunk(
                    cid=node.name,
                    ctype="function",
                    name=node.name,
                    source=source,
                    start_line=s,
                    end_line=e
                ))

        return chunks


# ===============================
# Chroma 向量库
# ===============================

class VectorStore:

    def __init__(self):
        self.client = chromadb.Client()
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

import requests

class OllamaEmbeddingFunction:
    def __call__(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for t in texts:
            res = requests.post(
                "http://localhost:11434/api/embeddings",
                json={
                    "model": EMBED_MODEL,
                    "prompt": t
                }
            )
            embeddings.append(res.json()["embedding"])
        return embeddings


# ===============================
# 输出（人工审查用）
# ===============================

def save_chunks_readable(chunks: List[CodeChunk], out_file="chunks.txt"):
    with open(out_file, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(c.to_text())
            f.write("\n\n")


# ===============================
# 主流程
# ===============================

def process_file(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    chunker = CodeChunker(code)
    chunks = chunker.chunk()

    print(f"[INFO] 切片数量: {len(chunks)}")

    # 保存可读版本
    save_chunks_readable(chunks)

    # 存入向量库
    store = VectorStore()
    store.add_chunks(chunks)

    print("[INFO] 已写入 ChromaDB")

    return chunks


# ===============================
# 🔜 后续扩展（框架预留）
# ===============================

"""
TODO:

1. Dependency Graph（依赖关系）
--------------------------------
- method → class
- function → function（调用关系）
- 类型依赖（ListNode / TreeNode）

class DependencyBuilder:
    def build(chunks):
        return graph


2. Retriever（RAG检索）
--------------------------------
class Retriever:
    def retrieve(query):
        topk = vector search
        + dependency expand
        return chunks


3. Prompt Builder
--------------------------------
def build_prompt(question, code, chunks):
    return prompt


4. Execution Feedback（未来核心）
--------------------------------
生成 → 执行 → 错误 → 调整权重

"""


# ===============================
# CLI
# ===============================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python RAG/slice_V0.py <file.py>")
        exit(1)

    process_file(sys.argv[1])