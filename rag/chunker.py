# 单文件 → chunks（纯AST）
# 2026-4-23

import ast
import json
import re
from typing import List,Tuple

# ===============================
# 数据结构
# ===============================

class CodeChunk:
    def __init__(self, cid, ctype, name, source, start_line, end_line, parent=None,  kind="func"):
        self.id = cid
        self.type = ctype
        self.name = name
        self.kind = kind   # ⭐ 新增
        self.source = source
        self.start_line = start_line
        self.end_line = end_line
        self.parent = parent
        self.sub_chunks = []

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
    # {file_id}:{class}.{name}#{kind}
    
    def __init__(self, file_path: str):
        with open(file_path, "r", encoding="utf-8") as f:
            self.code = f.read()

        self.file_path = file_path
        self.file_id = self.file_path.replace("\\", ".").replace("/", ".")
        self.lines = self.code.splitlines()

        self.ext = file_path.split(".")[-1]

    # ===============================
    # 公共工具
    # ===============================

    def _extend_up_comments(self, lineno: int) -> int:
        i = lineno - 2
        while i >= 0:
            line = self.lines[i].strip()
            if line.startswith("#"):
                i -= 1
            else:
                break
        return i + 2

    def _slice_block(self, start_line: int) -> Tuple[str, int, int]:
        """根据缩进获取代码块"""
        start_idx = start_line - 1
        base_indent = len(self.lines[start_idx]) - len(self.lines[start_idx].lstrip())

        end = start_idx

        for i in range(start_idx + 1, len(self.lines)):
            line = self.lines[i]
            if not line.strip():
                continue

            indent = len(line) - len(line.lstrip())
            if indent <= base_indent:
                break
            end = i

        new_start = self._extend_up_comments(start_line)
        source = "\n".join(self.lines[new_start-1:end+1])
        return source, new_start, end + 1

    # ===============================
    # Python AST
    # ===============================
    def _detect_kind_ast(self, node):
        if not node.decorator_list:
            return "func"

        for d in node.decorator_list:
            if isinstance(d, ast.Attribute):
                if d.attr == "setter":
                    return "setter"
            if isinstance(d, ast.Name):
                if d.id == "property":
                    return "getter"
                if d.id == "classmethod":
                    return "classmethod"
                if d.id == "staticmethod":
                    return "staticmethod"

        return "func"
    
    def _chunk_py(self):
        tree = ast.parse(self.code)
        chunks = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                source, s, e = self._get_source_ast(node)

                chunks.append(CodeChunk(
                    cid=f"{self.file_id}:{node.name}",
                    ctype="class",
                    name=node.name,
                    source=source,
                    start_line=s,
                    end_line=e
                ))

                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        source, s, e = self._get_source_ast(item)

                        chunks.append(CodeChunk(
                            cid=f"{self.file_id}:{node.name}.{item.name}",
                            ctype="method",
                            name=item.name,
                            parent=node.name,
                            source=source,
                            start_line=s,
                            end_line=e,
                            kind = self._detect_kind_ast(node)
                        ))

            elif isinstance(node, ast.FunctionDef):
                source, s, e = self._get_source_ast(node)

                chunks.append(CodeChunk(
                    cid=node.name,
                    ctype="function",
                    name=node.name,
                    source=source,
                    start_line=s,
                    end_line=e
                ))

        return chunks

    def _get_source_ast(self, node):
        start = node.lineno
        end = node.end_lineno
        new_start = self._extend_up_comments(start)
        source = "\n".join(self.lines[new_start-1:end])
        return source, new_start, end

    # ===============================
    # Cython（核心）
    # ===============================

    def _detect_kind(self, line: str, prev_lines: List[str]):
        """
        判断 getter / setter / classmethod 等
        """
        decorators = []

        # 向上找 decorator（最多3行）
        for l in reversed(prev_lines[-3:]):
            l = l.strip()
            if l.startswith("@"):
                decorators.append(l)
            else:
                break

        for d in decorators:
            if ".setter" in d:
                return "setter"
            if ".getter" in d:
                return "getter"
            if "@property" in d:
                return "getter"
            if "@classmethod" in d:
                return "classmethod"
            if "@staticmethod" in d:
                return "staticmethod"

        return "func"
    
    def _chunk_pyx(self):

        chunks = []

        class_pattern = re.compile(r"^\s*(cdef\s+)?class\s+(\w+)")
        func_pattern = re.compile(r"^\s*(cdef|cpdef|def)\s+[\w\*\s]*?(\w+)\s*\(")

        current_class = None

        for idx, line in enumerate(self.lines):
            lineno = idx + 1

            # ---------- class ----------
            m = class_pattern.match(line)
            if m:
                cls_name = m.group(2)
                source, s, e = self._slice_block(lineno)

                chunks.append(CodeChunk(
                    cid=f"{self.file_id}:{cls_name}",
                    ctype="class",
                    name=cls_name,
                    source=source,
                    start_line=s,
                    end_line=e
                ))

                current_class = cls_name
                continue

            # ---------- function ----------
            m = func_pattern.match(line)
            if m:
                func_name = m.group(2)
                source, s, e = self._slice_block(lineno)

                if current_class:
                    kind = self._detect_kind(line, self.lines[:idx])
                    cid = f"{self.file_id}:{current_class}.{func_name}#{kind}"
                    ctype = "method"
                    parent = current_class
                else:
                    cid = f"{self.file_id}:{func_name}"
                    ctype = "function"
                    parent = None

                chunks.append(CodeChunk(
                    cid=cid,
                    ctype=ctype,
                    name=func_name,
                    parent=parent,
                    source=source,
                    start_line=s,
                    end_line=e
                ))

        return chunks

    # ===============================
    # 主入口
    # ===============================

    def chunk(self) -> List:
        if self.ext == "py":
            return self._chunk_py()

        elif self.ext == "pyx":
            print(f"[INFO] 使用 Cython 解析: {self.file_path}")
            return self._chunk_pyx()

        else:
            print(f"[WARN] 跳过不支持文件: {self.file_path}")
            return []
        
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
