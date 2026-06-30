# agents/__init__.py
import sys
from pathlib import Path

# 自动将目录加入 sys.path
_AGENTS_DIR = Path(__file__).resolve().parent
if str(_AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENTS_DIR))
    print(f"RAG_INIT_ADD: {_AGENTS_DIR}")

# _LEETCODE_ROOT = _RAG_DIR.parent
# if str(_LEETCODE_ROOT) not in sys.path:
#     sys.path.insert(0, str(_LEETCODE_ROOT))
#     print(f"RAG_INIT_ADD: {_LEETCODE_ROOT}")