你的方向是对的，而且实际上这是一个非常典型的**编译层（solution_runner）与测试层（case_generator）解耦**问题。

目前看起来：

```text
solution_runner
├── 解析 Solution
├── 获取函数签名
├── 获取类型
├── 获取样例生成器(get_cases_generator)
├── 执行代码
└── 校验结果
```

其中：

```python
get_cases_generator()
```

实际上属于：

```text
AI-Agent Test Generation Layer
```

而不是：

```text
Code Execution Layer
```

因此应该移除。

---

# 新架构

建议变成：

```text
                ┌─────────────┐
                │ Solution.py │
                └──────┬──────┘
                       │
                       ▼
             ┌──────────────────┐
             │ solution_runner  │
             └────────┬─────────┘
                      │
              导出统一结构
                      │
                      ▼
            ┌──────────────────┐
            │  SolutionStruct  │
            └────────┬─────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼

case_generator   complexity_ai   judge_ai

```

以后：

```text
Python
C++
Java
Rust
```

全部导出同一种结构。

AI 不再关心源码语言。

---

# Solution_struct.py

建议设计成 dataclass。

## 枚举

```python
from enum import Enum


class Language(Enum):
    PYTHON = "python"
    CPP = "cpp"
    JAVA = "java"


class ParamKind(Enum):
    POSITIONAL = "positional"
```

---

# 参数结构

```python
from dataclasses import dataclass


@dataclass
class ParamStruct:
    name: str
    type_str: str

    origin_type: str | None = None

    nullable: bool = False

    default_value: object | None = None
```

例如：

```python
nums: List[int]
```

导出：

```python
ParamStruct(
    name="nums",
    type_str="List[int]",
    origin_type="list"
)
```

---

# 返回值结构

```python
@dataclass
class ReturnStruct:
    type_str: str

    origin_type: str | None = None
```

例如：

```python
List[int]
```

---

# 方法结构

```python
@dataclass
class MethodStruct:
    name: str

    params: list[ParamStruct]

    return_info: ReturnStruct

    source_code: str
```

例如：

```python
def twoSum(...)
```

导出：

```python
MethodStruct(...)
```

---

# 复杂度提示结构（重点）

未来 AI-agent 非常需要。

```python
@dataclass
class ComplexityHint:
    time_complexity: str | None = None

    space_complexity: str | None = None

    estimated_n_limit: int | None = None

    notes: str | None = None
```

例如：

```python
O(n²)
```

或者：

```python
estimated_n_limit=5000
```

即使当前留空也保留字段。

---

# 主结构

```python
from dataclasses import dataclass, field


@dataclass
class SolutionStruct:

    language: Language

    class_name: str

    source_code: str

    methods: list[MethodStruct]

    complexity_hint: ComplexityHint = field(
        default_factory=ComplexityHint
    )
```

---

# Python 示例

输入：

```python
class Solution:

    def twoSum(
        self,
        nums: List[int],
        target: int
    ) -> List[int]:
        ...
```

导出：

```python
SolutionStruct(
    language=Language.PYTHON,

    class_name="Solution",

    source_code=xxx,

    methods=[
        MethodStruct(
            name="twoSum",

            params=[
                ParamStruct(
                    name="nums",
                    type_str="List[int]"
                ),

                ParamStruct(
                    name="target",
                    type_str="int"
                )
            ],

            return_info=ReturnStruct(
                type_str="List[int]"
            ),

            source_code=...
        )
    ]
)
```

这样 AI 完全不需要解析 Python AST。

---

# solution_runner 需要修改

## 1 删除

直接删除：

```python
get_cases_generator()
```

及其所有调用。

---

## 2 新增

新增：

```python
build_solution_struct()
```

例如：

```python
def build_solution_struct(
        self
    ) -> SolutionStruct:
```

作用：

```python
源码
 ↓
AST
 ↓
SolutionStruct
```

---

## 3 parse_solution()

原来可能返回：

```python
method_name
arg_types
return_type
...
```

改为：

```python
SolutionStruct
```

即：

```python
solution_struct = build_solution_struct()
```

---

## 4 execute_case()

原来：

```python
execute_case(
    func_name,
    args
)
```

建议改：

```python
execute_case(
    method_name,
    args
)
```

因为未来：

```python
Solution
├── solve()
├── solve_v2()
├── brute_force()
```

可能存在多个公开方法。

---

## 5 新增序列化

非常重要。

```python
SolutionStruct.to_json()
```

```python
SolutionStruct.from_json()
```

例如：

```python
solution_struct.json
```

内容：

```json
{
  "language":"python",
  "class_name":"Solution",
  "methods":[
    {
      "name":"twoSum",
      "params":[...]
    }
  ]
}
```

这样：

```text
solution_runner
↓
solution_struct.json
↓
AI-agent
```

两边完全独立。

---

# 为下一步 case_generator 预留

我建议再增加一个字段：

```python
@dataclass
class ConstraintStruct:

    min_value: int | None = None

    max_value: int | None = None

    max_length: int | None = None
```

挂在：

```python
ParamStruct.constraints
```

目前为空。

以后 AI 可以自动填：

```python
nums.length <= 10^5
```

那么 case_generator 就知道：

```python
不要生成 10^8 个元素
```

而是：

```python
边界:
0
1
10^5

随机:
10^5

极端:
全重复
全递增
全递减
```

这样第二阶段的 AI-Agent 可以直接依据 `SolutionStruct + ConstraintStruct + ComplexityHint` 生成测试，而无需再次解析源码。

因此最小侵入式改造实际上只有两件事：

1. 删除 `get_cases_generator()`
2. 新增 `build_solution_struct() -> SolutionStruct`

其它执行逻辑基本不动，属于一次比较干净的架构升级。
