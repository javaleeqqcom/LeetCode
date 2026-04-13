# 📘 LeetCode 本地自动化测试框架（Python）—— README 更新版
- 版本：0.6.7

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

### 🧱 `tools/args_parser.py`（核心基础） + `list_node_kit.py` / `tree_node_kit.py`

> **模块拆分**：原 `args_parser_tools.old.txt` 被拆分为三个职责单一的文件：
> - `args_parser_tools.py`：定义通用基础类 `KitBase`（代理模式）和 `SafeIterBase`（安全迭代器，统一环检测）。
> - `list_node_kit.py`：链表调试增强工具 `ListNodeKit`。
> - `tree_node_kit.py`：二叉树调试增强工具 `TreeNodeKit`，并包含一个**极其精简且巧妙**的统一遍历器 `TreeIter`。

- **`ListNodeKit`**：包装原生 `ListNode`，提供安全扁平化、环检测、可视化打印。
   - `flatten(max_len=None)`
   - 返回 `(nodes, stop_index)`
   - `nodes`：展开得到的节点列表（原生节点）
   - `stop_index` 含义：
      - `-1`：正常结束（无环）
      - `>= 0`：检测到环，值为**环起始索引**
      - `== max_len`：因长度限制提前终止
  - `__repr__`：打印格式 `<class 'ListNodeKit'>: [1,2,>3,4,^]`（`>` 标记环起点，`^` 标记环尾）。
  - `__getitem__(idx)`：索引访问（安全版）
    - 支持链表随机访问
    - 自动处理环
    - kit[n]：
      - 若刚好越界 → 返回空节点（False）
      - 若超出 → 抛 IndexError
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

### 🔷 基础工具（`args_parser_tools.py`）

- `input_parser_registry`：类型转换注册表（如 `List[int] → ListNode`）。
- 预导入常用类型：`Optional`, `List`, `Dict`。

### 🔷 节点调试增强工具（`iter_node_tools.py`）

#### `KitBase`：
- 泛型代理基类，统一处理包装类与原生节点的互转（`unwrap`），避免重复包装。
#### `SafeIterBase`：
- 带环检测的安全迭代器基类，自动记录重复节点索引，支持提前停止或跳过重复节点。
  - 安全性设计（核心价值）
  - 1. 防止死循环（遇到重复节点自动停止）
  - 2. 区分“值相同”和“节点相同”（✔ 使用 **节点 identity（id）判断**，不是 val）
```python
# 不会误判为环
100 -> 100 -> 100
```
---

### 🔷 二叉树调试 —— **✨ 精妙设计：一个 `TreeIter` 搞定所有遍历 ✨**（`tree_node_kit.py`）

传统做法需要为前序、中序、后序、层序分别编写不同的迭代器，代码重复且易错。  
本框架仅用一个 `TreeIter` 类，通过**操作字符串**和**统一的栈/队列容器**，优雅地实现了四种遍历方式，**代码量减少 70% 以上**，并完美继承 `SafeIterBase` 的环检测能力。

#### 核心原理（基于实际代码）

`TreeIter` 构造函数接收三个关键参数：
- `operation`：操作字符串，每个小写字母代表一个动作（**注意：字符含义不同于常见缩写**）
- `use_queue`：`True` 使用队列（层序），`False` 使用栈（深度优先）
- `early_stop`：遇到重复节点时是否立即停止

**动作映射表**（`_operation_funs`）：
| 字符 | 方法 | 作用 |
|------|------|------|
| `l` | `_push_left` | 将当前节点的左子节点压入容器 |
| `r` | `_push_right` | 将当前节点的右子节点压入容器 |
| `c` | `_push_current` | 将当前节点自身**再次**压入容器，并附带一个 `True` 标志（用于后序/中序的二次访问） |
| `u` | `_update_current` | **直接**将当前节点设为 `_current_node`（用于层序或前序的即时输出） |

