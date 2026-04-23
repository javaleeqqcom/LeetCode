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
CHUNK_OUTPUT_PATH = "./rag_chunk"

# ===============================
# 数据结构
# ===============================

class CodeChunk:
    def __init__(self, cid, ctype, name, source, start_line, end_line, parent=None):
        self.id = cid
        self.type = ctype
        self.name = name
        self.source = source
        self.start_line = start_line
        self.end_line = end_line
        self.parent = parent

    def to_dict(self):
        text = self.source
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "parent": self.parent,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "line_count": self.end_line - self.start_line + 1,
            "char_count": len(text),              # ⭐ 新增
            "preview": text.strip().split("\n")[0][:80],
            "source": text
        }

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
                            parent=node.name,   # ⭐ 新增
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

from typing import List
import requests

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

# ===============================
# 输出（人工审查用）
# ===============================

def save_chunks_readable(chunks: List[CodeChunk], out_file="chunks.txt"):
    with open(out_file, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(c.to_text())
            f.write("\n\n")

def build_hierarchy(chunks: List[CodeChunk]):
    id_map = {c.id: c for c in chunks}

    for c in chunks:
        if c.type == "class":
            c.sub_chunks = []

    for c in chunks:
        if c.parent and c.parent in id_map:
            parent = id_map[c.parent]
            if hasattr(parent, "sub_chunks"):
                parent.sub_chunks.append(c.id)

    return chunks

import json

def save_chunks_json(chunks: List[CodeChunk], out_file="chunks.json"):
    chunks = build_hierarchy(chunks)

    data = []
    for c in chunks:
        d = c.to_dict()
        if hasattr(c, "sub_chunks"):
            d["sub_chunks"] = c.sub_chunks
        data.append(d)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[INFO] JSON已保存: {out_file}")

# ===============================
# 主流程
# ===============================

def process_file(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()
    
    chunk_out_name = os.path.relpath(file_path,os.getcwd()).replace("\\",".")
    print(f"chunk_out_name : {chunk_out_name}")

    chunker = CodeChunker(code)
    chunks = chunker.chunk()

    print(f"[INFO] 切片数量: {len(chunks)}")

    # 保存可读版本
    save_chunks_readable(chunks,os.path.join(CHUNK_OUTPUT_PATH,f"{chunk_out_name}.txt"))
    save_chunks_json(chunks,os.path.join(CHUNK_OUTPUT_PATH,f"{chunk_out_name}.json"))       # ⭐ 新增

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