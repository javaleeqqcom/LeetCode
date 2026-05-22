# 📘 LeetCode 本地自动化测试框架（Python）+ RAG 增强版

* 版本：0.2.0（双知识库 · 语义 + AST）

---

## 🧠 系统整体架构（最新版）

本系统在原有自动化测试框架基础上，引入 **双知识库 RAG 架构**：

- **Semantic 知识库**（case_generator）：基于人工标注的代码切片，用于生成测试用例 / 调试建议
- **AST 知识库**（conversion）：基于语法树自动抽取的代码切片，用于代码转换 / 结构理解

```text
┌─────────────────────────────────────────────────────────────┐
│                      代码源文件目录                          │
│   case_generator/                 conversion/               │
└───────────────┬─────────────────────────┬───────────────────┘
                │                         │
                ▼                         ▼
       docs_inclusion.py           docs_inclusion.py
        （交互式选择 + 哈希增量）      （交互式选择 + 哈希增量）
                │                         │
                ▼                         ▼
        docs_inclusion_*.json      docs_inclusion_*.json
                │                         │
                ▼                         ▼
    semantic_index_builder.py      index_builder.py
       （SemanticChunker）            （CodeChunker）
                │                         │
                ▼                         ▼
          VectorStore                   VectorStore
       (collection: case_generator)  (collection: conversion)
                │                         │
                └─────────────┬───────────┘
                              ▼
                    rag_knowledge_update.py
                      （统一更新入口）
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      检索阶段（LLM 增强）                     │
│   retriever.py  →  向量检索  →  构建上下文  →  Prompt 拼接   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 模块说明（按文件）

### 1. `docs_inclusion.py` – 文件选择与变更检测
- 用于选择需要RAG向量化的 python 代码文件。
- 提供 CLI 人工交互选择或自动选择。

| 函数 / 类 | 描述 |
|----------|------|
| `calc_file_hash(path)` | 计算文件 MD5 哈希，用于增量更新 |
| `scan_files(root)` | 递归扫描目录下所有 `.py` / `.pyx` 文件 |
| `parse_selection(choice, max_idx)` | 解析用户输入（如 `0-3,5,7-9`），返回选中索引列表 |
| `cli_select(files)` | 交互式 CLI 让用户勾选需要构建索引的文件 |
| `build_docs_inclusion(root_dir, out_dir, auto_select)` | 生成 `docs_inclusion_{timestamp}.json`，记录文件路径、hash、修改时间 |
| `diff_docs(old_docs, new_docs)` | 对比新旧两份 JSON，返回新增或哈希变化的文件列表 |

### 2. `chunker.py` – AST 代码切片（用于 conversion 知识库）

| 类 / 函数 | 描述 |
|----------|------|
| `CodeChunk` | 代码切片数据结构：包含 `id`, `type`（class/method/function）, `name`, `source`, `start_line`, `end_line`, `parent`, `file_path` 等 |
| `CodeChunker(file_path)` | 根据文件扩展名（`.py` 或 `.pyx`）选择解析器 |
| `CodeChunker._chunk_py()` | 使用 Python `ast` 模块解析类、方法、函数，生成 `CodeChunk` 列表 |
| `CodeChunker._chunk_pyx()` | 使用正则表达式解析 Cython 文件，支持 `cdef class` / `cdef` / `cpdef` / `def`，并识别装饰器（`@property` / `@setter` 等） |
| `save_chunks_readable(chunks, out_file)` | 将 chunks 保存为可读文本文件（调试用） |
| `save_chunks_json(chunks, out_file)` | 将 chunks 保存为 JSON 文件（调试用） |

### 3. `semantic_chunker.py` – 语义代码切片（用于 case_generator 知识库）

| 类 / 函数 | 描述 |
|----------|------|
| `RAGModule` | 语义模块数据结构：包含 `name`, `source`, `deps`（依赖模块列表）, `export`, `settings`, `embedding_text`（去除 `@RAG_*` 标记后的纯代码）, `prompt_text`（用于 LLM 拼接的文本） |
| `ExampleFile` | 代表一个标注了 `@EXAMPLE_BEGIN` / `@EXAMPLE_TAG` 的文件，包含多个 `RAGModule` |
| `SemanticChunker(file_path)` | 解析包含特殊标记的 `.py` 文件：<br> - `# @EXAMPLE_BEGIN: name`<br> - `# @EXAMPLE_TAG: tag1,tag2`<br> - `# @RAG_BEGIN: module_name` … `# @RAG_END`<br> - `# @RAG_EXPORT: yes/no`<br> - `# @RAG_DEP: dep1,dep2`<br> - `# @RAG_MODULE_SETTING: ...` |
| `SemanticChunker.parse()` | 主入口，返回 `ExampleFile` 对象，并自动检测循环依赖 |
| `SemanticChunker.rebuild_prompt_modules()` | 根据模块名列表（自动包含依赖）拼接出用于 LLM 的 prompt 文本 |

