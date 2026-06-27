# 📘 LeetCode 本地自动化测试框架（Python）+ RAG 增强版

> 版本：0.2.2（2026‑06‑27 更新）

---

## 🧠 系统整体架构（当前实现）

本系统采用 **双知识库 RAG 架构**，后续将统一为单客户端多集合的模型：

- **Semantic 知识库**（`case_generator`）：基于人工标注的语义切片（`@RAG_BEGIN` / `@RAG_END`），用于测试用例生成、调试建议等高层逻辑。
- **AST 知识库**（`conversion`）：基于语法树（AST / 正则）自动抽取的代码切片（类、方法、函数），用于代码转换、结构理解。

```text
┌─────────────────────────────────────────────────────────────────┐
│                        代码源文件目录                            │
│   case_generator/                       conversion/             │
└───────────────┬───────────────────────────┬─────────────────────┘
                │                           │
                ▼                           ▼
       docs_inclusion.py             docs_inclusion.py
        （交互选择 + 哈希增量）         （交互选择 + 哈希增量）
                │                           │
                ▼                           ▼
        docs_inclusion_*.json        docs_inclusion_*.json
                │                           │
                ▼                           ▼
    semantic_index_builder.py         index_builder.py
      (SemanticChunker)                 (CodeChunker)
                │                           │
                ▼                           ▼
          VectorStore                     VectorStore
       (collection: case_generator)    (collection: conversion)
                │                           │
                └─────────────┬─────────────┘
                              ▼
                    rag_knowledge_update.py
                       （统一更新入口）
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        检索阶段                                  │
│   retriever.py  →  向量检索（search）                            │
│   rag_tool.py    →  LangChain tool 封装（依赖 build_context）    │
│   debug_retriever.py  →  交互式调试工具                          │
└─────────────────────────────────────────────────────────────────┘
```

> **V0.2.2 变更**：`SemanticChunker` 已支持**嵌套模块解析**（`@RAG_BEGIN`/`@RAG_END` 允许缩进与层级嵌套），所有正则均已适配前导空格，模块间自动记录父子关系，为后续 Graph‑RAG 提供结构化数据。

---

## 📦 模块说明（按文件）

### 1. `docs_inclusion.py` – 文件选择与变更检测

用于选择需要向量化的 Python 代码文件，基于 MD5 哈希实现增量更新。

| 函数 / 类 | 描述 |
|----------|------|
| `calc_file_hash(path)` | 计算文件 MD5 哈希值。 |
| `scan_files(root)` | 递归扫描目录下所有 `.py` / `.pyx` 文件，返回绝对路径列表。 |
| `parse_selection(choice, max_idx)` | 解析用户输入（如 `"0-3,5,7-9"`、`"a"`），返回选中索引列表。 |
| `cli_select(files)` | 交互式 CLI 让用户勾选需要构建索引的文件。 |
| `build_docs_inclusion(root_dir, out_dir, auto_select)` | 生成 `docs_inclusion_{timestamp}.json`，记录文件路径、hash、修改时间。 |
| `diff_docs(old_docs, new_docs)` | 对比新旧两份 JSON，返回新增或哈希变化的文件列表。 |

---

### 2. `chunker.py` – AST 代码切片（用于 conversion 知识库）

解析 `.py`（AST）或 `.pyx`（正则）文件，抽取类、方法、函数作为 `CodeChunk`。

| 类 / 函数 | 描述 |
|----------|------|
| `CodeChunk` | 代码切片数据结构：`id`, `type`, `name`, `source`, `start_line`, `end_line`, `parent`, `file_path`, `kind` 等。 |
| `CodeChunker(file_path)` | 切片器，根据扩展名自动选择解析器。 |
| `CodeChunker._chunk_py()` | 使用 `ast` 模块解析类、方法、函数，识别装饰器（`@property`、`@setter` 等）。 |
| `CodeChunker._chunk_pyx()` | 使用正则表达式解析 Cython 文件，支持 `cdef class`、`cdef`/`cpdef`/`def`，识别装饰器。 |
| `CodeChunker.chunk()` | 主入口，返回 `List[CodeChunk]`。 |
| `save_chunks_readable(chunks, out_file)` | 保存为可读文本（调试用）。 |
| `save_chunks_json(chunks, out_file)` | 保存为 JSON，包含层次关系（`sub_chunks`）。 |
| `build_hierarchy(chunks)` | 构建父子关系（类包含方法）。 |

