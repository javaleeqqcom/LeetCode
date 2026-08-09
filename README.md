# LeetCode 本地自动化测试框架
- 版本：0.8.0

## 总览

本项目提供一套完整的本地化 LeetCode 题目测试解决方案，核心目标如下：

- **零侵入执行**：直接运行学生编写的 LeetCode 风格代码（含 `Solution` 类及 `ListNode`/`TreeNode` 等自定义类型），无需修改任何源代码。
- **全自动环境模拟**：自动处理编码检测（UTF‑8/GBK/BOM）、类型注入、虚拟模块隔离，使本地执行行为与 LeetCode 在线判题环境完全一致。
- **高效批量验证**：支持受控的多工作进程执行、早停策略和智能文件管理；执行器会保留单进程模式，避免小任务被进程启动开销拖慢。
- **结构化调试辅助**：为链表和二叉树提供安全迭代器、环检测、美观打印等工具，方便快速定位算法逻辑错误。
- **AI 增强工作流**：采用 Agent + Runtime 分层架构，通过统一的 `SolutionStruct` 导出代码结构，AI Agent 可基于此自动生成测试用例与暴力验证代码，实现执行逻辑与生成逻辑的完全解耦，并已初步集成 RAG 检索能力。

---

## 一、多进程测试工具（核心引擎）

`tools/solution_runner.py` 是框架的核心模块，提供以下功能：

### 1. 测试用例加载与解析
- **双重格式支持**：自动识别 `.json` 或 `.txt` 文件。
  - 字典格式（含“输入”关键词）：直接解析 `input` / `output` / `expected`。
  - 元组格式（纯参数行）：需指定 `params_num`，按固定行数分组。
- **智能类型转换**：`null` → `None`，`true`/`false` → `True`/`False`，并使用 `ast.literal_eval` 安全解析嵌套结构。
- **签名绑定验证**：在读取阶段即利用函数签名（`inspect.Signature`）进行参数匹配，避免运行时 `missing self` 等错误。

### 2. 执行与日志
```python
from tools.solution_runner import SolutionRunner

runner = SolutionRunner("P82_V0.py")                # 自动识别主方法
cases = runner.read_test_case("P82q1.txt")          # 读取测试用例
results = runner.run(cases, log_folder="logs")      # 执行并将错误日志写入 logs/
```
- **多进程支持**：兼容保留的 `thread` 参数用于设置工作进程数（默认为 1，`-1` 表示按逻辑处理器数自动选择）。执行器没有固定的工作进程上限，但不会创建多于测试用例数的空闲进程；超过逻辑处理器数时会给出过度调度警告。Windows 下使用 `spawn` 隔离子进程，以支持超时后终止失控任务。
- **适用范围**：多进程主要适合单例计算量较大的 CPU 密集任务；小任务或输入体积远大于计算量的任务通常使用 `thread=1` 更快。实测结果见 [`benchmark_results/parallel_scaling.md`](benchmark_results/parallel_scaling.md)。
- **结果顺序一致性保证**：并发完成后按原始输入顺序恢复结果；每个测试用例的 `cid` 只需唯一，可以是整数或字符串，无需预先排序。
- **早停机制**：支持按错误比例（`early_stop<1`）或错误数量（`early_stop>=1`）提前终止执行，节省无效计算资源。
- **日志文件**：每个测试用例生成独立日志文件，包含输入、输出、耗时、异常堆栈及 `print` 重定向内容。文件名自动去除非法字符并避免冲突，存放于学生代码文件所在目录。

### 3. 暴力算法验证流程
框架支持使用暴力算法自动生成标准答案，并用于验证优化算法：
```python
# brute.py – 暴力解法
class Solution:
    def yourMethod(self, ...): ...

# run_brute.py
brute = SolutionRunner("brute.py")
brute.save_cases(cases_generation, max_size=10, num_cases=20)  # 生成JSON用例+expected

# run_optimized.py
optimized = SolutionRunner("optimized.py")
cases = optimized.read_test_case("brute.json")
results = optimized.run(cases)
```
`save_cases` 会自动调用用户提供的 `cases_generation` 函数生成输入参数，然后执行暴力解法得到 `expected` 结果，最终保存为统一的 JSON 格式测试集。

---

## 二、长驻执行后端（大规模测试）

新代码位于 `runtime/runner/`，与旧 `tools/solution_runner.py` 分开，便于保持兼容并进行 A/B 性能验证。

```python
from runtime.runner import CaseStoreWriter, PersistentPythonRunner

CaseStoreWriter.write("cases.ojbin", generated_cases)  # generated_cases 可以是生成器
with PersistentPythonRunner(
    "solution.py",
    main_method="solve",
    workers=8,
    standard_mode=True,
) as runner:
    report = runner.run_store("cases.ojbin", collect_results=False)
    print(report.metrics.throughput_cases_per_second)
```

