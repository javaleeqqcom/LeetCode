```markdown
# 🧠 Agents 模块文档
> 版本：0.7.5（基于当前实现）
> 2026-6-13

## 概览
`agents/` 目录实现了框架的 **Agent 层**，负责题目分析、测试用例生成、工作流编排等高层任务。  
该层与 Runtime 层（`tools/`）和 RAG 知识库（`rag/`）完全解耦，通过标准化的数据结构（`ProblemContext`、`ProblemAnalysis`、`SolutionStruct`）传递信息。

当前 Agent 主要包含：
- **题目分析**：提取算法类型、复杂度信息
- **测试用例生成**：基于题目和代码自动生成 `case_generator` 函数
- **LangGraph 工作流**：将分析、检索、生成串联为自动化流程
- **辅助工具**：剪贴板交互、日志管理、RAG 检索封装

---

## 一、架构图
```text
┌─────────────────────────────────────────────────────────────────┐
│                        Agent 层                                 │
│                                                                 │
│  analyze_agent.py      case_generator_agent.py                  │
│  ┌───────────────┐    ┌──────────────────────────┐              │
│  │ AnalyzeAgent  │    │  CaseGeneratorAgent      │              │
│  │ (LLM + 模板)  │    │  - build_rag_context()    │              │
│  └───────┬───────┘    │  - build_prompt()         │              │
│          │            │  - run()                  │              │
│          ▼            └───────────┬──────────────┘              │
│   ProblemAnalysis                 │                              │
│          │                        │                              │
│          └────────┬───────────────┘                              │
│                   ▼                                              │
│   build_graph.py  (LangGraph 工作流)                             │
│   analyze → retrieve → generate_case                            │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                        辅助模块                                  │
│   agent_io.py            reference_retriever.py                 │
│   complexity_analyzer.py   graph_state.py                       │
├─────────────────────────────────────────────────────────────────┤
│                        外部依赖                                  │
│   schemas/  tools/  rag/   (Runtime & 知识库)                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、模块说明

### 1. `agent_io.py` – 通用 I/O 工具
提供目录管理、代码清理、剪贴板交互等常用功能。

| 类 / 方法 | 描述 |
|-----------|------|
| `AgentIO.get_auto_dir(problem_dir)` | 返回 `problem_dir/auto` 目录，若不存在则自动创建。用于存放 Agent 生成的代码文件。 |
| `AgentIO.get_log_dir(problem_dir)` | 返回 `problem_dir/agent_logs` 目录，自动创建。用于存放 Prompt 日志和调试信息。 |
| `AgentIO.next_index(problem_dir, prefix)` | 扫描 `auto_dir` 中 `prefix*.py` 文件，返回下一个可用编号（从 0 开始）。默认 `prefix="case_generator_"`。 |
| `AgentIO.clean_llm_code(text)` | 清洗 LLM 原始输出：去除 `think` 标签、提取 markdown 代码块或从第一个 `def` 行截取，返回纯净代码。 |
| `AgentIO.copy_to_clipboard(text)` | 跨平台复制文本到系统剪贴板（Win: clip, macOS: pbcopy, Linux: xclip/xsel）。 |
| `AgentIO.send_messages_to_clipboard(messages, problem_dir)` | 将 LangChain 消息列表序列化为文本并复制到剪贴板；复制失败则保存到 `agent_logs/manual_prompt_{题目名}.log`。 |

**使用示例：**
```python
from agents.agent_io import AgentIO
idx = AgentIO.next_index(problem_dir)
code = AgentIO.clean_llm_code(response.content)
```

---

### 2. `analyze_agent.py` – 题目分析 Agent
使用 LLM 分析 `ProblemContext`，输出结构化的 `ProblemAnalysis`。

| 类 / 方法 | 描述 |
|-----------|------|
| `AnalyzeAgent(llm)` | 初始化分析 Agent，可选传入 LLM 实例，默认使用 `qwen3-coder-30b-q8`（温度 0）。加载 `prompts/analyze.prompt.md` 提示模板，构建 `PydanticOutputParser` 解析链。 |
| `AnalyzeAgent.run(problem)` | 调用 LLM，传入题目标题、描述、约束、标签、方法签名等信息，返回 `ProblemAnalysis` 对象。 |