---

### 3. `semantic_chunker.py` – 语义代码切片（用于 case_generator 知识库）

解析包含特殊标记的 `.py` 文件，生成 `RAGModule` 列表。  
**V0.2.2 重要更新**：解析器改用**模块栈**，完整支持嵌套的 `@RAG_BEGIN` / `@RAG_END`；所有正则允许前导空格，识别函数体内的缩进标记；自动为模块建立 `parent` 关系，为 Graph‑RAG 提供直接结构。

**支持的标记：**
- `# @EXAMPLE_BEGIN: name`  标记示例开始
- `# @EXAMPLE_TAG: tag1,tag2`  打标签
- `# @RAG_BEGIN: module_name`  语义模块开始
- `# @RAG_END`  模块结束
- `# @RAG_EXPORT: yes/no`  是否导出
- `# @RAG_DEP: dep1,dep2`  依赖的其他模块
- `# @RAG_MODULE_SETTING: key=value`  模块级设置

| 类 / 函数 | 描述 |
|----------|------|
| `RAGModule` | 语义模块：`name`, `source`, `deps`, `export`, `settings`, `embedding_text`（去除标记后的纯代码）, `prompt_text`（含设置块）, `parent`（V0.2.2 新增）。 |
| `ExampleFile` | 代表一个标注文件，包含 `example_name`, `tags`, `rag_modules` 字典。 |
| `SemanticChunker(file_path)` | 解析器。 |
| `SemanticChunker.parse()` | 主入口，使用模块栈解析嵌套结构，返回 `ExampleFile`。自动检测循环依赖（DAG 验证）。 |
| `SemanticChunker._build_module()` | 从源代码块构建 `RAGModule`，提取元数据（含 `parent`）。 |
| `SemanticChunker._check_dependencies()` | 检测模块依赖是否存在循环或缺失。 |
| `SemanticChunker.rebuild_prompt_modules(example, module_names)` | 根据模块名列表（自动包含依赖）拼接 prompt 文本。 |

---

### 4. `embedding.py` – 向量存储与嵌入封装

基于 ChromaDB 持久化 + Ollama 嵌入模型。

| 类 / 函数 | 描述 |
|----------|------|
| `VectorStore(db_path, collection_name)` | ChromaDB 客户端封装。 |
| `VectorStore.add_chunks(chunks)` | **（旧版）** 将 `CodeChunk` 列表入库（已标记 `Warning`，保留兼容性）。 |
| `VectorStore.add_documents(docs)` | 新版入库方法，接收 `[{id, document, metadata}]` 列表。 |
| `OllamaEmbeddingFunction(model)` | 实现 ChromaDB 的 `EmbeddingFunction` 接口，通过 Ollama HTTP API 调用嵌入模型（默认 `qwen3-embed-0.6b:q8`）。 |

---

### 5. `index_builder.py` – AST 索引构建器

将 `docs_inclusion_*.json` 中列出的文件进行 AST 切片，存入向量库。

| 函数 | 描述 |
|------|------|
| `load_docs(path)` | 加载 JSON 文件。 |
| `build_index(docs_file, collection_name, prev_docs_file)` | 主流程：<br>1. 加载文档列表，若提供 `prev_docs_file` 则执行增量 diff。<br>2. 对每个文件实例化 `CodeChunker` → 生成 `CodeChunk` 列表。<br>3. 保存调试文件到 `./rag_chunk/`（`.txt` 和 `.json`）。<br>4. 调用 `VectorStore.add_chunks()` 入库（使用旧版接口）。 |

---

### 6. `semantic_index_builder.py` – 语义索引构建器

将语义标记文件转换为 `RAGModule`，并存入向量库（使用 `add_documents`）。

