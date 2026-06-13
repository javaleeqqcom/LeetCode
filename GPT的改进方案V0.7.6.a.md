我看完你的设计后，问题其实不在 `DRY_RUN`，而在 **CaseGeneratorAgent 根本没有把 RAG 检索结果真正喂给 LLM**。

从你给出的 Prompt 输出看：

```text
<system>
...
</system>

<request>
...
</request>

<student-code>
...
</student-code>

<template>
...
</template>

<attentions>
...
</attentions>
```

里面完全没有类似：

```text
<RAG_REFERENCE>
案例1:
...

案例2:
...
</RAG_REFERENCE>
```

说明：

```python
rag_context = self.build_rag_context([rag_query])
```

虽然执行了，

但：

```python
prompts/case_generator.prompt.md
```

模板里根本没引用 `{rag_context}`

或者引用了但位置不对。

---

# 第一阶段建议：不要让 Agent 直接生成

我反而建议 V0.7.6 先别做：

```python
Analyze -> Retrieve -> Generate
```

而做：

```python
Analyze
    ↓
Retrieve
    ↓
人工确认
    ↓
Generate
```

因为你现在最缺的是：

> 验证 RAG 是否真的检索到了正确样例

而不是生成代码。

否则：

```text
RAG失败
↓
LLM瞎编
↓
case_generator错误
↓
暴力跑半小时
↓
发现无效
```

浪费 token。

---

# 建议新增模式

```python
MODE = "inspect"
```

三种模式：

```python
MODE = "inspect"
MODE = "manual"
MODE = "auto"
```

---

## inspect

只看 RAG

```python
refs = retriever.retrieve(...)
```

输出：

```text
======== RAG TOP5 ========

[1]
相似度:0.91

文件:
xxx.py

原因:
区间修改
频率统计
双数组

代码:
...

-------------------
```

然后：

```python
input("继续生成? y/n")
```

---

## manual

生成 Prompt

复制到剪贴板

等待人工粘贴

这是你现在的 DRY_RUN。

---

## auto

真正调用模型。

---

# 第二阶段：RAG 不要只搜复杂度

目前：

```python
rag_query = complexity.time_complexity
```

这个效果极差。

例如：

```python
O(n log n)
```

会搜出来一堆：

```text
排序
ST表
线段树
FFT
```

毫无意义。

---

应该改成：

```python
rag_query_parts = []

rag_query_parts.extend(problem.tags)

rag_query_parts.append(problem.title)

rag_query_parts.append(
    complexity.time_complexity
)

rag_query_parts.extend(
    complexity.notes
)
```

例如：

```python
[
 "dp",
 "multiset",
 "bounded sum",
 "O(n²)"
]
```

拼成：

```python
dp multiset bounded sum O(n²)
```

效果会好很多。

---

# 第三阶段：CaseGeneratorAgent 应直接查询 case_generator 库

目前：

```python
ReferenceRetriever
    -> conversion
```

这是最大问题之一。

你在生成：

```python
case_generator.py
```

的时候，

却去搜：

```python
conversion
```

代码转换知识库。

结果拿到：

```python
FenwickTree
SegmentTree
DP
```

实现代码。

而不是：

```python
如何设计测试数据
如何设计退化结构
如何设计边界
```

这些经验。

---

应该改：

```python
search_case_knowledge()
```

对应：

```python
collection="case_generator"
```

你的语义库。

甚至优先搜：

```python
case_generator
```

然后再补：

```python
conversion
```

---

# 第四阶段：Prompt 中加入 RAG 样例摘要而不是原文

你现在准备直接塞：

```python
r.to_json()
```

很危险。

因为以后：

```python
topk=5
```

每个样例：

```python
3000 token
```

马上爆。

建议检索结果结构改成：

```python
{
    "problem_type":"区间修改+查询",
    "key_points":[
        "大量覆盖整个区间",
        "大量单点更新",
        "tot极大",
        "tot极小"
    ],
    "generator_snippet":"..."
}
```

Prompt：

```text
=== 检索到的优秀样例 ===

案例1：
题型：
区间修改+查询

覆盖点：
- 单点修改
- 全区间修改
- 重复值极多

关键生成代码：
...

=====================
```

而不是塞整个源文件。

---

# 第五阶段：DRY_RUN 最佳流程

我会改成：

```python
if DRY_RUN:

    # 1. Analyze
    analysis = AnalyzeAgent.run()

    # 2. Retrieve
    refs = retriever.retrieve()

    # 3. 保存 RAG
    rag_path = ...
    rag_path.write_text(...)

    # 4. Prompt
    prompt = build_prompt()

    # 5. 复制剪贴板

    # 6. 等待用户
    code = wait_clipboard_code()

    # 7. 自动 AST 校验
    ast.parse(code)

    # 8. 保存
```

这样：

```text
问题
 ↓
分析
 ↓
RAG
 ↓
人工看一眼
 ↓
LLM
 ↓
自动回收结果
 ↓
执行
```

整个链路基本不浪费 token。

---

如果是我继续迭代 V0.7.6，我会优先做下面三个改动：

1. **修复 Prompt 模板，确保 `{rag_context}` 真正输出。**
2. **把 ReferenceRetriever 默认库从 `conversion` 改为 `case_generator`。**
3. **增加 `inspect` 模式，先看 RAG TopK 再决定是否调用 LLM。**

这三个改完，RAG 的有效性会立刻显现出来，而不是现在这种“明明检索了但 Prompt 看起来像没检索”的状态。