**数据流：**
`ProblemContext` → `AnalyzeAgent` → `ProblemAnalysis`（含算法类型、知识需求等）

---

### 3. `case_generator_agent.py` – 测试用例生成 Agent
核心生成模块，根据题目和学生代码自动生成 `case_generator` 函数。

| 类 / 方法 | 描述 |
|-----------|------|
| `CaseGeneratorAgent(llm)` | 初始化，默认使用 `qwen3-coder-30b-q8`。内置 RAG 检索器 `ReferenceRetriever`，加载 `prompts/case_generator.prompt.md` 模板。 |
| `CaseGeneratorAgent.build_rag_context(knowledge_requirements)` | 调用 `ReferenceRetriever.retrieve` 获取参考 `SolutionStruct` 列表，拼接为 JSON 字符串；失败时返回空字符串。 |
| `CaseGeneratorAgent.build_prompt(problem)` | 构建完整的 LLM 消息列表。内容包含：题目描述、学生代码、`case_generator` 模板、复杂度分析摘要、RAG 检索上下文。 |
| `CaseGeneratorAgent.run(problem, dry_run)` | 执行生成流程。<br>**dry_run=True**：保存 Prompt 日志并尝试复制到剪贴板，不调用 LLM。<br>**dry_run=False**：调用 LLM → 清洗代码 → 保存到 `auto/case_generator_xxx.py`，返回代码字符串。 |

**生成文件命名规则：**
`auto/case_generator_000.py`、`auto/case_generator_001.py` ……

**依赖的模板字符串 `_DEFAULT_CASE_GENERATOR_TEMPLATE`** 内置于类中，为 `case_generator(scale)` 函数的空壳模板。

---

### 4. `complexity_analyzer.py` – 静态复杂度分析器
无需 LLM，通过静态代码扫描初步估算时间复杂度。

| 类 / 方法 | 描述 |
|-----------|------|
| `ComplexityAnalyzer` | 简单静态分析器。 |
| `analyze(struct)` | 接收 `SolutionStruct`，统计方法源码中 `for`/`while` 的嵌套深度。深度 0‑1 → `O(n)`/`O(1)`，2 → `O(n²)`，≥3 → `O(n³) or worse`，并给出 `estimated_n_limit`。返回 `ComplexityHint`。 |
| `_count_for_depth(code)` | 辅助函数，粗略计算循环嵌套最大深度（基于行首关键词，未实现精确缩进分析，仅供快速估算）。 |

> **注意**：当前实现为简化版本，未处理列表推导、递归、隐式循环等复杂情况。后续可扩展为 AST 级别分析或引入 LLM。

---

### 5. `reference_retriever.py` – RAG 检索封装
为 Agent 提供检索已存储的 `SolutionStruct` 的能力。

| 类 / 方法 | 描述 |
|-----------|------|
| `ReferenceRetriever(db_root)` | 初始化，默认使用 `"./rag_db"` 下的向量数据库。内部持有 `RAGRetriever` 实例。 |
| `retrieve(knowledge_requirements, topk)` | 输入关键词列表，拼接后查询 `conversion` 知识库。从返回结果的 `metadata.solution_struct_json` 字段反序列化为 `SolutionStruct` 列表。 |

**使用示例：**
```python
retriever = ReferenceRetriever()
refs = retriever.retrieve(["O(n^2)", "dp"])
```

---

### 6. `graph_state.py` – 工作流状态定义
定义 LangGraph 工作流中使用的共享状态结构。

| 类型 | 描述 |
|------|------|
| `AgentState(TypedDict)` | 包含字段：`problem`（`ProblemContext`）、`analysis`（`ProblemAnalysis`）、`retrieved_case_context`、`retrieved_conversion_context`、`generated_case_code`、`generated_cases`、`brute_force_results`、`evaluation`。所有字段均为 `Optional`。 |

此结构贯穿整个 Agent 工作流，各节点读写对应字段，实现数据传递。

---

### 7. `build_graph.py` – LangGraph 工作流
定义并编译题目分析 → 检索 → 用例生成的自动化流水线。

