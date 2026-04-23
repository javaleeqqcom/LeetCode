# 单文件 → chunks（纯AST）
# 2026-4-23

import ast
import json

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
    def __init__(self, file_path: str):
        
        with open(file_path, "r", encoding="utf-8") as f:
            self.code = f.read()

        # 需要检查是否为 .py 文件（ast 仅支持 Python 语法）
        # 将来分片其他文件，需要用其他逻辑

        self.file_path = file_path
        self.file_id = self.file_path.replace("\\", ".").replace("/", ".")
        self.lines = self.code.splitlines()

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
                    cid = f"{self.file_id}:{node.name}",
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
                            cid=f"{self.file_id}:{node.name}.{item.name}",
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
