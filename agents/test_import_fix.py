# agents/test_import_fix.py
"""
验证 AgentIO.auto_fix_imports 在无歧义情况下的 import 自动添加功能。
请从项目根目录运行:  python agents/test_import_fix.py
"""
import sys
from pathlib import Path

# 确保可以导入 agents 模块
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from agents.agent_io import AgentIO

def run_tests():
    tests = []

    # 1. 缺失 random
    code = "def f():\n    random.seed(0)\n"
    fixed = AgentIO.auto_fix_imports(code)
    assert "import random" in fixed, f"测试1失败: {fixed}"
    tests.append(True)

    # 2. 缺失 List
    code = "def f():\n    a: List[int] = []\n"
    fixed = AgentIO.auto_fix_imports(code)
    assert "from typing import List" in fixed, f"测试2失败: {fixed}"
    tests.append(True)

    # 3. 缺失 List + Dict → 合并为一行
    code = "def f():\n    a: List[int] = []\n    b: Dict[str, int] = {}\n"
    fixed = AgentIO.auto_fix_imports(code)
    import re
    match = re.search(r'from typing import (.+)', fixed)
    assert match, f"测试3失败: 无 typing 导入"
    names = set(n.strip() for n in match.group(1).split(','))
    assert names == {"List", "Dict"}, f"测试3失败: 合并不正确 {names}"
    tests.append(True)

    # 4. 已有 from typing import List，额外使用 Dict → 补一行 Dict
    code = "from typing import List\ndef f():\n    a: Dict[str, int] = {}\n"
    fixed = AgentIO.auto_fix_imports(code)
    typing_lines = [l for l in fixed.splitlines() if l.startswith("from typing import")]
    assert len(typing_lines) >= 1
    assert any("Dict" in l for l in typing_lines), f"测试4失败: Dict 未补"
    tests.append(True)

    # 5. 已有 import numpy as np，不应重复添加
    code = "import numpy as np\ndef f():\n    a = np.array([1,2])\n"
    fixed = AgentIO.auto_fix_imports(code)
    assert fixed.count("import numpy as np") == 1, f"测试5失败: 重复导入"
    tests.append(True)

    # 6. 使用别名 np 但未导入 → 补 import numpy as np
    code = "def f():\n    a = np.zeros(10)\n"
    fixed = AgentIO.auto_fix_imports(code)
    assert "import numpy as np" in fixed, f"测试6失败: {fixed}"
    tests.append(True)

    # 7. 直接使用 Counter → 补 from collections import Counter
    code = "def f():\n    c = Counter([1,2,3])\n"
    fixed = AgentIO.auto_fix_imports(code)
    assert "from collections import Counter" in fixed, f"测试7失败: {fixed}"
    tests.append(True)

    # 8. 属性访问 collections.Counter → 补 import collections
    code = "def f():\n    c = collections.Counter([1,2,3])\n"
    fixed = AgentIO.auto_fix_imports(code)
    assert "import collections" in fixed, f"测试8失败: {fixed}"
    tests.append(True)

    # 9. 同时使用 random + math
    code = "def f():\n    x = math.sin(random.random())\n"
    fixed = AgentIO.auto_fix_imports(code)
    assert "import random" in fixed and "import math" in fixed, f"测试9失败: {fixed}"
    tests.append(True)

    # 10. 保留 shebang 和 coding 声明
    code = "#!/usr/bin/env python\n# -*- coding: utf-8 -*-\ndef f():\n    x = random.random()\n"
    fixed = AgentIO.auto_fix_imports(code)
    lines = fixed.splitlines()
    assert lines[0].startswith("#!"), "测试10失败: shebang 丢失"
    assert "coding" in lines[1], "测试10失败: coding 丢失"
    assert "import random" in fixed, "测试10失败: 未补 random"
    tests.append(True)

    # 汇总
    passed = sum(tests)
    total = len(tests)
    print(f"✅ 通过 {passed}/{total} 项测试")
    if passed == total:
        print("🎉 自动 import 修复功能验证全部通过！")
    else:
        print("❌ 部分测试未通过，请检查 AgentIO.auto_fix_imports 实现。")

if __name__ == "__main__":
    run_tests()