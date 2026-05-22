# rag/debug_retriever.py
# 更新于 RAG V0.2.0
# 2026-5-22
"""
RAG 检索调试工具（基于新版 retriever.py）

用法：
    python rag/debug_retriever.py <collection_name>

示例：
    python rag/debug_retriever.py case_generator
    python rag/debug_retriever.py conversion

说明：
    - collection_name 对应 ./rag_db/ 下的子目录名
    - 进入交互模式后输入查询语句，回车即可查看 Top‑5 检索结果
    - 输入 exit 或 quit 退出
"""

import sys
import argparse
from typing import Dict, Any

from retriever import RAGRetriever


def format_metadata(meta: Dict[str, Any]) -> str:
    """将 metadata 格式化为易读的字符串（兼容 semantic / AST 两种知识库）"""
    lines = []

    # 通用字段
    if "file_path" in meta:
        lines.append(f"📁 文件: {meta['file_path']}")
    elif "file" in meta:
        lines.append(f"📁 文件: {meta['file']}")

    if "module_name" in meta:
        lines.append(f"🏷️  模块名: {meta['module_name']}")
    elif "name" in meta:
        lines.append(f"🏷️  名称: {meta['name']}")

    if "type" in meta:
        lines.append(f"📌 类型: {meta['type']}")

    # 行号（两种命名）
    start = meta.get("start_line") or meta.get("start")
    end = meta.get("end_line") or meta.get("end")
    if start and end:
        lines.append(f"📍 行号: {start} - {end}")

    # semantic 特有字段
    if "tags" in meta and meta["tags"]:
        lines.append(f"🔖 标签: {meta['tags']}")
    if "export" in meta:
        lines.append(f"📤 导出: {meta['export']}")
    if "deps" in meta and meta["deps"]:
        lines.append(f"⛓️ 依赖: {meta['deps']}")

    return "\n".join(lines)


def pretty_print_results(results, topk: int = 5):
    """格式化打印检索结果"""
    if not results:
        print("⚠️ 无检索结果")
        return

    for i, item in enumerate(results[:topk]):
        print("\n" + "=" * 60)
        print(f"📌 结果 #{i+1}  (相似度: {item['score']:.4f})")
        print("-" * 60)
        print(format_metadata(item["metadata"]))
        print("-" * 60)
        # 显示文档内容（最多 800 字符）
        doc = item["document"].strip()
        if len(doc) > 800:
            doc = doc[:800] + "...(截断)"
        print("📄 内容预览:")
        print(doc)
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="RAG 检索调试工具（基于新版 retriever）"
    )
    parser.add_argument(
        "collection",
        nargs="?",
        default=None,
        help="知识库名称（对应 ./rag_db/ 下的子目录，如 case_generator 或 conversion）"
    )
    parser.add_argument(
        "--topk",
        type=int,
        default=5,
        help="返回结果数量 (默认 5)"
    )
    args = parser.parse_args()

    # 确定 collection_name
    collection_name = args.collection
    if not collection_name:
        # 交互式询问
        print("可用的知识库目录（请查看 ./rag_db/ 下的子文件夹）：")
        print("  常见: case_generator, conversion")
        collection_name = input("请输入 collection_name: ").strip()
        if not collection_name:
            print("❌ 未提供 collection_name，退出")
            sys.exit(1)

    # 初始化检索器
    try:
        retriever = RAGRetriever(db_root="./rag_db")
        # 尝试获取 collection，若不存在会抛出异常
        retriever.get_collection(collection_name)
        print(f"✅ 已连接到知识库: {collection_name}")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print(f"   请确保 ./rag_db/{collection_name} 存在且已构建索引")
        sys.exit(1)

    print("\n🚀 RAG 调试控制台 (新版)")
    print("  输入查询语句 (支持自然语言)")
    print("  输入 exit / quit 退出\n")

    while True:
        try:
            query = input("🔍 Query > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye~")
            break

        if query.lower() in ("exit", "quit"):
            break
        if not query:
            continue

        # 执行检索
        results = retriever.search(
            query=query,
            collection_name=collection_name,
            topk=args.topk,
        )

        pretty_print_results(results, topk=args.topk)


if __name__ == "__main__":
    main()