你的 RAG 已经**建库成功**了，但 **Agent 完全没有在用 case_generator 知识库**。我把整个调用链顺了一遍，问题其实非常明确，而且不仅一个。

---

# 第一处：ReferenceRetriever 搜索错库了（这是最大的 Bug）

你现在的代码：

```python
class ReferenceRetriever:
    ...
    def retrieve(...):
        query = " ".join(knowledge_requirements)

        results = self.retriever.search(
            query,
            "conversion",      # ← 写死
            topk=topk
        )
```

它永远搜的是

```
conversion
```

但是你的 Prompt 想要的是

```
case_generator
```

所以：

```
rag_context=""
```

几乎就是必然。

---

应该至少改成

```python
results = self.retriever.search(
    query,
    "case_generator",
    topk=topk,
)
```

但是……

**仅改这一句仍然不够。**

---

# 第二处：retrieve() 的返回值设计已经过时

目前：

```python
retrieve(...)
    ↓
search()
    ↓
metadata
    ↓
solution_struct_json
```

你的代码：

```python
json_str = meta.get("solution_struct_json")
```

然而你新的 semantic_index_builder 根本没有存这个。

新的 metadata 大概只有

```
module_name
file_path
tags
type
...
```

而 document 才是真正内容。

所以：

```python
json_str = meta.get("solution_struct_json")
```

永远 None。

于是

```
refs=[]
```

所以

```
rag_context=""
```

---

因此：

ReferenceRetriever 已经完全不适合 Semantic RAG。

---

# 第三处：CaseGeneratorAgent 仍然按 AST RAG 写法设计

你现在：

```
CaseGeneratorAgent
      │
      ▼
ReferenceRetriever
      │
      ▼
SolutionStruct
      │
      ▼
to_json()
```

这是当初

```
conversion
```

知识库的设计。

因为 conversion 的目标是：

```
搜 SolutionStruct
```

但是

case_generator

不是。

它应该返回

```
prompt_text
```

或者

```
embedding_text
```

而不是

SolutionStruct。

所以这里应该拆。

---

# 我建议直接拆两个 Retriever

不要混。

例如

```
ReferenceRetriever
```

保留：

```
conversion
```

专门代码转换。

新增

```
CaseGeneratorRetriever
```

例如：

```python
class CaseGeneratorRetriever:

    def __init__(self):
        self.retriever = RAGRetriever()

    def retrieve(self, query, topk=5):

        return self.retriever.search(
            query=query,
            collection_name="case_generator",
            topk=topk,
        )
```

然后

```
CaseGeneratorAgent
```

直接：

```python
docs = self.case_retriever.retrieve(...)
```

不用再经过

```
SolutionStruct
```

---

# 第四处：Prompt 里根本没利用 metadata

你现在 Prompt：

```
其他模块代码参考：
{rag_context}
```

而

```
rag_context
```

现在实际上就是

```
SolutionStruct.to_json()
```

以后应该变成

例如：

```
# Example 1

文件:
leetcode_3660.py

模块:
nums_range_strategy

标签:
array unique_call

参考代码:

......
```

而不是

```
json
```

因为 LLM 写代码的时候：

**代码 > JSON**

---

例如：

```text
==========
Example 1

Module:
nums_range_strategy

Score:
0.92

Description:
数组元素差值不影响答案。

Reference:

# 又因为数组元素之间的差值...

SMALL_RATE=0.8

...
==========
```

效果会好很多。

---

# 第五处：你的 build_context() 已经写好了，却完全没用

你已经写了：

```python
retriever.build_context(...)
```

它输出就是：

```
Chunk1

File

Name

Content
```

但是现在

CaseGeneratorAgent

却没有调用。

反而自己：

```
retrieve()

↓

SolutionStruct

↓

to_json()
```

绕了一圈。

其实应该直接：

```python
rag_context = self.retriever.build_context(
    query=query,
    collection_name="case_generator",
    topk=5,
)
```

一句结束。

---

# 第六处：query 质量太差（后续建议）

目前：

```python
rag_query = complexity.time_complexity
```

例如：

```
O(n)
```

然后：

```
O(n) Estimated max n...
```

这几乎没有语义。

你的知识库里面真正有价值的是：

```
数组

重复元素

随机排列

图

树

DFS

拓扑

DP

坐标压缩
```

而不是：

```
O(n)
```

所以真正 query 应该来自：

```
ProblemContext
```

例如：

```
question

+

title

+

tags

+

constraints
```

甚至：

```
student_code
```

一起 embedding。

例如：

```python
query = "\n".join([
    self.problem.title,
    self.problem.description,
    " ".join(self.problem.tags),
    complexity.notes,
])
```

召回质量会比

```
O(n)
```

高得多。

---

# 我建议你下一版结构（V0.3）

我建议直接把 ReferenceRetriever 拆成两层：

```
CaseGeneratorAgent
        │
        │
        ├───────────────┐
        │               │
        ▼               ▼
ConversionRetriever   CaseGeneratorRetriever
        │               │
        ▼               ▼
conversion        case_generator
(AST)             (Semantic)
        │               │
        ▼               ▼
SolutionStruct     build_context()
        │               │
        └───────┬───────┘
                ▼
           Prompt Builder
```

这样两种知识库职责清晰：

* **conversion**：用于代码理解、API 转换、结构参考，继续返回 `SolutionStruct`。
* **case_generator**：用于测试策略、样例生成，直接返回 `build_context()` 生成的文本，不再经过 `SolutionStruct`。

---

**我还建议再进一步优化**：你已经实现了 `@RAG_DEP` 和 `@RAG_EXPORT`，下一步不要只返回检索到的单个模块，而是根据 `module_name` 自动调用 `SemanticChunker.rebuild_prompt_modules()`，把依赖模块（如 `nums_range_strategy` 自动带上 `scale2n`）一起拼成完整上下文。这会比当前纯向量召回的效果提升明显，也是你 DOC 中规划的 Graph-RAG 的第一步，而且实现成本并不高。
