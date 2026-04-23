# rag/docs_inclusion.py
import os
import json
import hashlib
import time
from typing import List, Dict

SUPPORTED_EXT = (".py", ".pyx")

# ===============================
# 工具函数
# ===============================

def calc_file_hash(path: str) -> str:
    """计算文件内容 hash"""
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def scan_files(root: str) -> List[str]:
    """扫描目录"""
    result = []
    for base, _, files in os.walk(root):
        for f in files:
            if f.endswith(SUPPORTED_EXT):
                result.append(os.path.join(base, f))
    return result


# ===============================
# CLI 勾选（简化版）
# ===============================
def parse_selection(choice: str, max_idx: int):
    """
    支持：
    - a            → 全选
    - 0,2,5        → 离散
    - 0-10         → 区间
    - 0-3,5,7-9    → 混合
    """
    choice = choice.strip()

    if choice == "a":
        return list(range(max_idx))

    result = set()

    parts = choice.split(",")

    for part in parts:
        part = part.strip()

        if "-" in part:
            try:
                start, end = part.split("-")
                start, end = int(start), int(end)
                if start > end:
                    start, end = end, start
                result.update(range(start, end + 1))
            except:
                raise ValueError(f"非法区间: {part}")
        else:
            try:
                result.add(int(part))
            except:
                raise ValueError(f"非法输入: {part}")

    # 边界过滤
    return sorted(i for i in result if 0 <= i < max_idx)

def cli_select(files: List[str]) -> List[str]:
    print("\n📂 发现文件：")
    for i, f in enumerate(files):
        print(f"[{i}] {f}")

    print("\n输入选择：")
    print("  a = 全选")
    print("  0,2,5 = 离散选择")
    print("  0-10 = 区间选择")
    print("  0-3,5,7-9 = 混合选择")

    choice = input("选择: ").strip()

    idxs = parse_selection(choice, len(files))

    if not idxs:
        print("⚠️ 未选择任何文件")
        return []

    return [files[i] for i in idxs]

# ===============================
# 主逻辑
# ===============================

def build_docs_inclusion(root_dir: str, out_dir="./rag_chunk"):
    files = scan_files(root_dir)

    if not files:
        print("⚠️ 未找到代码文件")
        return

    selected = cli_select(files)

    docs = []
    for path in selected:
        stat = os.stat(path)
        docs.append({
            "root": root_dir,
            "path": path,
            "file": os.path.basename(path),
            "mtime": stat.st_mtime,
            "hash": calc_file_hash(path)
        })

    ts = int(time.time())
    out_file = os.path.join(out_dir, f"docs_inclusion_{ts}.json")

    os.makedirs(out_dir, exist_ok=True)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 已保存: {out_file}")
    return out_file


# ===============================
# 增量检测
# ===============================

def diff_docs(old_docs: List[Dict], new_docs: List[Dict]):
    """找出变化文件"""
    old_map = {(d["root"], d["file"]): d for d in old_docs}

    changed = []

    for d in new_docs:
        key = (d["root"], d["file"])

        if key not in old_map:
            changed.append(d)
            continue

        old = old_map[key]
        if d["hash"] != old["hash"]:
            changed.append(d)

    return changed


# ===============================
# CLI
# ===============================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python rag/docs_inclusion.py <root_dir>")
        exit(1)

    build_docs_inclusion(sys.argv[1])