### 4. `embedding.py` – 向量存储与嵌入封装

| 类 / 函数 | 描述 |
|----------|------|
| `VectorStore(db_path, collection_name)` | 基于 ChromaDB 的持久化向量库封装 |
| `VectorStore.add_chunks(chunks)` | **（旧版）** 将 `CodeChunk` 列表入库（已警告为旧版） |
| `VectorStore.add_documents(docs)` | 将语义模块（`RAGModule`）转换为 `{id, document, metadata}` 格式入库 |
| `OllamaEmbeddingFunction(model)` | 兼容 ChromaDB 的 embedding 函数，通过 Ollama HTTP API 调用 `qwen3-embed-0.6b` 模型 |

### 5. `index_builder.py` – AST 索引构建器

| 函数 | 描述 |
|------|------|
| `load_docs(path)` | 加载 `docs_inclusion_*.json` |
| `build_index(docs_file, collection_name, prev_docs_file)` | 主流程：<br> 1. 加载文档列表<br> 2. 若提供 `prev_docs_file` 则执行增量 diff<br> 3. 对每个文件实例化 `CodeChunker` → 生成 `CodeChunk` 列表<br> 4. 保存 `.txt` / `.json` 调试文件到 `./rag_chunk/`<br> 5. 调用 `VectorStore.add_chunks()` 入库 |

### 6. `semantic_index_builder.py` – 语义索引构建器

| 函数 | 描述 |
|------|------|
| `load_docs(path)` | 加载 `docs_inclusion_*.json` |
| `build_semantic_index(docs_file, collection_name, prev_docs_file)` | 主流程：<br> 1. 加载文档列表，增量 diff<br> 2. 对每个文件实例化 `SemanticChunker` → 调用 `parse()` 获得 `ExampleFile`<br> 3. 将每个 `RAGModule` 转换为 vector chunk（`embedding_text` 作为 document，`prompt_text` 保留在 metadata 中）<br> 4. 保存 `.semantic.json` 调试文件到 `./rag_chunk/`<br> 5. 调用 `VectorStore.add_documents()` 入库 |

### 7. `retriever.py` – 检索器（供 LLM 调用）

| 类 / 函数 | 描述 |
|----------|------|
| `OllamaEmbedding` | 轻量 embedding 客户端，仅提供 `embed(text)` 方法 |
| `RAGRetriever(db_root)` | 检索器主类，支持多 collection（`case_generator` / `conversion`） |
| `RAGRetriever.get_collection(collection_name)` | 懒加载 ChromaDB collection |
| `RAGRetriever.search(query, collection_name, topk, where)` | 向量检索，返回 `{score, document, metadata}` 列表 |
| `RAGRetriever.build_context(query, collection_name, topk)` | 将检索结果格式化为文本块（包含文件路径、类型、名称、内容），可直接拼接至 prompt |

### 8. `rag_knowledge_update.py` – 统一知识库更新入口

