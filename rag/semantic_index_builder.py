# rag/semantic_index_builder.py
# 更新于 RAG V0.1.3
# 2026-5-17

import json
import os
from pathlib import Path

from .embedding import VectorStore
from .docs_inclusion import diff_docs

from .semantic_chunker import SemanticChunker


# =========================================================
# load docs
# =========================================================

def load_docs(path):

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# =========================================================
# semantic chunk -> vector store
# =========================================================

def build_semantic_index(
    docs_file: str,
    collection_name: str,
    prev_docs_file: str | None = None,
):

    docs = load_docs(docs_file)

    # =====================================================
    # 增量更新
    # =====================================================

    if prev_docs_file and os.path.exists(prev_docs_file):

        old_docs = load_docs(prev_docs_file)

        docs = diff_docs(old_docs, docs)

        print(f"[INFO] 增量更新文件数: {len(docs)}")

    else:

        print(f"[INFO] 全量构建文件数: {len(docs)}")

    if not docs:

        print("✅ 无需更新")

        return

    store = VectorStore( collection_name=collection_name )

    total_modules = 0

    # =====================================================
    # build
    # =====================================================

    for d in docs:

        path = d["path"]

        print(f"\n📄 Semantic处理: {path}")

        try:

            chunker = SemanticChunker(path)

            example = chunker.parse()

            # =================================================
            # 保存调试文件
            # =================================================

            base_name = (
                path.replace("\\", ".")
                .replace("/", ".")
            )

            os.makedirs("./rag_chunk", exist_ok=True)

            # -------------------------
            # 完整 example
            # -------------------------

            example_json = {

                "example_name": example.example_name,

                "tags": example.tags,

                "file_path": example.file_path,

                "module_count": len(example.rag_modules),

                "modules": list(example.rag_modules.keys()),
            }

            with open(
                f"./rag_chunk/{base_name}.semantic.json",
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    example_json,
                    f,
                    indent=2,
                    ensure_ascii=False
                )

            # =================================================
            # build vector chunks
            # =================================================

            vector_chunks = []

            for module in example.rag_modules.values():

                # embedding 空则跳过
                if not module.embedding_text.strip():
                    continue

                vector_chunks.append({

                    "id":
                        module.module_id,

                    "document":
                        module.embedding_text,

                    "metadata": {

                        "type": "semantic_module",

                        "module_name": module.name,

                        "file_path": module.file_path,

                        "example_name":
                            example.example_name,

                        "tags":
                            ",".join(example.tags),

                        "export":
                            module.export,

                        "deps":
                            ",".join(module.deps),

                        "start_line":
                            module.start_line,

                        "end_line":
                            module.end_line,
                    },

                    # AI prompt rebuild 用
                    "prompt_text":
                        module.prompt_text,

                    "source":
                        module.source,
                })

            # =================================================
            # add to vector db
            # =================================================

            store.add_documents(
                vector_chunks
            )

            total_modules += len(vector_chunks)

            print(
                f"  -> semantic modules: "
                f"{len(vector_chunks)}"
            )

        except Exception as e:

            print(f"❌ Semantic失败: {path}")

            print(e)

    print(
        f"\n✅ Semantic完成，总 modules: "
        f"{total_modules}"
    )