| 函数 | 描述 |
|------|------|
| `load_docs(path)` | 加载 JSON 文件。 |
| `build_semantic_index(docs_file, collection_name, prev_docs_file)` | 主流程：<br>1. 加载文档列表，增量 diff。<br>2. 对每个文件实例化 `SemanticChunker` → `parse()` 获得 `ExampleFile`。<br>3. 为每个非空 `embedding_text` 的模块构造 `{id, document, metadata}`，额外保留 `prompt_text` 和 `source`（未入库，仅调试）。<br>4. 保存调试文件 `*.semantic.json`。<br>5. 调用 `VectorStore.add_documents()` 入库。 |

---

### 7. `retriever.py` – 检索器（供 LLM 调用）

| 类 / 函数 | 描述 |
|----------|------|
| `RAGRetriever(db_root)` | 初始化，`db_root` 默认 `"./rag_db"`。 |
| `RAGRetriever.get_collection(collection_name)` | 懒加载 ChromaDB collection，复用客户端。 |
| `RAGRetriever.search(query, collection_name, topk, where)` | 执行向量检索，返回 `[{score, document, metadata}]`。内部调用 ChromaDB 的 `query`，并将距离转换为相似度（`1.0 - dist`）。 |
| `RAGRetriever.build_context(query, collection_name, topk)` | 调用 `search()` 后格式化输出为文本块，包含相似度、文件路径、类型、名称和内容，便于直接拼接到 Prompt 中。 |

---

### 8. `rag_tool.py` – LangChain 工具封装

为两个知识库提供 LangChain `@tool` 装饰器函数，供 Agent 调用。

| 工具函数 | 描述 |
|----------|------|
| `search_case_knowledge(query)` | 搜索 `case_generator` 语义知识库。 |
| `search_conversion_code(query)` | 搜索 `conversion` AST 知识库。 |

> ✅ 这两个工具均调用 `retriever.build_context()`，该方法已在 `retriever.py` 中实现，可直接使用。

---

### 9. `rag_knowledge_update.py` – 统一知识库更新入口

一键更新两个知识库（semantic + AST），自动处理时间戳和增量构建。

| 函数 | 描述 |
|------|------|
| `latest_docs_file(prefix)` | 从 `./rag_docs/` 中查找最新的 `{prefix}_*.json` 文件。 |
| `build_case_generator()` | 更新 semantic 库：<br>1. 调用 `build_docs_inclusion(CASE_GENERATOR_ROOT, auto_select=True)`。<br>2. 重命名为 `case_generator_{timestamp}.json`。<br>3. 调用 `build_semantic_index()`（自动增量）。 |
| `build_conversion()` | 更新 AST 库：流程同上，调用 `build_index()`。 |
| `main` | 依次执行上述两个构建函数。 |

**配置常量：**
- `CASE_GENERATOR_ROOT = "rag_knowledge/case_generator"`
- `CONVERSION_ROOT = "rag_knowledge/conversion"`
- `DOCS_DIR = "./rag_docs"`

---

### 10. `debug_retriever.py` – 检索调试工具

交互式命令行工具，用于测试检索效果。

| 函数 | 描述 |
|------|------|
| `format_metadata(meta)` | 将 metadata 格式化为易读文本（兼容 semantic 和 AST 两种知识库）。 |
| `pretty_print_results(results, topk)` | 格式化打印检索结果，包含相似度、元数据、内容预览。 |
| `main()` | 解析命令行参数，进入 REPL 循环，支持输入查询并显示 Top‑K 结果。 |

**用法示例：**
```bash
python rag/debug_retriever.py case_generator
python rag/debug_retriever.py conversion --topk 3
```

---

## 🚀 快速使用

### 1. 构建 / 更新知识库

```bash
# 一键更新两个知识库（自动扫描配置目录，无需交互）
python rag/rag_knowledge_update.py

# 单独更新 AST 知识库（交互式选择文件）
python rag/index_builder.py ./rag_docs/conversion_xxx.json

# 单独更新 Semantic 知识库
python rag/semantic_index_builder.py ./rag_docs/case_generator_xxx.json
```