- 每个 Python Worker 只加载一次学生源码和依赖，然后循环执行多个样例。
- `.ojbin` 使用版本化偏移表和只读内存映射，可以流式生成、随机读取 10 万或 100 万样例；Worker 不再解析整套输入。
- 默认动态分成约 `4 × workers` 个批次，在 Queue 通信与尾部负载均衡之间折中。
- 正确结果可只在 Worker 内比较并回传摘要；错误、完整结果和 stdout 可按需收集。
- 正式调试配置最多使用 16 个 Worker，避免 Windows 桌面进程与 24 个逻辑处理器过度争抢。
- `standard_mode=True` 仅允许基础 JSON 输入输出和常用算法库，启动更轻并兼容 PyPy；它是格式约束，不是安全沙箱。

`native_runner/` 提供独立的 Windows C++ 管理器。当前已使用 Job Object 限制进程数、单进程提交内存、批次超时，并保证管理器退出时终止全部 Worker。文件系统 ACL、受限令牌/AppContainer 和网络隔离仍属于后续安全阶段，当前版本不会错误地宣称已经完成完整沙箱。

后端对照脚本：

```powershell
python -m tests.benchmark_runner_backends --repeats 3
```

架构、限制与采纳结论见 [`plan_documents/NATIVE_RUNNER_DESIGN.md`](plan_documents/NATIVE_RUNNER_DESIGN.md)，最终性能数据见 [`benchmark_results/FINAL_RUNNER_REPORT.md`](benchmark_results/FINAL_RUNNER_REPORT.md)。

`PersistentPythonRunner` 的 Worker 默认是长驻的 CPython 解释器进程；“长驻”表示复用解释器和已加载模块，并不表示学生代码已经编译为 C。框架热点的可选 Cython 机器码化方案见 [`plan_documents/CYTHON_HOTPATH_PLAN.md`](plan_documents/CYTHON_HOTPATH_PLAN.md)。

---

## 三、特殊类型调试工具

### 1. 基础工具 (`args_parser_tools.py`)
- `input_parser_registry`：类型转换注册表，例如将 `List[int]` 自动转换为 `ListNode`。
- `KitBase`：泛型代理基类，统一处理包装类与原生节点的互转（`unwrap`），避免重复包装。
- `SafeIterBase`：安全迭代器基类，提供统一的环检测能力。使用**节点 identity（`id`）** 判断重复，不会误判值相同而地址不同的节点。

### 2. 链表调试 (`list_node_kit.py`)
`ListNodeKit` 包装原生 `ListNode`，提供：
- **安全扁平化**：`flatten(max_len=None)` 返回 `(nodes, stop_index)`。
  - `stop_index == -1`：无环，正常结束。
  - `stop_index >= 0`：检测到环，值为环起始索引。
  - `stop_index == max_len`：因长度限制提前终止。
- **环可视化打印**：`__repr__` 输出 `<class 'ListNodeKit'>: [1,2,>3,4,^]`，其中 `>` 标记环起点，`^` 标记环尾。
- **安全索引访问**：`kit[idx]` 支持环内循环访问（取余运算），越界时抛出 `IndexError`。

```python
head = List2ListNode([1,2,3,4,5])
ListNodeKit(head)[4].next = head   # 创建环
nodes, cycle_idx = ListNodeKit(head).flatten()
assert cycle_idx == 0
```

### 3. 二叉树调试 (`tree_node_kit.py`)
#### 统一迭代器 `TreeIter`
通过**操作字符串** + **栈/队列容器**，一个类实现四种遍历方式，代码量减少 70% 以上：

| 遍历方式 | 方法 | `operation` | `use_queue` | 原理 |
|----------|------|-------------|-------------|------|
| 层序遍历 | `layer_iter()` | `"ULR"` | `True` | `u` 输出当前节点，`l`/`r` 入队左右子 |
| 前序遍历 | `NLR_iter()` | `"RLU"` | `False` | 先压右子，再压左子，最后 `u` 输出 |
| 中序遍历 | `LNR_iter()` | `"RCL"` | `False` | 先压右子，再压当前节点（带标志），最后压左子 |
| 后序遍历 | `LRN_iter()` | `"CRL"` | `False` | 先压当前节点（带标志），再压右子，最后压左子 |

- `l`/`r`/`c`/`u` 分别对应：压左子、压右子、压当前节点（带标志）、立即输出。
- 环检测由 `SafeIterBase` 自动继承，遇到重复节点时停止或跳过。
- **美观打印**：`TreeNodeKit.__repr__` 生成树形结构图（依赖 `binarytree` 库），同时输出完全二叉树索引与节点值的映射，超长树自动截断，环检测时标记重复键。

