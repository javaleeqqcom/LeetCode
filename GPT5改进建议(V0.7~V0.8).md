你现在的架构最大的问题不是 RAG 没接进去，而是 **AI 与执行框架耦合方向反了**。

当前调用链实际上是：

```text
SolutionRunner
    └── get_cases_generator()
            └── TEST_CASE_GENERATOR.get_manual_prompt()
                    └── 拼Prompt
                            └── 人工复制给LLM
```

也就是说：

```text
测试执行器
    控制
Prompt生成器
```

而不是：

```text
Agent
    控制
RAG
    控制
Prompt
    控制
SolutionRunner
```

这是典型的「脚本时代架构」，不是 Agent 架构。

---

# 一、当前架构的问题

目前：

```text
SolutionRunner
├─ 代码解析
├─ 类型推断
├─ Prompt构造
├─ AI提问
├─ 测试执行
├─ 结果比较
└─ 日志
```

属于：

```text
God Object
```

（上帝类）

已经承担：

* 执行器
* Prompt工厂
* 类型分析器
* 代码解析器

四种职责。

而未来：

* RAG
* LangGraph
* AnalyzeAgent
* CaseGeneratorAgent
* ConversionAgent

都会接入。

此时：

```text
SolutionRunner
```

不应该知道：

```python
TEST_CASE_GENERATOR
```

的存在。

---

# 二、建议的新架构

改成：

```text
┌─────────────────────┐
│   LeetCodeAgent     │
└──────────┬──────────┘
           │
           ▼
    LangGraph Workflow
           │
 ┌─────────┼──────────┐
 ▼         ▼          ▼

Analyze  Retrieval  Convert

 ▼
CaseGenerator

 ▼
Execute

 ▼
Evaluate
```

---

# 三、重新划分目录

建议：

```text
agents/

    analyze_agent.py

    retrieval_agent.py

    case_generator_agent.py

    conversion_agent.py

    execute_agent.py

    evaluate_agent.py

    build_graph.py

rag/

    retriever.py

    rag_tool.py

    ...

runtime/

    solution_runner.py

    test_case_runner.py

    result_compare.py

prompts/

    analyze.prompt.md

    case_generator.prompt.md

    conversion.prompt.md

schemas/

    analysis_schema.py

    case_generator_schema.py

    conversion_schema.py

workflow/

    leetcode_workflow.py
```

---

# 四、SolutionRunner 应该缩减

未来：

```python
SolutionRunner
```

只负责：

```python
run()
save_test_cases()
read_test_cases()
```

仅此而已。

不要负责：

```python
Prompt
AI
RAG
Agent
```

---

# 五、重构 get_cases_generator()

删除：

```python
SolutionRunner.get_cases_generator()
```

因为：

```python
Prompt
```

属于 Agent。

不属于 Runtime。

---

改成：

```python
class CaseGeneratorAgent:
```

负责：

```python
build_prompt()
```

---

# 六、引入 RetrievalAgent

你已经有：

```python
RAGRetriever
```

但现在：

```python
CaseGeneratorAgent
```

直接调用：

```python
retriever.search()
```

未来会越来越乱。

建议：

```python
class RetrievalAgent:
```

统一封装：

```python
retrieve_case_knowledge()

retrieve_conversion_knowledge()

retrieve_debug_knowledge()
```

例如：

```python
class RetrievalAgent:

    def retrieve_case(self, query):
        ...

    def retrieve_conversion(self, query):
        ...
```

---

# 七、AnalyzeAgent 不应该直接输出 rag_queries

目前：

```python
ProblemAnalysis
```

里面：

```python
rag_queries
```

其实已经泄露实现细节。

应该改成：

```python
knowledge_requirements
```

例如：

```json
{
  "algorithm_type":"data structure",

  "knowledge_requirements":[
      "segment tree",
      "range update",
      "offline query"
  ]
}
```

然后：

```python
RetrievalAgent
```

负责：

```python
segment tree
    ↓

query1
query2
query3
```

这样：

Analyze 与 RAG 解耦。

---

# 八、Graph重构

你现在：

```python
analyze
```

一个节点结束。

应该变：

```text
analyze
    ↓
retrieve
    ↓
generate_case
    ↓
execute_bt
    ↓
evaluate
```

即：

```python
builder.add_node("analyze", ...)
builder.add_node("retrieve", ...)
builder.add_node("generate_case", ...)
builder.add_node("execute_bt", ...)
builder.add_node("evaluate", ...)
```

---

# 九、AgentState重构

现在：

```python
class AgentState
```

只有：

```python
analysis
retrieved_context
```

不够。

建议：

```python
class AgentState(TypedDict):

    question_text:str

    student_code:str

    file_suffix:str

    analysis:ProblemAnalysis

    retrieved_case_context:str

    retrieved_conversion_context:str

    generated_case_code:str

    generated_conversion_code:str

    generated_cases:list

    brute_force_results:list

    evaluation:dict
```

---

# 十、CaseGeneratorAgent 应改为结构化输出

目前：

```python
return self.chain.invoke(...)
```

返回：

```python
AIMessage
```

后续不好处理。

建议：

```python
CaseGeneratorSchema
```

例如：

```python
class CaseGeneratorOutput(BaseModel):

    reasoning:str

    case_generator_code:str
```

然后：

```python
PydanticOutputParser
```

解析。

这样：

```python
generated_case_code
```

可以直接落入：

```python
AgentState
```

---

# 十一、真正发挥 RAG 的方式

你现在的知识库：

```text
case_generator
conversion
```

其实非常适合做两级检索。

### Analyze

输出：

```json
{
    "algorithm":"segment tree",
    "difficulty":"hard",
    "data_type":"range query"
}
```

---

### Retrieval

查询：

```text
segment tree
range update
offline query
```

得到：

```text
历史优秀测试生成器
```

---

### CaseGenerator

Prompt：

```text
题目

学生代码

分析结果

RAG案例
```

生成：

```python
case_generator.py
```

---

# 十二、最终目标架构

我建议最终收敛为：

```text
LeetCodeWorkflow

    AnalyzeAgent
          ↓

    RetrievalAgent
          ↓

    CaseGeneratorAgent
          ↓

    ExecuteAgent
          ↓

    EvaluateAgent
```

其中：

```text
runtime/
```

完全不依赖：

```text
LangChain
LangGraph
RAG
Prompt
LLM
```

而：

```text
agents/
```

完全不依赖：

```text
SolutionRunner内部实现
```

两者只通过：

```python
generated_case_code
generated_cases
execution_result
```

交互。

这是比较标准的：

```text
Agent Layer
        ↓
Runtime Layer
```

分层结构，也能为后面你计划做的：

* Rerank
* GraphRAG
* 多Agent协作
* 自动修复 CaseGenerator
* 自动生成 Conversion

留出扩展空间。