**遍历实现对照表**（`TreeNodeKit` 提供的方法及内部调用）：
| 遍历方式 | 方法 | `operation` | `use_queue` | 原理 |
|----------|------|-------------|-------------|------|
| 层序遍历 | `layer_iter()` | `"ULR"` | `True` | `u` 立即输出当前节点，然后 `l`、`r` 将左右子入队，利用队列 FIFO 实现层序 |
| 前序遍历 | `NLR_iter()` | `"RLU"` | `False` | 先压右子，再压左子（栈 LIFO 保证左子先出），最后 `u` 输出当前节点 |
| 中序遍历 | `LNR_iter()` | `"RCL"` | `False` | 先压右子，再压**当前节点（带标志）**，最后压左子。弹出时带标志的节点直接输出 |
| 后序遍历 | `LRN_iter()` | `"CRL"` | `False` | 先压**当前节点（带标志）**，再压右子，最后压左子。标志确保左右子处理完毕后才输出根 |
- 另外：`u`可省略，即当 operation 中不含 `c`和`u`，则会在最后一步自动实现`u`。

#### 为什么说“极其精简且巧妙”？

- **一个类代替四个类**：不再需要 `LayeredTraversal`、`PreorderTraversal`、`InorderTraversal`、`PostorderTraversal`。
- **操作字符串驱动**：改变字符串即可切换遍历顺序，逻辑清晰，易于扩展（例如逆层序只需反转队列顺序）。
- **标志位复用**：利用 `c` 动作压入带 `True` 标志的节点，`_prepare_next` 中统一处理“已检查过”的逻辑，巧妙解决了后序和中序需要二次访问父节点的问题。
- **环检测自动继承**：所有遍历共享 `SafeIterBase` 的 `_check_safe`，无需额外代码。
- **代码行数从 300+ 缩减至约 100 行**，可读性和可维护性大幅提升。

**示例：手动创建一个中序遍历迭代器**
```python
it = TreeIter(root, operation="RCL", use_queue=False)
for idx, node in it:
    print(idx, node.val)   # 输出顺序：左 → 根 → 右
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

1. ** SafeIterBase 采用 Cython 加速**
   - 操作对象从原生节点改为包装节点
   - self._seen[原生节点哈希] = [包装节点引用,...]    # values[*] 保存包装节点是因为包装节点可能含有类似 assigned_idx 的信息，若存原生节点则丢失信息。
   - self._revisit_index = [重复访问>1次的 原生节点哈希,...] # 其值必须 in self._seen

2. ** KitBase **
   - 需实现 __hash__ = id(_node) 供 SafeIterBase 确定原生节点哈希
   - KitBase 的子类可以增加 visit_idx 替代原 SafeIterBase._current_idx 的职能
   - 
3. ** 进一步性能优化 **
   - 树节点的 visit_idx 因为（堆索引方式），只需要做如下运算： ==、!=、+1、<<1（或*2）、>>1（或//2）、%2（判断奇偶）。
   - 拟采用带头结点的链表：头结点（链表首指针，二进制位数 usize）、链表节点（next指针，val无符号整型）。其中 链表首 为最低位，以便于 <<1 时，当首指针位数<整型位数，只需要修改首指针.val << 1即可。而无需修改其他指针，+1同理，只有当 val 溢出，才用头插法创建新指针。而 二进制位数 方便确定节点在二叉树的深度
   - 
4. **统一安全迭代器接口**
   - 为 `ListNodeKit` 和 `TreeNodeKit` 增加 `safe_iter()` 方法，返回 `SafeIter` 实例，支持手动安全遍历
   - 树的安全迭代先实现层序遍历（`LayeredTraversal` 包装），后续可扩展前序/中序/后序
5. **优化链表的索引访问**
   - 当链表存在环时，`__getitem__` 可通过取余运算实现任意大索引的 O(环长度) 复杂度访问（类似循环链表）
   - 仅当链表无环且索引超出实际节点数时才抛出 `IndexError`
6. **自动向AI提问**（维持原计划）
   - 注意：提问的范围仅限于测试学生的代码是否正确
   - 用于自动生成测试样例代码
   - 智能地区分单一魔术方法，和多魔术方法等不同情况
   - 若设置的AI-agent，则自动提问测试样例生成代码；若未设置则仅生成 token 提示词，由学生复制后手动向AI提问
7. **极小化预定义代码**（维持原计划）
   - 智能检测用户代码所需的特殊类型定义，筛选其中实际用到的特殊类型代码，减少 pre_code 代码量
8. **更智能的调度策略**（维持原计划）
   - 优化等比递减分割器，使各线程负载更加均衡
   - 改进早停机制，减少多线程环境下的滞后现象
9. **VS Code 插件集成**（维持原计划）
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
