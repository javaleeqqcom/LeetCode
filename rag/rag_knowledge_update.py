# rag/rag_knowledge_update.py
# 更新于 RAG V0.2.0
# 2026-5-22

from pathlib import Path
import time

from .docs_inclusion import build_docs_inclusion

from .index_builder import build_index
from .semantic_index_builder import build_semantic_index


# =========================================================
# config
# =========================================================

CASE_GENERATOR_ROOT = (
    "rag_knowledge/case_generator"
)

CONVERSION_ROOT = (
    "rag_knowledge/conversion"
)

DOCS_DIR = "./rag_docs"


# =========================================================
# helper
# =========================================================

def latest_docs_file(prefix: str):

    root = Path(DOCS_DIR)

    if not root.exists():
        return None

    files = sorted(
        root.glob(f"{prefix}_*.json")
    )

    if not files:
        return None

    return str(files[-1])


# =========================================================
# build one knowledge
# =========================================================

def build_case_generator():

    print("\n" + "=" * 60)
    print("🚀 更新 case_generator semantic RAG")
    print("=" * 60)

    prev = latest_docs_file(
        "case_generator"
    )

    docs_file = build_docs_inclusion(
        CASE_GENERATOR_ROOT,
        out_dir=DOCS_DIR,
        auto_select= True
    )

    # rename
    ts = int(time.time())

    renamed = (
        f"{DOCS_DIR}/"
        f"case_generator_{ts}.json"
    )

    Path(docs_file).rename(renamed)

    build_semantic_index(
        renamed,
        "case_generator",
        prev
    )


def build_conversion():

    print("\n" + "=" * 60)
    print("🚀 更新 conversion AST RAG")
    print("=" * 60)

    prev = latest_docs_file(
        "conversion"
    )

    docs_file = build_docs_inclusion(
        CONVERSION_ROOT,
        out_dir=DOCS_DIR,
        auto_select=True
    )

    ts = int(time.time())

    renamed = (
        f"{DOCS_DIR}/"
        f"conversion_{ts}.json"
    )

    Path(docs_file).rename(renamed)

    build_index(
        renamed,
        "conversion",
        prev
    )


# =========================================================
# main
# =========================================================

if __name__ == "__main__":

    build_case_generator()

    build_conversion()

    print("\n🎉 全部 RAG 更新完成")
