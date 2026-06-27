# rag/semantic_chunker.py
# 更新于 RAG V0.1.2
# 2026-5-16

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


# =========================================================
# 数据结构
# =========================================================

@dataclass
class RAGModule:
    module_id: str
    name: str
    file_path: str
    start_line: int
    end_line: int
    source: str
    export: str = "no"
    deps: List[str] = field(default_factory=list)
    settings: List[str] = field(default_factory=list)
    embedding_text: str = ""
    prompt_text: str = ""
    parent: str = ""          # 新增：父模块名（顶层为空字符串）

@dataclass
class ExampleFile:

    example_name: str

    tags: List[str]

    file_path: str

    source: str

    rag_modules: Dict[str, RAGModule] = field(default_factory=dict)


# =========================================================
# Parser
# =========================================================

class SemanticChunker:

    RE_EXAMPLE_BEGIN = re.compile(
        r"\s*#\s*@EXAMPLE_BEGIN:\s*(.+)"
    )
    RE_EXAMPLE_TAG = re.compile(
        r"\s*#\s*@EXAMPLE_TAG:\s*(.+)"
    )
    RE_EXAMPLE_END = re.compile(
        r"\s*#\s*@EXAMPLE_END"
    )
    RE_RAG_BEGIN = re.compile(
        r"\s*#\s*@RAG_BEGIN:\s*(\w+)"
    )
    RE_RAG_END = re.compile(
        r"\s*#\s*@RAG_END"
    )
    RE_RAG_EXPORT = re.compile(
        r"\s*#\s*@RAG_EXPORT:\s*(\w+)"
    )
    RE_RAG_DEP = re.compile(
        r"\s*#\s*@RAG_DEP:\s*(.+)"
    )
    RE_RAG_MODULE_SETTING = re.compile(
        r"\s*#\s*@RAG_MODULE_SETTING:\s*(.+)"
    )

    def __init__(self, file_path: str):

        self.file_path = str(file_path)

        self.lines = Path(file_path).read_text(
            encoding="utf-8"
        ).splitlines()

    # =====================================================
    # 主入口
    # =====================================================
    def parse(self) -> ExampleFile:
        example_name = ""
        tags = []
        rag_modules = {}
        in_example = False
        example_start = 0

        # 模块栈：每个元素为 (module_name, start_line, collected_lines)
        module_stack = []

        source_lines = []

        for idx, line in enumerate(self.lines):
            lineno = idx + 1
            source_lines.append(line)

            # --- example begin ---
            m = self.RE_EXAMPLE_BEGIN.match(line)
            if m:
                example_name = m.group(1).strip()
                in_example = True
                example_start = lineno
                continue

            # --- tags ---
            m = self.RE_EXAMPLE_TAG.match(line)
            if m:
                tags = [x.strip() for x in m.group(1).split(",")]
                continue

            # --- RAG_BEGIN：压入新模块 ---
            m = self.RE_RAG_BEGIN.match(line)
            if m:
                module_name = m.group(1).strip()
                module_stack.append((module_name, lineno, []))
                continue

            # --- 当前处于某个模块内部 ---
            if module_stack:
                current_name, start_line, module_lines = module_stack[-1]
                # 遇到 RAG_END：弹出当前模块并构建
                if self.RE_RAG_END.match(line):
                    module_stack.pop()
                    module_source = "\n".join(module_lines)
                    # 确定父模块
                    parent_name = ""
                    if module_stack:
                        parent_name = module_stack[-1][0]
                    module = self._build_module(
                        current_name,
                        module_source,
                        start_line,
                        lineno,
                        parent_name,
                    )
                    rag_modules[current_name] = module
                else:
                    # 普通行：追加到当前模块
                    module_stack[-1][2].append(line)

        full_source = "\n".join(source_lines)
        example = ExampleFile(
            example_name=example_name,
            tags=tags,
            file_path=self.file_path,
            source=full_source,
            rag_modules=rag_modules,
        )
        self._check_dependencies(example)
        return example

    # =====================================================
    # build module
    # =====================================================
    def _build_module(
        self,
        name: str,
        source: str,
        start_line: int,
        end_line: int,
        parent: str = "",
    ) -> RAGModule:
        export = "no"
        deps = []
        settings = []
        for line in source.splitlines():
            m = self.RE_RAG_EXPORT.match(line)
            if m:
                export = m.group(1).strip()
            m = self.RE_RAG_DEP.match(line)
            if m:
                deps.extend([x.strip() for x in m.group(1).split(",")])
            m = self.RE_RAG_MODULE_SETTING.match(line)
            if m:
                settings.append(m.group(1).strip())

        # embedding_text：去除所有 @RAG_* 行
        embedding_lines = []
        for line in source.splitlines():
            if "@RAG_" in line:
                continue
            embedding_lines.append(line)
        embedding_text = "\n".join(embedding_lines).strip()

        # prompt_text：保留 settings 标记，但去除其他 @RAG_
        prompt_lines = []
        if settings:
            prompt_lines.append("# Module Settings")
            for s in settings:
                prompt_lines.append(f"# {s}")
            prompt_lines.append("")
        for line in source.splitlines():
            if "@RAG_" in line:
                continue
            prompt_lines.append(line)
        prompt_text = "\n".join(prompt_lines).strip()

        return RAGModule(
            module_id=f"{self.file_path}:{name}",
            name=name,
            file_path=self.file_path,
            start_line=start_line,
            end_line=end_line,
            source=source,
            export=export,
            deps=deps,
            settings=settings,
            embedding_text=embedding_text,
            prompt_text=prompt_text,
            parent=parent,
        )

    # =====================================================
    # DAG 检测
    # =====================================================

    def _check_dependencies(
        self,
        example: ExampleFile
    ):

        graph = {
            k: v.deps
            for k, v in example.rag_modules.items()
        }

        visited = set()

        stack = set()

        def dfs(node):

            if node in stack:
                raise ValueError(
                    f"检测到循环依赖: {node}"
                )

            if node in visited:
                return

            stack.add(node)

            for dep in graph.get(node, []):

                if dep not in graph:

                    raise ValueError(
                        f"{node} 依赖不存在模块 {dep}"
                    )

                dfs(dep)

            stack.remove(node)

            visited.add(node)

        for node in graph:
            dfs(node)

    # =====================================================
    # prompt rebuild
    # =====================================================

    def rebuild_prompt_modules(
        self,
        example: ExampleFile,
        module_names: List[str]
    ) -> str:

        ordered = []

        visited = set()

        def add_module(name):

            if name in visited:
                return

            visited.add(name)

            module = example.rag_modules[name]

            for dep in module.deps:
                add_module(dep)

            ordered.append(module)

        for m in module_names:
            add_module(m)

        result = []

        for module in ordered:

            result.append(
                f"# =================================="
            )

            result.append(
                f"# MODULE: {module.name}"
            )

            result.append(
                f"# =================================="
            )

            result.append(
                module.prompt_text
            )

            result.append("")

        return "\n".join(result)