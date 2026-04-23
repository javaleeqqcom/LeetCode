# 📘 LeetCode 本地自动化测试框架（Python）+ RAG 增强版

* 版本：0.1.0（RAG Integration MVP）

---

# 🌟 核心升级：RAG 驱动测试用例生成（新增）

本版本在原有「自动化测试框架」基础上，引入 **RAG（Retrieval-Augmented Generation）代码理解层**，用于：

> 🔥 让 LLM 生成测试用例 / debug 时“看到相关代码上下文”，而不是仅依赖 prompt

---

# 🧠 一、系统整体架构（升级版）

```text
                ┌──────────────┐
                │ 代码解析器    │  AST / Cython
                └──────┬───────┘
                       ↓
                ┌──────────────┐
                │ Chunk 构建器  │  CodeChunk
                └──────┬───────┘
                       ↓
                ┌──────────────┐
                │ 向量数据库    │  ChromaDB / FAISS
                └──────┬───────┘
                       ↓
用户输入 → embedding → 相似检索（Retriever）
                       ↓
                ┌──────────────┐
                │ 依赖扩展器    │  method → class 补全
                └──────┬───────┘
                       ↓
                ┌──────────────┐
                │ Prompt 构造器 │  （你原有模板保留）
                └──────┬───────┘
                       ↓
                      LLM
                       ↓
                测试用例 / Debug 输出
```

---

# 📦 二、新增 RAG 模块说明

## 📁 rag/ 目录结构（新增）

```text
rag/
├── chunker.py          # AST / Cython 代码切片
├── embedding.py        # Chroma + Ollama embedding
├── vector_store.py     # 向量存储封装
├── retriever.py        # 检索核心逻辑
├── dependency.py       # 依赖扩展（method→class）
├── index_builder.py    # 索引构建入口
├── docs_inclusion.py   # 文件选择 + 增量更新
├── prompt_builder.py   # Prompt拼接
└── rag_runner.py       # RAG 主入口
```

---

# 🧩 三、RAG核心设计

## 1️⃣ Chunking（代码结构化）

### CodeChunk

* class / method / function 统一建模
* 保留：

  * source
  * line range
  * parent-child关系

👉 支持：

* Python AST
* Cython regex fallback

---

## 2️⃣ Embedding（语义表示）

* 模型：`qwen3-embed-0.6b`
* backend：Ollama HTTP API
* 存储：ChromaDB persistent

---

## 3️⃣ Retriever（语义检索）

```text
query → embedding → FAISS/Chroma top-k → dependency expand
```

### 关键增强：Dependency Expansion

```text
method → 自动补 class
```

---

## 4️⃣ Prompt Builder（你现有系统保留）

RAG只负责“喂上下文”，不改你 prompt 风格：

```text
【题目】
【学生代码】
【相关代码上下文（RAG）】
```

---

## 5️⃣ RAG Runner（新增入口）

```python
chunks = retriever.retrieve(question + code)
prompt = build_prompt(question, code, chunks)
llm(prompt)
```

---

# 🔬 四、实际效果（你现在已经验证）

### 查询示例

```text
我需要查找链表打印的算法代码
```

### 返回结果：

✔ ListNode2List
✔ ListNode class
✔ _to_string safe print
✔ __repr debug方法

👉 已实现：

* method级检索
* class级补全
* 多定义去重

---

# 🚀 五、系统升级价值（关键变化）

## Before（纯Prompt）

```text
LLM ← prompt（无上下文）
```

## After（RAG）

```text
LLM ← prompt + 相关代码上下文
```

---

# 📊 六、当前系统能力对比

| 能力      | 原系统 | RAG系统   |
| ------- | --- | ------- |
| 代码理解    | ❌   | ✅       |
| 方法关联    | ❌   | ✅       |
| 类上下文    | ❌   | ✅       |
| debug定位 | ❌   | ✅       |
| 测试用例生成  | ⚠️  | ✅（稳定提升） |

---

# 🔧 七、与原 SolutionRunner 集成方式

### 修改点（最小侵入）

```python
prompt = build_prompt(...)
```

改为：

```python
chunks = retriever.retrieve(query)
prompt = build_prompt(question, code, chunks)
```

---

# 🧪 八、RAG Debug工具

```bash
python rag/debug_retriever.py
```

功能：

* CLI 查询代码语义
* top-k chunk 展示
* score排序

---

# 🔮 九、下一步计划（关键路线）

## Phase 2：结构增强（强烈建议优先）

### 1. AST Dependency Graph

* function call graph
* class inheritance graph

---

### 2. SafeIterBase Cython化

* node wrapper → C层结构
* hash(id(node))统一

---

### 3. Graph-RAG（终极目标）

```text
code → graph → retrieval → reasoning
```

---

## Phase 3：执行反馈闭环

```text
LLM生成 → run → error → re-rank chunks
```

---

## Phase 4：自动测试用例优化

* mutation testing
* coverage driven RAG

---

# ⚠️ 当前已知限制

* embedding仍为单向语义
* dependency规则为启发式
* graph未完全构建

---

# 🧠 一句话总结当前系统

> 你现在已经从“写prompt的人”
> 进化到“控制代码上下文流动的人”

---

# 🚀 总结

当前系统已经完成：

* ✔ AST code slicing
* ✔ vector retrieval
* ✔ dependency expansion
* ✔ prompt injection

👉 下一跃迁点是：

> **Graph RAG（结构理解） + execution feedback（闭环学习）**
