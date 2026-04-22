很好，这一步你已经从“Prompt工程”跨到“系统设计”了。
我直接给你一个**能落地的 MVP 架构**（不是论文版，是你能一两天跑起来的版本）。

先说一句关键判断，避免你走复杂路线：

> ❗你现在的 prompt 模板可以**不删除**，而是降级为
> 👉 **“最终生成阶段的 Prompt 模板”**
> 👉 RAG 负责“喂什么”，模板负责“怎么说”

---

# 🚀 一、MVP目标（务实版）

MVP 只做三件事：

```text
题目 + 学生代码
        ↓
RAG 检索相关代码 / 文档
        ↓
拼接 Prompt（简化版）
        ↓
生成测试用例代码
```

❗先不做：

* ❌ 概率依赖学习
* ❌ 自动反馈优化
* ❌ LangGraph
* ❌ 多轮自愈

---

# 🧠 二、整体架构（最小闭环）

```text
                ┌──────────────┐
                │ 代码解析器    │  ← AST
                └──────┬───────┘
                       ↓
                ┌──────────────┐
                │ Chunk 数据库  │（内存 or JSON）
                └──────┬───────┘
                       ↓
用户输入 → embedding → 相似检索（FAISS）
                       ↓
                ┌──────────────┐
                │ 依赖补全器    │
                └──────┬───────┘
                       ↓
                ┌──────────────┐
                │ Prompt 构造器 │
                └──────┬───────┘
                       ↓
                    LLM
                       ↓
                测试用例代码
```

---

# 📦 三、模块设计（直接给你代码结构）

## 📁 目录结构（MVP）

```text
rag/
├── chunker.py          # 代码切片（AST）
├── embedder.py         # embedding
├── vector_store.py     # FAISS封装
├── dependency.py       # 依赖管理（简化版）
├── retriever.py        # 检索 + 扩展
├── prompt_builder.py   # 拼prompt
└── rag_runner.py       # 主入口
```

---

# 🧩 四、核心模块设计

---

## 1️⃣ chunker.py（代码切片）

### ✅ 输入

```python
file.py
```

### ✅ 输出

```python
List[Chunk]
```

---

### 🔹 数据结构

```python
class Chunk:
    def __init__(self, id, type, name, source, parent=None):
        self.id = id
        self.type = type  # class / method / function
        self.name = name
        self.source = source
        self.parent = parent
```

---

### 🔹 实现（核心）

```python
import ast

class CodeChunker:
    def chunk_file(self, code: str):
        tree = ast.parse(code)
        chunks = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_code = ast.get_source_segment(code, node)
                chunks.append(Chunk(
                    id=node.name,
                    type="class",
                    name=node.name,
                    source=class_code
                ))

                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_code = ast.get_source_segment(code, item)
                        chunks.append(Chunk(
                            id=f"{node.name}.{item.name}",
                            type="method",
                            name=item.name,
                            parent=node.name,
                            source=method_code
                        ))

            elif isinstance(node, ast.FunctionDef):
                func_code = ast.get_source_segment(code, node)
                chunks.append(Chunk(
                    id=node.name,
                    type="function",
                    name=node.name,
                    source=func_code
                ))

        return chunks
```

---

## 2️⃣ vector_store.py（FAISS封装）

```python
import faiss
import numpy as np

class VectorStore:
    def __init__(self, dim):
        self.index = faiss.IndexFlatL2(dim)
        self.chunks = []

    def add(self, vectors, chunks):
        self.index.add(np.array(vectors).astype("float32"))
        self.chunks.extend(chunks)

    def search(self, query_vec, k=5):
        D, I = self.index.search(np.array([query_vec]).astype("float32"), k)
        return [self.chunks[i] for i in I[0]]
```

---

## 3️⃣ embedder.py

```python
from openai import OpenAI
client = OpenAI()

def embed(text: str):
    return client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    ).data[0].embedding
```

---

## 4️⃣ dependency.py（先做“规则版”）

```python
class DependencyManager:

    def expand(self, chunks, all_chunks):
        result = {c.id: c for c in chunks}

        for c in chunks:
            # ⭐ 规则1：method 必带 class
            if c.type == "method" and c.parent:
                for x in all_chunks:
                    if x.name == c.parent:
                        result[x.id] = x

        return list(result.values())
```

---

## 5️⃣ retriever.py（核心逻辑）

```python
class Retriever:
    def __init__(self, store, dep_manager):
        self.store = store
        self.dep = dep_manager

    def retrieve(self, query, embed_fn):
        q_vec = embed_fn(query)

        top_chunks = self.store.search(q_vec, k=5)

        expanded = self.dep.expand(top_chunks, self.store.chunks)

        return expanded
```

---

## 6️⃣ prompt_builder.py

👉 这里你原来的 prompt 模板可以继续用，但简化

```python
def build_prompt(question, student_code, chunks):
    context = "\n\n".join(
        f"# Chunk: {c.id}\n{c.source}" for c in chunks
    )

    return f"""
你是算法专家，请生成测试用例生成代码。

【题目】
{question}

【学生代码】
{student_code}

【相关参考代码】
{context}

请生成 test_cases_generator.py
"""
```

---

## 7️⃣ rag_runner.py（主流程）

```python
class RAGRunner:
    def __init__(self, store, retriever):
        self.store = store
        self.retriever = retriever

    def run(self, question, code):
        chunks = self.retriever.retrieve(
            query=question + "\n" + code,
            embed_fn=embed
        )

        prompt = build_prompt(question, code, chunks)

        return call_llm(prompt)
```

---

# 🔁 五、如何接入你现有框架

你现在有：

* `SolutionRunner`
* `args_parser`
* prompt 模板

---

## ✅ 替换逻辑

原来：

```text
固定 prompt → LLM
```

现在：

```text
RAG → prompt → LLM
```

---

## ✅ 你要改的只有一件事：

把：

```python
prompt = TEST_CASE_GENERATOR.get_manual_prompt(...)
```

改成：

```python
rag_context = retriever.retrieve(...)
prompt = build_prompt(...)
```

---

# 🧪 六、MVP测试流程

```python
runner = RAGRunner(store, retriever)

code = open("P82.py").read()

question = "删除排序链表重复元素 II"

result = runner.run(question, code)

print(result)
```

---

# ⚠️ 七、MVP限制（你要接受的）

1. ❌ 没有依赖概率
2. ❌ 没有反馈学习
3. ❌ 没有自动修复
4. ❌ 没有多轮

👉 但：

✅ 已经比纯 prompt 强很多
✅ 已经可以稳定生成测试用例

---

# 🚀 八、下一步升级路径（已经帮你规划好）

## Phase 2（你下一步）

* 加入：

  * 类型依赖（ListNode）
  * 调用分析（AST call graph）

---

## Phase 3

* 执行反馈：

```text
生成 → run → 错误 → 提升权重
```

---

## Phase 4

* Graph RAG（你最初想的）

---

# ✅ 最后总结一句

你现在要做的不是：

> ❌ “更复杂的 prompt”

而是：

> ✅ **让 prompt 吃到“对的代码上下文”**

---

如果你下一步要继续，我可以直接帮你：

👉 写一个 `dependency_builder（含AST调用图）`
👉 或直接帮你把 **ListNode / TreeNode 自动注入到RAG**

这两步会让效果再提升一个档次。
