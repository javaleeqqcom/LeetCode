

# 📘 LeetCode 本地自动化测试框架（Python）—— README 更新版

## 🌟 核心价值
**学生零配置调试 LeetCode 题目**：无需修改学生代码、无需处理编码问题、无需担心类型冲突，完全模拟 LeetCode 在线环境执行逻辑。

---

## 📁 项目结构

### 🔑 `tools/solution_runner.py`（核心引擎）
👉 **全格式兼容与防呆设计**：直接加载 `.py` 源文件，自动注入 LeetCode 环境所需类型，并具备智能防错机制。

- **构造函数**：`SolutionRunner(solution_file: str, main_method: Optional[str] = None)`
  - `solution_file`：学生代码文件路径（如 `"P82_V0.py"`）
  - `main_method`：当 `Solution` 含多个方法时指定主函数名（如 `"deleteDuplicates"`）；未指定时自动选择唯一非魔术方法
  - **智能处理**：
    - ✅ **自动检测文件编码**（UTF-8/GBK/BOM），完美支持中文注释/变量名/字符串
    - ✅ **创建虚拟模块**执行学生代码，将 `ListNode`/`TreeNode` 注入全局命名空间，确保内存地址一致性
    - ✅ **JSON 自适应识别**：智能解析由框架生成的 JSON 格式测试用例，**自动推断参数结构**，无需手动指定参数数量（`params_num`），解决了不同格式间的解析割裂问题

- **核心方法**：
  - `read_test_case(path_list, file_name_pattern=None)`：
    - **双重解析引擎**：自动识别文件后缀（`.json` 或 `.txt`）
    - **签名绑定验证**：在读取阶段即利用函数签名（Signature）进行参数绑定验证
  - `run(test_cases, log_suffix=None)`：执行测试
    - `log_suffix=None`：静默运行
    - `log_suffix="_debug"`：为每个用例生成日志（含输入/输出/耗时/异常堆栈），文件名自动去非法字符+防冲突
  
### 📜 `tools/examples_parser.py`
👉 智能解析 LeetCode 风格测试样例（`.txt`）
- 支持字典格式（含 `input`/`output`/`expected`）与元组格式
- 安全转换：`null→None`, `true→True`, `false→False`（保留字符串内关键字）
- 使用 `ast.literal_eval` 安全解析嵌套结构
- ⚠️ 学生不可修改（调试完成后建议设为只读）

### 🧱 `tools/custom_init.py`
👉 定义 LeetCode 标准数据结构
- `ListNode` / `TreeNode`：带友好 `__repr__`（打印链表/树结构）
- `input_parser_registry`：注册类型转换器（如 `(ListNode, list) → List2ListNode`）
- 预导入常用类型：`Optional`, `List`, `Dict`

### `tools/compacted_json.py`
用于将 JSON 数据进行压缩，减少文件大小。
- 其 __main__ 调用 random_object.py 进行测试，……未完待续……

## 项目测试代码（用于验证项目程序的可靠性）

### `tools/random_object.py`
用于生成随机对象，采用模块化……未完待续……

### `tools/parser_test.py`
未完待续……

---

## 🚀 快速开始（学生只需 4 行代码！）

### ✅ `run_solution.py`（学生编写）
```python
from tools.solution_runner import SolutionRunner

runner = SolutionRunner("P82_V0.py")  # 或指定方法：SolutionRunner("P82_V0.py", main_method="deleteDuplicates")
cases = runner.read_test_case("P82q1.txt")
results = runner.run(cases, log_suffix="_V0")  # 生成日志：P82q1.txt#1_V0.log
print(results)
```

### ✅ `P82_V0.py`（学生代码，**无需任何修改**）
```python
from typing import Optional

class Solution:
    def deleteDuplicates(self, head: Optional[ListNode]) -> Optional[ListNode]:
        # LeetCode 标准写法，直接使用 ListNode（无需导入！）
        dummy = ListNode(0)
        dummy.next = head
        prev = dummy
        while head:
            if head.next and head.val == head.next.val:
                while head.next and head.val == head.next.val:
                    head = head.next
                prev.next = head.next
            else:
                prev = prev.next
            head = head.next
        return dummy.next
```

### ✅ `P82q1.txt`（测试样例）
```
input:
{"head": [1,2,3,3,4,4,5]}
output:
[1,2,5]

input:
{"head": [1,1,1,2,3]}
output:
[2,3]
```

## 🔥 暴力算法测试用例生成

框架支持通过暴力算法生成可靠的测试用例，用于验证优化算法的正确性。

### 📝 步骤1: 创建暴力解法
创建`brute.py`文件，实现暴力解法（时间复杂度可能较高，但保证正确）:
```python
class Solution:
    def yourMethod(self, param1, param2):
        # 暴力解法实现 ...
```

### 🚀 步骤2: 生成测试用例
创建`run_brute.py`文件:
```python
from tools.solution_runner import SolutionRunner

# 初始化暴力解法运行器
brute = SolutionRunner("brute.py")

# 生成测试用例指引
brute.get_ask_for_cases()  # 生成brute.txt文件，包含生成测试用例的指引

# 定义测试用例生成函数
def cases_generation(max_size=5, num_cases=10):
    # 生成测试用例的逻辑 ...

# 保存测试用例，并自动运行暴力算法生成expected结果
brute.save_cases(cases_generation, max_size=10, num_cases=20)
```