| 节点 / 组件 | 描述 |
|-------------|------|
| `analyze_node` | 调用 `AnalyzeAgent.run()`，将结果写入 `state["analysis"]`。 |
| `retrieve_node` | 将 `analysis.knowledge_requirements` 存入 `retrieved_case_context`（暂未执行实际检索，供后续扩展）。 |
| `generate_case_node` | 调用 `CaseGeneratorAgent.run()`，将生成的代码字符串写入 `generated_case_code`。 |
| `graph` | `StateGraph(AgentState)` 实例，包含上述三个节点，边顺序：`analyze` → `retrieve` → `generate_case`。入口 `analyze`，终点 `generate_case`。 |

**执行方式：**
```python
from agents.build_graph import graph
result = graph.invoke({"problem": problem_context})
```

---

## 三、快速入门
### 1. 使用 CaseGeneratorAgent 生成测试用例代码
```python
from agents.case_generator_agent import CaseGeneratorAgent
from schemas.problem_context import ProblemContext

agent = CaseGeneratorAgent()
# dry_run=True 仅生成 Prompt，不消耗 LLM 调用
code = agent.run(problem_context, dry_run=False)
# 生成的代码已自动保存到 problem_dir/auto/case_generator_xxx.py
```

### 2. 运行完整工作流
```python
from agents.build_graph import graph
from schemas.problem_context import ProblemContext

context = ProblemContext(...)   # 需要预先构建
result = graph.invoke({"problem": context})
print(result["generated_case_code"])
```

### 3. 复杂度快速评估
```python
from agents.complexity_analyzer import ComplexityAnalyzer
from tools.solution_struct import SolutionStruct

analyzer = ComplexityAnalyzer()
hint = analyzer.analyze(student_struct)
print(hint.time_complexity, hint.estimated_n_limit)
```

---

## 四、目录结构
```
agents/
├── agent_io.py                  # 通用 I/O 工具
├── analyze_agent.py             # 题目分析 Agent
├── case_generator_agent.py      # 测试用例生成 Agent
├── complexity_analyzer.py       # 静态复杂度分析器
├── reference_retriever.py       # RAG 检索封装
├── graph_state.py               # LangGraph 状态定义
└── build_graph.py               # LangGraph 工作流定义
```

---

## 五、注意事项
1. **LLM 依赖**：`AnalyzeAgent` 和 `CaseGeneratorAgent` 默认使用本地 Ollama 模型（`qwen3-coder-30b-q8`），请确保服务已启动。
2. **模板文件**：Agent 依赖 `prompts/` 目录下的 `.prompt.md` 文件，路径硬编码，移动时需同步调整。
3. **剪贴板功能**：跨平台剪贴板需要对应的系统工具（`clip`、`pbcopy`、`xclip`/`xsel`），缺失时自动降级为文件保存。
4. **复杂度分析**：`ComplexityAnalyzer` 为简易实现，仅作参考，不应作为精确的复杂度判断依据。
5. **RAG 检索**：`ReferenceRetriever` 依赖已构建好的 `conversion` 知识库，使用前请确保已执行 `rag/rag_knowledge_update.py`。
6. **工作流状态**：`build_graph.py` 中的 `retrieve_node` 目前仅透传数据，未执行实际 RAG 查询；实际检索逻辑已集成在 `CaseGeneratorAgent.build_rag_context()` 中。

---

## 六、与 Runtime 层的协作
Agent 层输出的代码（如 `case_generator_xxx.py`）最终由 Runtime 层的 `tools/solution_runner.py` 或 `tools/cases_generator.py` 执行。完整的暴力验证流程参见 `V0.7.5版调用程序.py` 示例（文档外提供）。

---

> 本文档基于 `agents/` 目录下现有源码（2026‑06‑13 提供的版本）生成。若后续新增 Agent 或修改接口，请同步更新。
>
## 七、改进方案
- 复杂度迭代：一开始由代码 for 循环嵌套层数的 regex 等方法解析复杂度上限。后续在实际执行代码中，统计不同 scale 下的执行时间，对 时间~scale 关系进行拟合，得到更精确的复杂度渐进函数，以供更进一步生成更合适的测试样例使用。