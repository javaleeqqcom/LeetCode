# rag/debug_retriever.py
# 更新于 RAG V0.2.2
# 2026-5-22
"""
RAG 检索调试工具（基于新版 retriever.py）
用法：
    python rag/debug_retriever.py <collection_name>
示例：
    python rag/debug_retriever.py case_generator
    python rag/debug_retriever.py conversion
说明：
    - collection_name 为 ChromaDB 集合名（如 case_generator, conversion）
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


def list_collections(db_root="./rag_db") -> list:
    """列出 ChromaDB 中所有集合名称"""
    import chromadb
    client = chromadb.PersistentClient(path=db_root)
    return client.list_collections()


def main():
    parser = argparse.ArgumentParser(
        description="RAG 检索调试工具（基于新版 retriever）"
    )
    parser.add_argument(
        "collection",
        nargs="?",
        default=None,
        help="知识库集合名（如 case_generator 或 conversion）"
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
        # 自动列出所有可用集合
        print("🔍 正在连接 ChromaDB 并获取可用集合...")
        try:
            available = list_collections()
            if not available:
                print("❌ 未找到任何集合，请先运行 rag/rag_knowledge_update.py 构建索引。")
                sys.exit(1)
            print("可用集合：")
            for i, col in enumerate(available):
                print(f"  [{i}] {col}")
            choice = input("请输入集合编号或名称: ").strip()
            if choice.isdigit():
                idx = int(choice)
                if 0 <= idx < len(available):
                    collection_name = available[idx]
                else:
                    print("❌ 无效编号")
                    sys.exit(1)
            else:
                collection_name = choice
        except Exception as e:
            print(f"❌ 无法获取集合列表: {e}")
            sys.exit(1)

    # 初始化检索器
    try:
        retriever = RAGRetriever(db_root="./rag_db")
        # 尝试获取 collection，若不存在会抛出异常
        retriever.get_collection(collection_name)
        print(f"✅ 已连接到知识库集合: {collection_name}")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print(f"   请确保集合 `{collection_name}` 已存在，可运行 rag/rag_knowledge_update.py 构建索引。")
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