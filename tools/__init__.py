# tools/__init__.py
import sys
from pathlib import Path

# 自动将 LeetCode 根目录加入 sys.path
_TOOLS_DIR = Path(__file__).resolve().parent
_LEETCODE_ROOT = _TOOLS_DIR.parent
if str(_LEETCODE_ROOT) not in sys.path:
    sys.path.insert(0, str(_LEETCODE_ROOT))