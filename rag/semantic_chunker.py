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
        r"#\s*@EXAMPLE_BEGIN:\s*(.+)"
    )

    RE_EXAMPLE_TAG = re.compile(
        r"#\s*@EXAMPLE_TAG:\s*(.+)"
    )

    RE_EXAMPLE_END = re.compile(
        r"#\s*@EXAMPLE_END"
    )

    RE_RAG_BEGIN = re.compile(
        r"#\s*@RAG_BEGIN:\s*(\w+)"
    )

    RE_RAG_END = re.compile(
        r"#\s*@RAG_END"
    )

    RE_RAG_EXPORT = re.compile(
        r"#\s*@RAG_EXPORT:\s*(\w+)"
    )

    RE_RAG_DEP = re.compile(
        r"#\s*@RAG_DEP:\s*(.+)"
    )

    RE_RAG_MODULE_SETTING = re.compile(
        r"#\s*@RAG_MODULE_SETTING:\s*(.+)"
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

        current_module = None

        module_start = 0

        module_lines = []

        source_lines = []

        for idx, line in enumerate(self.lines):

            lineno = idx + 1

            source_lines.append(line)

            # -----------------------------------------
            # example begin
            # -----------------------------------------

            m = self.RE_EXAMPLE_BEGIN.match(line)

            if m:

                example_name = m.group(1).strip()

                in_example = True

                example_start = lineno

                continue

            # -----------------------------------------
            # tags
            # -----------------------------------------

            m = self.RE_EXAMPLE_TAG.match(line)

            if m:

                tags = [
                    x.strip()
                    for x in m.group(1).split(",")
                ]

                continue

            # -----------------------------------------
            # RAG begin
            # -----------------------------------------

            m = self.RE_RAG_BEGIN.match(line)

            if m:

                current_module = m.group(1).strip()

                module_start = lineno

                module_lines = []

                continue

            # -----------------------------------------
            # inside module
            # -----------------------------------------

            if current_module:

                module_lines.append(line)

                # -------------------------
                # RAG END
                # -------------------------

                m_end = self.RE_RAG_END.match(line)

                if m_end:

                    module_source = "\n".join(module_lines)

                    module = self._build_module(
                        current_module,
                        module_source,
                        module_start,
                        lineno
                    )

                    rag_modules[current_module] = module

                    current_module = None

                    module_lines = []

        # =================================================
        # 完整文件
        # =================================================

        full_source = "\n".join(source_lines)

        example = ExampleFile(
            example_name=example_name,
            tags=tags,
            file_path=self.file_path,
            source=full_source,
            rag_modules=rag_modules
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
        end_line: int
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

                deps.extend([
                    x.strip()
                    for x in m.group(1).split(",")
                ])

            m = self.RE_RAG_MODULE_SETTING.match(line)

            if m:

                settings.append(
                    m.group(1).strip()
                )

        # =================================================
        # embedding text
        # 去除 @RAG_* 标记
        # =================================================

        embedding_lines = []

        for line in source.splitlines():

            if "@RAG_" in line:
                continue

            embedding_lines.append(line)

        embedding_text = "\n".join(
            embedding_lines
        ).strip()

        # =================================================
        # prompt text
        # =================================================

        prompt_lines = []

        # 若存在 @RAG_MODULE_SETTING 块，则按行添加到 prompt_lines 中
        if settings:

            prompt_lines.append(
                "# Module Settings"
            )

            for s in settings:

                prompt_lines.append(
                    f"# {s}"
                )

            prompt_lines.append("")

        for line in source.splitlines():

            if "@RAG_" in line:
                continue

            prompt_lines.append(line)

        prompt_text = "\n".join(
            prompt_lines
        ).strip()

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