# 📘 LeetCode 本地自动化测试框架（Python）—— README 更新版
- 版本：0.5.14

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



### 🧱 `tools/args_parser.py`
👉 定义 LeetCode 标准数据结构及链表安全工具类
- `ListNode` / `TreeNode`：带友好 `__repr__`（打印链表/树结构，自动处理环路）
- `input_parser_registry`：注册类型转换器（如 `(ListNode, list) → List2ListNode`）
- 预导入常用类型：`Optional`, `List`, `Dict`
- 提供了 **`ListNodeKit`** 链表安全增强工具类：
  - **`ListNodeKit`**是用于辅助链表调试的包装类，提供安全的扁平化、环检测和打印功能。它将原生 `ListNode` 节点包装为增强对象，保持链式操作的类型一致性。

#### ListNodeKit
- **安全扁平化**：自动检测环路（返回节点列表和环起始索引，-1表示无环）
- **死循环防护**：处理带环链表时能自动检测首个成环节点并终止迭代，避免死循环
- **篡改验证**：通过 `flatten()` 方法验证学生代码是否修改链表结构
- **可视化打印**：`to_string()` 安全打印链表，若链表有环，则以 `>` 表示环起点，结尾 `^` 表示最后一个节点后继到环起点。
- **便捷操作**：支持 `ListNodeKit(head)[index]` 索引访问，简化测试用例验证

#### TreeNodeKit
- **安全层序遍历**：基于 `SafeIter` 实现环检测，`flatten()` 返回节点列表与首次重复的完全二叉树索引。
- **索引访问保护**：`__getitem__` 遇到环时立即停止并抛出 `IndexError`，附带重复键和已遍历节点数，避免死循环。
- **可视化打印**：`__repr__` 输出层序节点及其完全二叉树索引，若有重复节点则标记 `repeat_key`。

```python
# 使用示例
head = List2ListNode([1,2,3,4,5])
ListNodeKit(head)[4].next = head  # 创建环

# 安全检测
nodes, cycle_idx = ListNodeKit(head).flatten()
assert cycle_idx == 0  # 环起点在索引0

# 验证链表未被篡改
student_result = solve(head)
after_nodes, _ = ListNodeKit(student_result).flatten()
assert after_nodes == nodes  # 确保学生未修改链表结构
```

### `tools/compacted_json.py`
用于将 JSON 数据进行压缩，减少文件大小。
- 其 __main__ 调用 random_object.py 进行测试，……未完待续……

## 项目测试代码（用于验证项目程序的可靠性）

### `tools/random_object.py`
用于生成随机对象，采用模块化……未完待续……

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

## 🔮 当前特性增强

### 🚀 多线程支持
- ✅ **支持多线程**：通过 `thread` 参数控制线程数量，支持单线程（thread=1）和多线程（thread>1）模式
- ⚠️ **路径限制**：执行的Python脚本必须在LeetCode工程根目录，否则多线程功能不可用（放在其他目录则不支持多线程）
- 📊 **性能提升**：多线程可显著提升大规模测试用例的执行速度

### 📁 智能文件管理
- ✅ **自动目录管理**：输出的日志文件和临时保存的JSON文件都会自动放置到学生代码文件所在的目录下，不会污染根目录
- 🗂️ **组织清晰**：所有相关文件都集中存放，便于管理和查找

### ⚡ 早停机制
- ✅ **支持早停**：通过 `early_stop` 参数控制早停行为
  - 当 `early_stop < 1` 时，按错误比例早停（如 `early_stop=0.1` 表示错误率达到10%时停止）
  - 当 `early_stop >= 1` 时，按错误数量早停（如 `early_stop=5` 表示出现5个错误时停止）
- ⚠️ **多线程延迟**：在多线程环境下，早停会有一定滞后，因为需要等待当前正在执行的批次完成

### 支持自定义类的双向转化
- 在 custom_init.py 定义的如链表、二叉树等 LeetCode 部分题目定义结构，需要以基础类型如List进行相互转换，以便多线程执行时不依赖自定义类（容易导致类名相同但认为是不同类型的冲突）。
- 通过 custom_init.py 中的 input_parser_registry 自动查找互转函数并执行实现。
- 比较结果时统一转换为 JSON 标准输入的类型，以避免内存地址不一致的、实际代码同构的类型，无法比较的错误。

在“当前特性增强”部分，我们已经有了“支持自定义类的双向转化”小节，现在在其后增加“自定义类打印调试”小节，描述本次打印格式的优化和树形图的增强。

