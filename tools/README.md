

# 📘 LeetCode 本地自动化测试框架（Python）—— README 更新版

## 🌟 核心价值
**学生零配置调试 LeetCode 题目**：无需修改学生代码、无需处理编码问题、无需担心类型冲突，完全模拟 LeetCode 在线环境执行逻辑。

---

## 📁 项目结构

### 🔑 `tools/solution_runner.py`（核心引擎）
👉 **革命性设计**：直接加载 `.py` 源文件，自动注入 LeetCode 环境所需类型  
- **构造函数**：`SolutionRunner(solution_file: str, main_method: Optional[str] = None)`
  - `solution_file`：学生代码文件路径（如 `"P82_V0.py"`）
  - `main_method`：当 `Solution` 含多个方法时指定主函数名（如 `"deleteDuplicates"`）；未指定时自动选择唯一非魔术方法
  - **智能处理**：
    - ✅ 自动检测文件编码（UTF-8/GBK/BOM），完美支持中文注释/变量名/字符串
    - ✅ 创建虚拟模块执行学生代码，将 `ListNode`/`TreeNode` 注入全局命名空间
    - ✅ 确保学生代码中的 `ListNode` 与转换器使用的 **完全同一对象**（内存地址一致）
- **核心方法**：
  - `read_test_case(path_list, file_name_pattern=None)`：解析测试文件，**自动完成类型转换**（如 `list → ListNode`）
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

---

## 💡 为什么能完美工作？
| 问题 | 传统方案 | 本框架方案 |
|------|----------|------------|
| **类型不一致** | 导致 `isinstance` 失败 | 虚拟模块注入 → **同一内存对象** |
| **中文编码错误** | 手动指定 encoding | `charset-normalizer` 智能检测 |
| **学生代码需修改** | 删除注释/调整导入 | **零修改**，保留 LeetCode 原生写法 |
| **self 参数绑定** | 签名验证失败 | 使用 **绑定方法签名**（自动排除 self） |

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
| **学生** | 1. 编写标准 LeetCode 风格代码（含 `Solution` 类）2. 创建极简 `run_solution.py`3. 运行测试，查看日志 |
| **教师** | 1. 提供测试样例文件（`.txt`）2. 框架自动处理类型转换与执行 |
| **框架** | 全程透明：编码检测 → 类型注入 → 样例转换 → 执行验证 → 日志输出 |

> 💬 **学生反馈**：  
> *“终于不用在本地反复删改 ListNode 定义了！代码和 LeetCode 上完全一致，调试效率翻倍！”*  
> *“中文注释再也不报错了，日志文件清晰展示每一步输入输出，排查 bug 超方便！”*

---

✨ **让本地调试体验无限接近 LeetCode 在线环境，专注算法本身，告别环境配置烦恼！** ✨