```python
it = TreeIter(root, operation="RCL", use_queue=False)  # 中序遍历
for idx, node in it:
    print(idx, node.val)
```

---

## 四、AI Agent 工作流（解耦设计）

框架已实现 **Agent 层** 与 **Runtime 层** 的分离，通过标准化数据结构（`ProblemContext`、`SolutionStruct`）实现完全解耦。
- **Runtime 层**（`tools/`）：仅负责代码执行、结果比较、测试用例读写。
- **Agent 层**（`agents/`）：已实现 `AnalyzeAgent`（题目分析）、`CaseGeneratorAgent`（测试用例生成器生成），并接入 RAG 知识库，可自动检索相关测试策略，生成高质量的 `case_generator` 代码。支持 `dry_run` 模式，方便调试 Prompt 和人工介入。
- **统一结构**：`SolutionStruct` 将 Python / C++ / Java 等代码的方法签名、参数类型等信息导出为语言无关的数据结构，Agent 无需接触原始源码即可生成测试用例。

### 当前 RAG 能力
已建成 **双知识库 RAG 系统**，并统一为单 ChromaDB 客户端、多集合的管理模式：
- **语义知识库**（`case_generator`）：存储人工标注的测试策略代码模块，用于指导 Agent 生成符合题目特点的测试用例。
- **AST 知识库**（`conversion`）：存储自动抽取的代码片段（类、方法等），用于代码转换和结构理解。

向量检索通过 `RAGRetriever` 统一接口进行，支持多知识库查询和格式化文本上下文的构建，已无缝嵌入 `CaseGeneratorAgent` 的 Prompt 生成流程。

### Agent 工作流
```text
AnalyzeAgent  →  输出 problem_analysis (含算法类型、复杂度)
       ↓
CaseGeneratorAgent  →  结合 RAG 检索的 case_generator 参考代码，生成测试用例生成器
       ↓
ExecuteAgent (Runtime) →  调用 SolutionRunner 执行测试并收集结果
       ↓
EvaluateAgent (规划中) →  分析通过率、错误分布，反馈优化建议
```
目前 `AnalyzeAgent` 和 `CaseGeneratorAgent` 已可独立使用，也可通过 LangGraph 工作流（`build_graph.py`）串联执行。全部中间数据通过结构化 Schema 传递，RAG 与执行模块完全解耦。

### 暴力算法验证流程
原有的暴力算法验证仍可复用：通过 Agent 生成暴力解法代码，手动调用 `SolutionRunner` 执行并比较；未来计划将验证流程集成至 `CaseGeneratorAgent` 的自动编排中。

---

## 五、总结

| 模块 | 核心价值 |
|------|----------|
| **多进程测试工具** | 零侵入运行学生代码，自动处理编码/类型/环境，支持并发执行与早停。 |
| **特殊类型调试工具** | 为链表和二叉树提供安全迭代、环检测、美观打印，显著提升调试效率。 |
| **AI Agent 架构** | 通过 Agent 与 Runtime 分层、SolutionStruct 统一导出，并集成 RAG 知识库，自动生成测试用例与暴力算法。已实现测试生成与 RAG 协同，向 Graph‑RAG 演进。 |

本项目致力于让本地算法调试体验**无限接近 LeetCode 在线环境**，同时通过结构化的调试工具和 AI 辅助工作流，帮助学习者更快定位问题、验证算法正确性。后续将重点推进 **AST 调用图分析**、**Graph‑RAG 检索增强**与 **按文件粒度的稳健增量更新**。

## 🔮 下一步计划

- 记录错误用例编号，支持 DEBUG 模式下重跑并打印调试日志。
- 升级静态复杂度分析为基于执行时间的拟合估计，使测试规模更精准。
- 实现基于模块依赖的 Graph‑RAG 检索，自动拉取关联模块，提升生成质量。
- 统一 AST 知识库入库接口，实现按文件粒度的删除与替换，杜绝残留 chunk。

1. **小模型驱动的代码生成流程**  
   题目 → 小型 LLM 提取关键词 → RAG 检索相关代码 → 将题目与参考代码共同输入 LLM → 生成目标代码。

2. **代码自动验证与迭代优化**  
   生成代码 → 检验合规性与安全性（禁用高危库） → 自动执行测试 → 根据错误信息自动反馈并返回上一级循环 → 直至成功执行或超过重试次数。

3. **自定义类的性能优化**  
   - 不再通过对 Python 原生节点进行包装来实现迭代  
   - 改为定义 Cython 原生节点，并将其封装为用户无感的 Python 对象  
   - 迭代过程采用 Cython + C 层高效实现，大幅提升运行效率。