### 自定义类打印调试
- ✅ **链表友好打印**：`ListNodeKit` 的 `__repr__` 输出格式统一为 `<class 'ListNodeKit'>: [1,2,3]`，便于日志正则提取。支持自动检测环路，环起点用 `>` 标记，环尾用 `^` 标记，例如 `<class 'ListNodeKit'>: [1,>,2,3,4,^]`。
- ✅ **二叉树美观打印**：`TreeNodeKit` 的 `__repr__` 生成树形结构图（利用 `binarytree` 库），同时输出完全二叉树索引与节点值的映射，超长树自动截断，环检测时标记重复键。示例输出（检测到非法重复键）：
```
<class 'TreeNodeKit'>: {
  "stop_by_duplicate_idx": 6,
  "tree_by_idx": """
    1___
   /    \
  2     _3
 /     /  \
4     *6   7
""",
  "idx:val": {1: 1, 2: 2, 3: 3, 4: 4, 6: 6, 7: 7}
}
```
- ✅ **属性名定制**：通过 `prep_property` 参数可指定节点取值属性（如 `val`、`value`），适配不同题目。
- ✅ **空值安全**：空链表/空树打印为 `<class 'ListNodeKit'>: []` 或 `<class 'TreeNodeKit'>: empty`，避免属性访问异常。

---

## 🌈 当前进展
- ✅ **类型一致性彻底解决**：虚拟模块注入机制，100% 匹配 LeetCode 执行环境
- ✅ **全编码支持**：中文注释/变量名/字符串无压力
- ✅ **签名绑定修复**：绑定方法签名验证，杜绝 `missing self` 错误
- ✅ **多方法支持**：`main_method` 参数灵活指定主函数
- ✅ **日志系统完善**：独立日志文件 + 时间戳 + 异常堆栈 + 耗时统计 + 错误记录 + print 重定向
- ✅ **多线程支持**：并发执行测试用例，大幅提升大规模测试效率
- ✅ **智能文件管理**：自动将日志和临时文件存储到学生代码目录下
- ✅ **早停机制**：支持按错误数量或比例进行早停，节省无效计算时间
- ✅ **安全迭代器 SafeIter**：统一实现链表和二叉树的环检测，避免死循环，`__getitem__` 支持环检测并抛出明确异常。

---

## 🔮 下一步计划

- ~~args_parser.py 中的自定义类方法有死循环的风险，必须完善。如链表成环、树有环等，需增加环路检测。~~ ✅ **已完成**
   - 已通过 `test_listnode_kit` 和 `test_TreeNodeKit` 测试
   - 已实现 `SafeIter` 统一安全迭代器，替代原有 `SafeFlatten`
   - 已提取 `KitBase` 基类，消除 `ListNodeKitBase` 与 `TreeNodeKitBase` 的重复代码
- ~~增强树的可视化打印~~✅ **已完成**
   - 已实现 直观的二叉树打印方法
1. **SafeIterBase**
   - 实现是否早停选项 early_stop，若非早停，则记录全部重复节点，便于调试和分析
   - 当 early_stop 为 True 时，检测到任何重复节点时即终止遍历，不管遍历类的栈或队列是否还有元素；
   - 当 early_stop 为 False 时，也能防止死循环（要求继承类合理调用安全检查下），检测到重复节点时记录同时阻止根据重复节点而后继的行为。
   - _seen 成员变量改为 {node:[历次访问时的 idx，...]}，通过遍历 _seen 可以得到所有指向重复节点的索引，即可还原如树结构的非法路径
   - repeat_idx 改为数组，记录所有重复节点（当非早停时至多只能有1个元素）
   - 将来可以用 Cython 优化性能，唯一需要依赖 python 结构的就只有求 id(node) 吧
2. **统一安全迭代器接口**
   - 为 `ListNodeKit` 和 `TreeNodeKit` 增加 `safe_iter()` 方法，返回 `SafeIter` 实例，支持手动安全遍历
   - 树的安全迭代先实现层序遍历（`LayeredTraversal` 包装），后续可扩展前序/中序/后序
3. **优化链表的索引访问**
   - 当链表存在环时，`__getitem__` 可通过取余运算实现任意大索引的 O(环长度) 复杂度访问（类似循环链表）
   - 仅当链表无环且索引超出实际节点数时才抛出 `IndexError`
4. **自动向AI提问**（维持原计划）
   - 注意：提问的范围仅限于测试学生的代码是否正确
   - 用于自动生成测试样例代码
   - 智能地区分单一魔术方法，和多魔术方法等不同情况
   - 若设置的AI-agent，则自动提问测试样例生成代码；若未设置则仅生成 token 提示词，由学生复制后手动向AI提问
5. **极小化预定义代码**（维持原计划）
   - 智能检测用户代码所需的特殊类型定义，筛选其中实际用到的特殊类型代码，减少 pre_code 代码量
6. **更智能的调度策略**（维持原计划）
   - 优化等比递减分割器，使各线程负载更加均衡
   - 改进早停机制，减少多线程环境下的滞后现象
7. **VS Code 插件集成**（维持原计划）
   - 一键运行当前题目测试，结果直接显示在编辑器侧边栏

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