### 2. 检索测试（使用 debug 工具）

```bash
python rag/debug_retriever.py case_generator
```

然后在提示符下输入查询语句，例如：
```
🔍 Query > 如何生成边界测试用例？
```

### 3. 在代码中使用检索器

```python
from rag.retriever import RAGRetriever

retriever = RAGRetriever(db_root="./rag_db")
results = retriever.search(
    query="链表反转函数",
    collection_name="conversion",
    topk=3
)

for r in results:
    print(f"Score: {r['score']:.4f}")
    print(r["metadata"])
    print(r["document"][:200])
    print("---")
```

### 4. 与 `SolutionRunner` 集成（示例）

```python
retriever = RAGRetriever()
chunks = retriever.search(question + code, "case_generator", topk=4)
context = "\n\n".join([c["document"] for c in chunks])
prompt = f"{question}\n\n学生代码：\n{code}\n\n相关代码上下文：\n{context}"
```

---

## 📁 目录结构（RAG 模块）

```
项目根目录/
├── rag/                         # RAG 模块源码目录
│   ├── docs_inclusion.py
│   ├── chunker.py
│   ├── semantic_chunker.py      # V0.2.2 支持嵌套模块
│   ├── embedding.py
│   ├── index_builder.py
│   ├── semantic_index_builder.py
│   ├── retriever.py
│   ├── rag_tool.py
│   ├── rag_knowledge_update.py
│   └── debug_retriever.py
├── rag_db/                      # ChromaDB 持久化数据（当前双目录，规划中统一）
│   ├── case_generator/
│   └── conversion/
├── rag_docs/                    # docs_inclusion_*.json
└── rag_chunk/                   # 调试用 JSON/TXT 切片导出
```

**未来目标结构**（Phase 5）：
```
项目根目录/
├── rag_db/                      # 单一 PersistentClient，多 Collection
│   └── chroma.sqlite3           # 内含 case_generator 与 conversion 集合
```

---

## ⚠️ 已知问题与不一致

1. **新旧接口混用**  
   `index_builder.py` 仍调用 `VectorStore.add_chunks()`（旧版），而 `semantic_index_builder.py` 使用 `add_documents()`（新版）。建议统一为 `add_documents`，并迁移 AST 知识库至统一的 Document 格式。

2. **嵌入模型固定**  
   `embedding.py` 中的 `EMBED_MODEL = "qwen3-embed-0.6b:q8"` 为硬编码，未实现运行时切换。

3. **图结构未充分利用**  
   虽在 `CodeChunk` 和 `RAGModule` 中设计了 `parent`/`deps` 字段，但检索时未利用这些关系进行 Graph‑RAG 排序或遍历。`SemanticChunker` 已正确填充父子关系，待下游利用。

4. **ChromaDB 存储分目录**  
   当前为每个知识库使用独立的 `PersistentClient` 路径（`rag_db/case_generator/`、`rag_db/conversion/`），造成资源重复（多个 SQLite/WAL），不利于跨集合检索和统一管理。

---

## 🔮 下一步计划（路线图）

- ✅ **Phase 1**：实现 `retriever.build_context()`（已完成）。  
- **Phase 2**：统一 `VectorStore` 接口，废弃 `add_chunks`，全面迁移至 `add_documents`。  
- **Phase 3**：在 `retriever.py` 中加入重排序（rerank）模块。  
- **Phase 4**：实现基于 `parent` 和 `deps` 的 Graph‑RAG 检索增强。  
- **Phase 5（新增）**：**统一 ChromaDB 存储为单 PersistentClient + 多 Collection**，废弃 `rag_db/case_generator/`、`rag_db/conversion/` 分目录方式，改为 `rag_db/chroma.sqlite3` 内维护 `case_generator` 与 `conversion` 两个 Collection。同步调整 `VectorStore`、`RAGRetriever`、`rag_knowledge_update` 等组件，支持跨知识库查询与统一的 Document 元数据模型。

---

> 本文档基于 `rag/` 目录下所有 `.py` 文件（截至 2026‑06‑27）更新。若代码有后续修改，请以源码为准。