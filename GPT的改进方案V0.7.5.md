我认为你这次架构调整方向是正确的，而且比之前的 `get_cases_generator()` 更容易扩展到 C++/Java。

核心思想其实已经从：

```text
AI <- solution_runner <- Python AST
```

变成：

```text
AI <- SolutionStruct <- solution_runner(Python/C++/Java)
```

这样 AI-Agent 完全不需要知道语言细节。

---

# 一、建议的最终架构

建议未来目录：

```text
AI-Agent/
│
├─ case_generator.py
├─ conversion_generator.py
├─ complexity_analyzer.py
├─ reference_retriever.py
├─ testcase_executor.py
│
└─ prompts/
    ├─ case_prompt.txt
    ├─ conversion_prompt.txt
    └─ complexity_prompt.txt
```

职责：

```text
SolutionRunner
    ↓
SolutionStruct
    ↓
AI-Agent
    ├─ complexity_analyzer
    ├─ reference_retriever
    ├─ case_generator
    ├─ conversion_generator
    └─ testcase_executor
```

---

# 二、建议新增 ContextStruct

仅靠 SolutionStruct 不够。

因为 CaseGenerator 的输入来源其实有两个：

```text
题面
+
代码
```

而不是只有代码。

建议新增：

```python
@dataclass
class ProblemContext:
    title:str

    description:str

    examples:list[dict]

    constraints:str

    tags:list[str]

    solution_struct:SolutionStruct
```

AI-Agent统一吃这个对象。

---

# 三、Complexity Analyzer

先于 CaseGenerator 执行。

例如：

```python
class ComplexityAnalyzer:

    def analyze(
        self,
        problem:ProblemContext
    )->ComplexityHint:
```

返回：

```python
ComplexityHint(
    time_complexity="O(n^2)",
    space_complexity="O(n)",
    estimated_n_limit=1000,
    notes="双重循环"
)
```

---

## 第一版实现

甚至不用 AI。

直接 AST 静态分析。

例如：

```python
for
    for
```

推测：

```python
O(n²)
```

---

结果写回：

```python
problem.solution_struct.complexity_hint
```

---

# 四、Reference Retriever

负责RAG。

接口：

```python
class ReferenceRetriever:

    def retrieve(
        self,
        problem:ProblemContext,
        topk:int=5
    )->list[SolutionStruct]
```

返回：

```python
[
    reference_solution_1,
    reference_solution_2,
]
```

统一也是 SolutionStruct。

这样未来：

```text
Python
C++
Java
```

参考代码全部统一结构。

---

# 五、Case Generator

这是核心。

我建议不要：

```python
generate_cases(
    solution_struct
)
```

而是：

```python
generate_cases(
    problem:ProblemContext,
    references:list[SolutionStruct]
)
```

---

接口

```python
class CaseGenerator:

    def generate(
        self,
        problem:ProblemContext,
        references:list[SolutionStruct]
    )->list[_CASE]:
```

---

Prompt构造：

```python
prompt = f"""
# Problem

{problem.description}

# Constraints

{problem.constraints}

# Student Solution

{problem.solution_struct.to_json()}

# Complexity

{problem.solution_struct.complexity_hint}

# Reference Solutions

{json.dumps([
    x.to_dict()
    for x in references
],ensure_ascii=False)}

设计测试用例。
"""
```

---

# 六、规模控制逻辑

这是你最关心的部分。

不要让AI自由发挥。

应该先计算：

```python
max_n
```

---

例如：

```python
def infer_max_scale(
    complexity:ComplexityHint
)->int:
```

```python
if "O(1)" in tc:
    return 10**7

if "O(log" in tc:
    return 10**6

if "O(n)" in tc:
    return 10**5

if "O(n log n)" in tc:
    return 10**5

if "O(n²)" in tc:
    return 2000

if "O(n³)" in tc:
    return 200
```

---

然后 Prompt：

```text
学生代码复杂度：

O(n²)

请勿设计超过 n=2000 的样例
```

这样 AI 不会生成：

```python
n=100000
```

这种炸机器样例。

---

# 七、Conversion Generator

你的架构里这个模块会越来越重要。

---

接口：

```python
class ConversionGenerator:
```

```python
def need_conversion(
    self,
    solution:SolutionStruct
)->bool:
```

---

规则：

### 情况1

基础类型

```python
List[int]
str
int
```

直接 False

---

### 情况2

存在自定义类

```python
Node
TreeNode
ListNode
GraphNode
```

True

---

检测：

```python
BASE_TYPES = {
    "int",
    "float",
    "str",
    "bool",
    "list",
    "dict",
    "tuple"
}
```

```python
for method in solution.methods:
    for param in method.params:

        if param.origin_type not in BASE_TYPES:
            return True
```

---

---

生成 Prompt：

```python
prompt = f"""
根据下面结构

{solution.to_json()}

生成 conversion.py

要求实现：

main_caller_args
main_caller_kwargs

支持 TreeNode 构造
支持 ListNode 构造
"""
```

---

返回：

```python
conversion.py
```

---

# 八、自动执行模块

以后直接：

```python
class TestCaseExecutor:
```

```python
def execute(
    self,
    runner:SolutionRunner,
    cases:list[_CASE]
)->list[_RESULT]
```

内部：

```python
runner.run(
    cases,
    thread=-1,
    early_stop=0.3
)
```

---

# 九、Agent总控

最终会非常简单：

```python
class TestCaseAgent:

    def build_cases(
        self,
        problem:ProblemContext
    ):
```

流程：

```python
1 ComplexityAnalyzer

2 ReferenceRetriever

3 ConversionGenerator

4 CaseGenerator

5 人工确认

6 TestCaseExecutor
```

即：

```text
题目
 ↓
SolutionStruct
 ↓
复杂度分析
 ↓
RAG参考解
 ↓
conversion.py
 ↓
测试样例生成
 ↓
人工确认
 ↓
执行验证
```

这里最关键的一点是：**AI-Agent 永远不要再直接依赖 Python AST，而是只依赖 `SolutionStruct`。**

这样未来你新增：

```text
CppSolutionRunner
JavaSolutionRunner
RustSolutionRunner
```

只要都能导出：

```python
SolutionStruct
```

整个 AI-Agent 层一行代码都不用改，这才是真正的最小侵入式解耦。
