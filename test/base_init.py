# base_init.py
from typing import *
import ast

def parse_int(s: str) -> int:
    return int(ast.literal_eval(s))

def parse_float(s: str) -> float:
    return float(ast.literal_eval(s))

def parse_str(s: str) -> str:
    val = ast.literal_eval(s)
    if not isinstance(val, str):
        raise ValueError(f"Expected string, got {type(val)}")
    return val

def parse_list(s: str) -> list:
    val = ast.literal_eval(s)
    if not isinstance(val, list):
        raise ValueError(f"Expected list, got {type(val)}")
    return val

def parse_bool(s: str) -> bool:
    val = ast.literal_eval(s)
    if not isinstance(val, bool):
        raise ValueError(f"Expected bool, got {type(val)}")
    return val

# 基础类型注册表（键：(类型名,)，值：解析函数）
base_input_parser_registry = {
    ("int",): lambda args: parse_int(args[0]),
    ("float",): lambda args: parse_float(args[0]),
    ("str",): lambda args: parse_str(args[0]),
    ("bool",): lambda args: parse_bool(args[0]),
    ("list",): lambda args: parse_list(args[0]),  # 注意：不处理泛型如 List[int]
}