从工程演进角度看，我建议：

> **短期：Prompt约束 + 自动补齐 import 双保险**
>
> **长期：做一个真正的 Python 依赖分析器（AST级）**
>
> **不建议：在 case_generator 前面无脑 prepend 一大堆 import**

因为你的系统已经进入 Agent + 半监督阶段，未来 LLM 生成代码会越来越复杂，单纯预置 import 很快失控。

---

# 先分析这次为什么出错

LLM生成：

```python
values = random.sample(...)
random.shuffle(...)
nums: List[int] = []
```

实际缺失：

```python
import random
from typing import List
```

说明：

AgentIO.clean_llm_code()

只负责：

````python
去 think
提取 ```python
截取 def case_generator
````

没有做：

```python
代码合法性修复
```

所以：

```python
exec(generated_code)
```

直接炸。

---

# 方案1：统一预置所有库

例如：

```python
PREFIX = r'''
from typing import *
import random
import math
import itertools
import collections
import heapq
import bisect
'''
```

然后：

```python
generated_code = PREFIX + generated_code
```

---

## 优点

实现最快

5分钟搞定

---

## 缺点

以后越来越脏

例如：

```python
numpy
networkx
sortedcontainers
fractions
decimal
```

要不要预置？

再以后：

```python
from collections import defaultdict
```

用户生成：

```python
defaultdict(...)
```

又会炸。

---

而且：

```python
exec()
```

环境和保存到文件的代码不一致。

这是最大问题。

你保存的是：

```python
case_generator_002.py
```

用户打开：

```python
NameError
```

但运行时：

```python
没问题
```

调试困难。

---

# 方案2：自动补齐 import（推荐）

你的想法其实已经接近 Copilot 的做法。

---

# 第一版可以非常简单

建立映射表：

```python
COMMON_IMPORTS = {
    "random": "import random",

    "math": "import math",

    "np": "import numpy as np",

    "numpy": "import numpy",

    "List": "from typing import List",
    "Dict": "from typing import Dict",
    "Tuple": "from typing import Tuple",
    "Set": "from typing import Set",

    "Counter": "from collections import Counter",
    "defaultdict": "from collections import defaultdict",
    "deque": "from collections import deque",

    "heapq": "import heapq",
    "bisect": "import bisect",
}
```

---

AST解析：

```python
import ast
```

获取：

```python
已导入名字
```

以及：

```python
所有使用名字
```

例如：

```python
random
List
Counter
```

---

差集：

```python
used - imported
```

然后补齐。

---

# 示例实现

直接放 AgentIO：

```python
@classmethod
def auto_fix_imports(cls, code:str)->str:
    import ast

    COMMON_IMPORTS = {
        "random": "import random",
        "math": "import math",

        "List": "from typing import List",
        "Dict": "from typing import Dict",
        "Tuple": "from typing import Tuple",
        "Set": "from typing import Set",

        "Counter": "from collections import Counter",
        "defaultdict": "from collections import defaultdict",
        "deque": "from collections import deque",
    }

    tree = ast.parse(code)

    imported = set()
    used = set()

    class Visitor(ast.NodeVisitor):

        def visit_Import(self,node):
            for alias in node.names:
                imported.add(alias.asname or alias.name.split(".")[0])

        def visit_ImportFrom(self,node):
            for alias in node.names:
                imported.add(alias.asname or alias.name)

        def visit_Name(self,node):
            used.add(node.id)

    Visitor().visit(tree)

    missing = []

    for name in sorted(used):
        if name in COMMON_IMPORTS and name not in imported:
            missing.append(COMMON_IMPORTS[name])

    if missing:
        code = "\n".join(missing) + "\n\n" + code

    return code
```

---

然后：

```python
code = AgentIO.clean_llm_code(raw)

code = AgentIO.auto_fix_imports(code)
```

即可。

---

# 但这里还有一个坑

仅看 Name 不够。

例如：

```python
np.random.randint(...)
```

AST里出现：

```python
Name("np")
```

没问题。

---

但：

```python
random.Random(...)
```

也只会看到：

```python
Name("random")
```

没问题。

---

真正麻烦的是：

```python
collections.Counter(...)
```

AST看到：

```python
Name("collections")
```

而不是：

```python
Counter
```

所以建议映射里同时支持：

```python
"collections": "import collections"
```

---

# 我更推荐的 V0.7.6 做法

新增：

```python
AgentIO.validate_python_code()
```

流程：

```text
clean_llm_code
    ↓
auto_fix_imports
    ↓
ast.parse
    ↓
compile
    ↓
exec(test namespace)
```

---

例如：

```python
try:
    compile(code,"<agent>","exec")
except Exception as e:
    ...
```

如果失败：

```python
提示用户重新生成
```

而不是等到：

```python
build_test_cases()
```

才炸。

---

# 最终架构建议

V0.7.6：

```text
LLM
 ↓
clean_llm_code
 ↓
auto_fix_imports
 ↓
syntax_check
 ↓
save file
 ↓
exec
 ↓
case_generator
```

V0.8：

```text
LLM
 ↓
clean_llm_code
 ↓
AST依赖分析
 ↓
自动补 import
 ↓
静态检查
 ↓
执行沙箱验证
 ↓
保存
```

这样以后无论是：

```python
random
typing
collections
heapq
bisect
math
numpy
```

都能自动修复，Agent 的容错率会明显提升，而且保存下来的 `case_generator_xxx.py` 本身就是可运行文件，不会出现“运行能过、文件不能跑”的状态。