| 函数 | 描述 |
|------|------|
| `latest_docs_file(prefix)` | 从 `./rag_docs/` 中找到最新的 `{prefix}_*.json` 文件 |
| `build_case_generator()` | 更新 semantic 知识库：<br> 1. 调用 `build_docs_inclusion(CASE_GENERATOR_ROOT, auto_select=True)`<br> 2. 重命名生成的文件为 `case_generator_{timestamp}.json`<br> 3. 调用 `build_semantic_index()` 增量构建 |
| `build_conversion()` | 更新 AST 知识库：流程同上，调用 `build_index()` |
| `main` | 依次执行 `build_case_generator()` 和 `build_conversion()` |

---

## 🚀 快速使用

### 构建 / 更新知识库

```bash
# 1. 自动扫描并更新两个知识库
python rag/rag_knowledge_update.py

# 2. 单独更新 AST 索引（交互式选择文件）
python rag/index_builder.py ./rag_docs/conversion_xxx.json

# 3. 单独更新 Semantic 索引
python rag/semantic_index_builder.py ./rag_docs/case_generator_xxx.json
```

### 检索测试

```python
from rag.retriever import RAGRetriever

retriever = RAGRetriever()
context = retriever.build_context(
    query="如何实现链表打印函数？",
    collection_name="case_generator",
    topk=3
)
print(context)
```

### 与 `SolutionRunner` 集成（最小侵入）

```python
# 原 prompt = build_prompt(question, code)
retriever = RAGRetriever()
chunks = retriever.build_context(question + code, "case_generator")
prompt = f"{question}\n\n学生代码：\n{code}\n\n相关代码上下文：\n{chunks}"
```

---

## 📁 目录结构（RAG 模块）

```
rag/
├── docs_inclusion.py         # 文件选择 + 哈希变更检测
├── chunker.py                # AST 切片（.py / .pyx）
├── semantic_chunker.py       # 语义切片（基于标注）
├── embedding.py              # ChromaDB + Ollama embedding
├── index_builder.py          # AST 索引构建
├── semantic_index_builder.py # 语义索引构建
├── retriever.py              # 检索器 + 上下文构建
├── rag_knowledge_update.py   # 统一更新入口
└── (输出目录)
    ├── rag_db/               # ChromaDB 持久化数据
    │   ├── case_generator/
    │   └── conversion/
    ├── rag_docs/             # docs_inclusion_*.json
    └── rag_chunk/            # 调试用 JSON/TXT 切片导出
```

---

## 🔮 能力对比（当前系统）

| 能力         | 原系统（纯 Prompt） | 当前系统（双知识库 RAG） |
| ------------ | ------------------- | ------------------------- |
| 代码结构理解 | ❌                  | ✅（AST + 语义切片）       |
| 方法关联     | ❌                  | ✅（依赖字段 + 父子关系）  |
| 类上下文补全 | ❌                  | ✅                         |
| 增量更新     | ❌                  | ✅（基于文件 hash）        |
| 跨库检索     | ❌                  | ✅（多 collection）        |
| 测试用例生成 | ⚠️ 不稳定           | ✅（稳定提升）             |

---

## ⚠️ 已知限制

- `chunker.py` 中 `add_chunks` 方法已标记为旧版，新代码应使用 `add_documents`（但 `index_builder.py` 仍调用旧方法，待统一）
- `semantic_chunker` 的依赖检测仅能做有向无环图验证，未实际用于检索排序
- embedding 模型固定为 `qwen3-embed-0.6b`，未实现模型热切换
- 未实现 Graph-RAG（call graph / inheritance graph）

---

## 📌 下一步计划（路线图）

1. **Phase 2**：统一 `VectorStore` 接口，废弃 `add_chunks`
2. **Phase 3**：在 `retriever.py` 中加入重排序（rerank）模块
3. **Phase 4**：实现执行反馈闭环 – 根据 LLM 生成的测试用例运行结果，反向优化检索权重

---

> 你现在已经拥有一个 **双知识库、支持增量更新的 RAG 系统**，能够为 LLM 提供精准的代码上下文，而不仅仅是依赖 prompt 中的模糊描述。