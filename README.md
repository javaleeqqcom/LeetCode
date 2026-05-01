# LeetCode 本地自动化测试框架
- 版本：0.7.1

## 总览

本项目提供一套完整的本地化 LeetCode 题目测试解决方案，核心目标如下：

- **零侵入执行**：直接运行学生编写的 LeetCode 风格代码（含 `Solution` 类及 `ListNode`/`TreeNode` 等自定义类型），无需修改任何源代码。
- **全自动环境模拟**：自动处理编码检测（UTF‑8/GBK/BOM）、类型注入、虚拟模块隔离，使本地执行行为与 LeetCode 在线判题环境完全一致。
- **高效批量验证**：支持多线程并发执行、早停策略、智能文件管理，显著提升大规模测试用例的运行效率。
- **结构化调试辅助**：为链表和二叉树提供安全迭代器、环检测、美观打印等工具，方便快速定位算法逻辑错误。
- **AI 增强工作流**：集成 RAG（检索增强生成）提示词模板，可自动生成测试用例与暴力验证代码，逐步向代码结构理解（Graph‑RAG）演进。

---

## 一、多线程测试工具（核心引擎）

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
results = runner.run(cases, log_suffix="_V0")       # 执行并输出日志
```
- **多线程支持**：通过 `thread` 参数设置并发数（默认为1）。多线程模式下，测试用例被分批次提交给线程池，大幅缩短总耗时。
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

## 二、特殊类型调试工具

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

## 三、RAG AI Prompt（代码理解与生成）

框架已集成 **检索增强生成（RAG）** 模块，用于自动化测试用例生成与暴力算法编写。该模块的目标是从“语义检索”升级为“结构检索 + 语义补充”，最终演进至 **Graph‑RAG**。

### 当前 RAG 能力（`rag/` 目录）
- **文档分块（chunk）**：将代码/注释按函数、类等语义边界切分。
- **向量嵌入（embedding）**：使用嵌入模型将代码块转换为向量，支持相似度检索。
- **检索器（retriever）**：基于 FAISS 的向量检索，返回与查询最相关的代码片段。
- **依赖扩展（dependency）**：根据检索结果自动补充相关类型定义（如 `ListNode` → 自动引入 `ListNodeKit`）。

### AI Prompt 工作流示例
#### 自动生成测试用例
```text
[System] 你是 LeetCode 测试用例生成器。
[User] 题目：删除排序链表中的重复元素 II（给定 head: ListNode），返回删除重复元素后的链表。...
请按如下模板函数生成一个函数，使其返回边界测试用例，以及随机测试用例：
...
```
框架可调用 RAG 检索已有题目的相似测试模板，并利用 LLM 生成新的用例。

#### 自动编写暴力算法
- 可以考虑用非学生练习语言编写暴力算法，如学生用 Python 作答时，可以用 C/C++ 编写暴力算法，只要统一以 JSON 格式保存输入和预期输出即可。

### 演进路线（Phase 2）
1. **AST Call Graph**：分析代码调用关系（`function A → calls → function B`），使 RAG 理解程序执行流。
2. **SafeIterBase Cython 化**：将安全迭代器的核心循环用 Cython 重写，降低遍历与依赖扩展的成本。
3. **Graph‑RAG**：用图遍历（`query → subgraph retrieval → LLM context injection`）替换纯向量检索，实现真正的代码逻辑理解。

---

## 四、总结

| 模块 | 核心价值 |
|------|----------|
| **多线程测试工具** | 零侵入运行学生代码，自动处理编码/类型/环境，支持并发执行与早停。 |
| **特殊类型调试工具** | 为链表和二叉树提供安全迭代、环检测、美观打印，显著提升调试效率。 |
| **RAG AI Prompt** | 利用检索增强生成自动产生测试用例与暴力算法，并规划向 Graph‑RAG 演进。 |

本项目致力于让本地算法调试体验**无限接近 LeetCode 在线环境**，同时通过结构化的调试工具和 AI 辅助工作流，帮助学习者更快定位问题、验证算法正确性。后续将重点推进 **AST 调用图分析**与 **Graph‑RAG 检索**，使框架从“能找代码”进化为“能理解代码”。


## 🔮 下一步计划

1. **小模型驱动的代码生成流程**  
   题目 → 小型 LLM 提取关键词 → RAG 检索相关代码 → 将题目与参考代码共同输入 LLM → 生成目标代码。

2. **代码自动验证与迭代优化**  
   生成代码 → 检验合规性与安全性（禁用高危库） → 自动执行测试 → 根据错误信息自动反馈并返回上一级循环 → 直至成功执行或超过重试次数。

3. **自定义类的性能优化**  
   - 不再通过对 Python 原生节点进行包装来实现迭代  
   - 改为定义 Cython 原生节点，并将其封装为用户无感的 Python 对象  
   - 迭代过程采用 Cython + C 层高效实现，大幅提升运行效率。