### ✅ 步骤3: 测试优化算法
创建`run_optimized.py`文件测试优化算法:
```python
from tools.solution_runner import SolutionRunner

# 加载优化算法
optimized = SolutionRunner("optimized.py")

# 读取生成的测试用例
cases = optimized.read_test_case("brute.json")  # 由brute.save_cases()生成

# 运行测试
results = optimized.run(cases, log_suffix="_optimized")
```

### 💡 为什么这种方式更好？
| 问题 | 传统方案 | 本框架方案 |
| --- | --- | --- |
| 测试用例正确性 | 人工编写，易出错 | 由暴力算法自动生成，100%正确 |
| 测试用例多样性 | 有限的手动测试 | 参数化生成，覆盖边界条件 |
| 算法对比 | 需手动对比结果 | 自动对比expected与output |
| 调试效率 | 逐个测试 | 批量验证，快速定位问题 |

###  💡 **元组格式说明**：
- 在生成测试用例时，如需使用元组格式（无"输入"关键词），请确保每个测试用例的参数数量一致，并在调用`read_test_case`时提供`params_num`参数。

### 📊 测试用例格式说明

测试用例数据是一个列表`List`，其中的每个元素代表一个次调用测试函数的输入，支持两种输入格式:

1. **字典格式**（含"输入"关键词）:
   ```
   输入
   n = 7
   edges = [[0, 1], [0, 2], [1, 4], [1, 5], [2, 3], [2, 6]]
   hasApple = [False, False, True, False, True, True, False]
   输出
   8
   预期结果
   null
   ```

2. **元组格式**（无"输入"关键词，仅包含连续参数行）:
   ```
   7
   [[0, 1], [0, 2], [1, 4], [1, 5], [2, 3], [2, 6]]
   [False, False, True, False, True, True, False]
   ```
   
   **元组格式要求**:
   - 文件**不包含**"输入"关键词
   - 仅包含连续的参数行
   - 需要指定每个测试用例的参数数量（`params_num`）
   - 每 `params_num` 行组成一个测试用例
   - **不包含**"输出"和"预期结果"部分（这些信息应通过其他方式提供）

注意: 需要在外面再包裹一层`List`（哪怕只有1次测试）才是最终的测试数据结构。

---

## 💡 为什么能完美工作？

这些修改完善了框架对暴力算法测试用例的支持，使开发者可以:
1. 自动生成测试用例指引
2. 通过函数或直接提供方式创建测试用例
3. 自动运行暴力算法获取正确结果
4. 将测试用例保存为JSON格式
5. 用这些用例验证优化算法

这种设计符合框架核心价值：无需修改学生代码、自动处理编码问题、无需担心类型冲突，完全模拟LeetCode在线环境，同时增加了算法对比的能力。
---

## 🌈 当前进展
- ✅ **类型一致性彻底解决**：虚拟模块注入机制，100% 匹配 LeetCode 执行环境
- ✅ **全编码支持**：中文注释/变量名/字符串无压力
- ✅ **签名绑定修复**：绑定方法签名验证，杜绝 `missing self` 错误
- ✅ **多方法支持**：`main_method` 参数灵活指定主函数
- ✅ **日志系统完善**：独立日志文件 + 时间戳 + 异常堆栈 + 耗时统计

---

## 🔮 下一步计划
1. **JSON 测试样例支持**  
   → 生成更清晰、无歧义的测试数据（AI 友好），兼容现有 TXT 格式
2. **结果自动比对**  
   → 输出 `passed/failed` 状态 + 差异高亮（对比 `output` 与 `expected`）
3. **多算法对比**  
   → 注意禁止同时加载多个解法文件！而是通过构造 brute 对象，生成 expected 的测试样例实现对比
4. **多进程加速、早停机制**
   适配大规模随机样例测试，实现多进程加速、早停机制（错误次数、比例早停，以及超时早停）。
5. **VS Code 插件集成**  
   → 一键运行当前题目测试，结果直接显示在编辑器侧边栏

---

## 📌 使用规范
| 角色 | 操作 |
|------|------|
| **学生** | 1. 编写标准 LeetCode 风格代码（含 `Solution` 类）<br>2. 创建极简 `run_solution.py`<br>3. 运行测试，查看日志 |
| **教师** | 1. 提供测试样例文件（`.txt`）<br>   - **字典格式**：包含"输入"关键词，每个测试用例包含输入、输出和预期结果<br>   - **元组格式**：不包含"输入"关键词，仅包含连续参数行，需指定参数数量（`params_num`）<br>2. 框架自动处理类型转换与执行 |
| **框架** | 全程透明：编码检测 → 类型注入 → 样例转换 → 执行验证 → 日志输出 |

> 💬 **学生反馈**：  
现在出现了测试用例非法的问题：
为了适应这种情况，需要对 SolutionRunner 的 run 和 save_cases 的架构进行优化：
1. 撤销 save_cases 方法，让学生自行调用 cases_generation 得到 cases 代入 run 计算结果
2. 修改 run 方法，让其以 List[case+{"output":每一个样例的返回结果} if not-error else {"error":错误信息,"traceback":错误} for case in cases] 格式输出结果
3. 新增一个 get_expected_cases 方法，用于过滤得到无 error 的测试用例，并将其 "output" 改为 "expected"，以便用于暴力算法的标准答案验证。
4. run的多线程和早停等，可视情况逐步实现
---

✨ **让本地调试体验无限接近 LeetCode 在线环境，专注算法本身，告别环境配置烦恼！** ✨