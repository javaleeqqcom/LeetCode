# Solution_init.py
from typing import *
from math import inf, isinf, isnan
from collections import deque, defaultdict, Counter

# 辅助 List、Dict 的构造的函数
……

# ====== 【核心】注册转换规则 ======
# 键：(目标类型名, 输入类型签名...)
# 值：转换函数
base_input_parser_registry = {
    ("int","str"): lambda string: int(string),
    ("float","str"): lambda string: float(string),
    ("List",): : # 需要根据 List[class] 内部的 class 递归创建
    ("Dict",) : # 需要根据 Dict[class] 内部的 class 递归创建
}