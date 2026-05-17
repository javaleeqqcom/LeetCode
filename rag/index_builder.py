# rag/index_builder.py
import json
import os

from embedding import VectorStore
from docs_inclusion import diff_docs
from chunker import CodeChunker, save_chunks_readable, save_chunks_json


# ===============================
# 加载 JSON
# ===============================

def load_docs(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ===============================
# 构建索引
# ===============================

def build_index(docs_file: str, 
                collection_name : str,
                prev_docs_file: str|None = None
                ):
    docs = load_docs(docs_file)

    if prev_docs_file and os.path.exists(prev_docs_file):
        old_docs = load_docs(prev_docs_file)
        docs = diff_docs(old_docs, docs)
        print(f"[INFO] 增量更新文件数: {len(docs)}")
    else:
        print(f"[INFO] 全量构建: {len(docs)}")

    if not docs:
        print("✅ 无需更新")
        return

    store = VectorStore(
        db_path = os.path.join("./rag_db", collection_name),
        collection_name=collection_name
    )

    total_chunks = 0
    for d in docs:
        path = d["path"]
        print(f"\n📄 处理: {path}")

        try:
            chunker = CodeChunker(path)
            chunks = chunker.chunk()

            # ⭐⭐⭐ 新增：持久化 chunk
            base_name = path.replace("\\", ".").replace("/", ".")
            txt_path = f"./rag_chunk/{base_name}.txt"
            json_path = f"./rag_chunk/{base_name}.json"

            os.makedirs("./rag_chunk", exist_ok=True)

            save_chunks_readable(chunks, txt_path)
            save_chunks_json(chunks, json_path)

            # 入库
            store.add_chunks(chunks)

            print(f"  -> chunks: {len(chunks)}")

        except Exception as e:
            print(f"❌ 失败: {path}")
            print(e)
            
    print(f"\n✅ 完成，总 chunks: {total_chunks}")


# ===============================
# CLI
# ===============================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python rag/index_builder.py <docs.json> [prev_docs.json]")
        exit(1)

    docs_file = sys.argv[1]
    prev_file = sys.argv[2] if len(sys.argv) > 2 else None

    build_index(docs_file, prev_file)