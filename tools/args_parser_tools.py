from typing import Any, Callable, Dict, List, Tuple, Union, Optional, get_type_hints, get_args, get_origin,Generic,TypeVar,Iterator,Hashable,Deque,Iterable,Protocol, runtime_checkable ,cast
from collections import deque,defaultdict
from itertools import chain
from typing_extensions import Self
from binarytree import build
import json
import numpy as np
import cython

__DEBUG__ = False

def _is_base_type(sig_type) -> bool:
    """
    判断类型是否属于 _BASE_TYPE 范畴
    _BASE_TYPE = Union[
        _BASE_TYPE,  # int, float, bool, None, str
        List["_BASE_TYPE"], 
        Dict[Union[str, int], "_BASE_TYPE"]
    ]
    """
    # 处理 Optional/Union 类型
    origin = get_origin(sig_type)
    
    if origin is Union:
        args = get_args(sig_type)
        # 过滤掉 NoneType，检查所有非 None 类型
        non_none_args = [arg for arg in args if arg is not type(None)]
        # 所有非 None 类型都必须是标准类型
        return all(_is_base_type(arg) for arg in non_none_args)
    
    # 基础类型检查
    if sig_type in (int, float, bool, str, type(None)):
        return True
    
    # List 类型检查
    if origin is list or sig_type is list:
        args = get_args(sig_type)
        if not args:  # 裸 list
            return True
        # 检查元素类型
        return all(_is_base_type(arg) for arg in args)
    
    # Dict 类型检查
    if origin is dict or sig_type is dict:
        args = get_args(sig_type)
        if not args:  # 裸 dict
            return True
        # 检查键类型（必须是 str 或 int）和值类型
        key_type, value_type = args[0], args[1] if len(args) > 1 else Any
        key_ok = key_type in (str, int) or get_origin(key_type) is Union
        value_ok = _is_base_type(value_type)
        return key_ok and value_ok
    
    # 其他类型（如 ListNode, TreeNode 等自定义类型）
    return False

def _extract_actual_type(sig_type):
    """
    从类型注解中提取实际类型，用于注册表匹配
    """
    origin = get_origin(sig_type)
    
    if origin is not None:
        # 处理 Union/Optional 情况
        if origin is Union:
            args = get_args(sig_type)
            # 过滤掉 NoneType，返回第一个非 None 类型
            non_none_args = [arg for arg in args if arg is not type(None)]
            if len(non_none_args) == 1:
                return _extract_actual_type(non_none_args[0])
            elif len(non_none_args) > 1:
                # 多个非 None 类型，返回第一个（Union 情况）
                return _extract_actual_type(non_none_args[0])
        else:
            return origin
    
    # 非泛型类型，直接返回
    return sig_type

def _formated_string(val):
    # 处理字符串类型：转义单引号并包裹在 '' 中
    if isinstance(val, str):
        escaped = val.replace("'", "\\'")
        return f"'{escaped}'"
    
    # 递归处理列表
    elif isinstance(val, list):
        return "[" + ", ".join(_formated_string(item) for item in val) + "]"
    
    # 递归处理字典
    elif isinstance(val, dict):
        # 注意：这里根据需求，如果是嵌套处理，只需对内部值再次调用即可
        return "{" + ", ".join(f"{_formated_string(k)}: {_formated_string(v)}" for k, v in val.items()) + "}"
    
    # 递归处理元组
    elif isinstance(val, tuple):
        return "(" + ", ".join(_formated_string(item) for item in val) + ")"
    
    # 其他基本类型（int, float, bool 等）直接返回其字符串表示
    else:
        return str(val)

import functools
import inspect

def ReprDecorator(prep_property: str = "val"):
    def wrapper(cls):
        # 获取父类 _to_string 的签名
        orig_method = cls._to_string
        sig = inspect.signature(orig_method)
        
        @functools.wraps(orig_method)
        def to_str(self, *args, **kwargs):
            # 自动注入 prep_property，其余参数透传
            bound = sig.bind_partial(self, *args, **kwargs)
            return orig_method(
                self, 
                prep_property=prep_property, 
                **{k: v for k, v in bound.arguments.items() if k != 'root'}
            )
        
        def _repr(self):
            return self.to_str()
        
        cls.to_str = to_str
        cls.__repr__ = _repr
        return cls
    return wrapper

def _safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        return f"<error: {type(e).__name__}>"

def _at_id(obj):
    if obj is None:
        return ""
    return f"at 0x{id(obj):012X}"

_MAX_LEN_A_LINE = 80

def _format_repr(obj, *args, **kwargs):
    """
    通用对象格式化打印工具（支持嵌套结构、递归、异常保护）。

    ----------------------------------------
    🧩 基本功能
    ----------------------------------------
    将对象格式化为结构化字符串，支持：
    - 属性访问
    - 嵌套对象递归
    - 自定义函数计算
    - 自动单行 / 多行布局
    - 异常安全访问（不会中断）

    ----------------------------------------
    📌 基本用法
    ----------------------------------------

    1️⃣ 打印属性：
        _format_repr(obj, "val", "next")

    输出：
        <ClassName> { val: ..., next: ... }

    ----------------------------------------
    🧠 参数说明
    ----------------------------------------

    obj:
        要打印的对象

    *args:
        支持三种类型（按顺序解析）：

        1. str
            表示对象属性名
            如：
                "val" → obj.val

        2. callable
            函数：fn(obj) → 任意值
            - 若在最前面，会作为 header 注释
            - 否则作为普通字段输出

        3. dict
            结构描述（递归 DSL）
            如：
                {
                    "left": ("val",),
                    "right": ("val",)
                }

    **kwargs:
        等价于 dict 配置（只处理一次）

    ----------------------------------------
    🔁 递归规则（tuple）
    ----------------------------------------

    若字段配置为 tuple：

        key = (arg1, arg2, ..., sub_dict?)

    则表示递归调用：

        _format_repr(child, *args, **kwargs)

    示例：

        _format_repr(obj,
            left=("val",),
            right=("val",)
        )

    ----------------------------------------
    ⚙️ 支持类型总结
    ----------------------------------------

    字段值 prop 支持：

        tuple       → 递归
        callable    → 动态计算
        str         → 原样字符串
        None        → 输出 None

    ----------------------------------------
    🛡 异常处理
    ----------------------------------------

    所有 getattr / callable 均自动 try/except：

        <error: ExceptionType>

    不会中断打印流程

    ----------------------------------------
    🧾 输出格式
    ----------------------------------------

    Header:
        <ClassName [notes]>

    Body:
        单行：
            <A> { x: 1, y: 2 }

        多行：
            <A> {
                x: 1
                y: 2
            }

    自动根据长度切换（_MAX_LEN_A_LINE）

    ----------------------------------------
    💡 示例
    ----------------------------------------

        _format_repr(
            node,
            lambda x: f"id={id(x)}",
            "val",
            next=("val",)
        )

    输出：
        <Node id=...> {
            val: 1
            next: <Node> { val: 2 }
        }

    ----------------------------------------
    🚀 设计目标
    ----------------------------------------

    - 统一 repr 格式
    - 替代手写 __repr__
    - 支持复杂结构调试（链表 / 树 / 图）
    - 可作为轻量 DSL 描述对象结构
    - 对 Cython / PyObject* 友好（无反射依赖）

    ----------------------------------------
    ⚠️ 注意事项
    ----------------------------------------

    - tuple 最后一项若为 dict，会作为子 kwargs
    - callable 若在最前，会作为 header 注释
    - 不要传入非法类型（否则抛 ValueError / TypeError）

    ----------------------------------------
    """
    if obj is None:
        return "None"

    # ===== 内部缩进工具 =====
    def __fmt_indent_lines(__fmt_text, __fmt_level):
        __fmt_prefix = "\t" * __fmt_level
        return "\n".join(
            (__fmt_prefix + line) if line else line
            for line in __fmt_text.split("\n")
        )

    # ===== 内部递归核心 =====
    def __fmt_core(__fmt_obj, __fmt_level, __fmt_args, __fmt_kwargs):
        if __fmt_obj is None:
            return "None"

        __fmt_lines = []
        __fmt_notes = []
        __fmt_prefix_all_call = True

        # ========================
        # 处理 dict（fields）
        # ========================
        def __fmt_handle_dict(__fmt_dict):
            for __fmt_key, __fmt_prop in __fmt_dict.items():
                try:
                    __fmt_child = getattr(__fmt_obj, __fmt_key)
                except Exception as __fmt_e:
                    __fmt_lines.append(f"{__fmt_key}: <error {type(__fmt_e).__name__}>")
                    continue

                # ---- tuple: 递归 ----
                if isinstance(__fmt_prop, tuple) and __fmt_prop:
                    if isinstance(__fmt_prop[-1], dict):
                        __fmt_sub_kwargs = __fmt_prop[-1]
                        __fmt_end = len(__fmt_prop) - 1
                    else:
                        __fmt_sub_kwargs = {}
                        __fmt_end = len(__fmt_prop)

                    __fmt_sub_args = __fmt_prop[:__fmt_end]

                    __fmt_res = __fmt_core(
                        __fmt_child,
                        __fmt_level + 1,
                        __fmt_sub_args,
                        __fmt_sub_kwargs
                    )

                    if "\n" in __fmt_res:
                        __fmt_lines.append(f"{__fmt_key}:")
                        __fmt_lines.append(__fmt_res)
                    else:
                        __fmt_lines.append(f"{__fmt_key}: {__fmt_res}")

                # ---- callable ----
                elif callable(__fmt_prop):
                    __fmt_val = _safe_call(__fmt_prop, __fmt_child)
                    __fmt_lines.append(f"{__fmt_key}: {__fmt_val}")

                # ---- str ----
                elif isinstance(__fmt_prop, str):
                    __fmt_lines.append(f"{__fmt_key}: {__fmt_prop}")

                # ---- None ----
                elif __fmt_prop is None:
                    __fmt_lines.append(f"{__fmt_key}: None")

                else:
                    raise TypeError(
                        f"{__fmt_obj.__class__.__name__}._format_repr: invalid field '{__fmt_key}'"
                    )

        # ========================
        # 处理 args
        # ========================
        for __fmt_arg in __fmt_args:
            if isinstance(__fmt_arg, str):
                __fmt_prefix_all_call = False
                try:
                    __fmt_val = getattr(__fmt_obj, __fmt_arg)
                    __fmt_lines.append(f"{__fmt_arg}: {_formated_string(__fmt_val)}")
                except Exception as __fmt_e:
                    __fmt_lines.append(f"{__fmt_arg}: <error {type(__fmt_e).__name__}>")

            elif callable(__fmt_arg):
                if __fmt_prefix_all_call:
                    __fmt_notes.append(_safe_call(__fmt_arg, __fmt_obj))
                else:
                    __fmt_lines.append(_safe_call(__fmt_arg, __fmt_obj))

            elif isinstance(__fmt_arg, dict):
                __fmt_prefix_all_call = False
                __fmt_handle_dict(__fmt_arg)

            else:
                raise ValueError(f"Invalid arg type: {type(__fmt_arg)}")

        # kwargs（fields）
        __fmt_handle_dict(__fmt_kwargs)

        # ========================
        # header
        # ========================
        __fmt_note_str = ""
        if __fmt_notes:
            __fmt_note_str = " " + ", ".join(map(str, __fmt_notes))

        __fmt_header = f"<{__fmt_obj.__class__.__name__}{__fmt_note_str}>"

        # ========================
        # 无 body
        # ========================
        if not __fmt_lines:
            return __fmt_header

        # ========================
        # 单行尝试
        # ========================
        __fmt_inline_body = ", ".join(__fmt_lines)
        __fmt_inline_repr = f"{__fmt_header} {{ {__fmt_inline_body} }}"

        if len(__fmt_inline_repr) <= _MAX_LEN_A_LINE:
            return __fmt_inline_repr

        # ========================
        # 多行结构化输出
        # ========================
        __fmt_body_lines = []

        for __fmt_line in __fmt_lines:
            if "\n" in __fmt_line:
                # 子结构，整体缩进
                __fmt_body_lines.append(
                    __fmt_indent_lines(__fmt_line, __fmt_level + 1)
                )
            else:
                __fmt_body_lines.append(
                    ("\t" * (__fmt_level + 1)) + __fmt_line
                )

        __fmt_body = "\n".join(__fmt_body_lines)

        return (
            f"{__fmt_header} {{\n"
            f"{__fmt_body}\n"
            f"{'\t' * __fmt_level}"
            f"}}"
        )

    # ===== 启动递归 =====
    return __fmt_core(obj, 0, args, kwargs)

if __name__ == "__main__":
    # =========================
    # 测试类定义
    # =========================

    class Node:
        def __init__(self, val, next=None):
            self.val = val
            self.next = next

    class Tree:
        def __init__(self, val, left=None, right=None):
            self.val = val
            self.left = left
            self.right = right

    class Weird:
        def __init__(self):
            self.ok = 123

        @property
        def bad(self):
            raise RuntimeError("boom")


    # =========================
    # 构造数据
    # =========================

    # 链表：1 -> 2 -> 3
    l3 = Node(3)
    l2 = Node(2, l3)
    l1 = Node(1, l2)

    # 树：
    #       1
    #     /   \
    #    2     3
    t = Tree(1, Tree(2), Tree(3))

    # 深层嵌套
    deep = Tree(10,
                Tree(20, Tree(30)),
                Tree(40, None, Tree(50)))

    w = Weird()


    # =========================
    # 测试1：基础属性
    # =========================
    print(_format_repr(l1, "val"))

    # =========================
    # 测试2：callable
    # =========================
    print(_format_repr(l1, lambda x: f"val*2={x.val*2}", "val"))

    # =========================
    # 测试3：嵌套 tuple
    # =========================
    print(_format_repr(
        l1,
        "val",
        next=("val",)
    ))

    # =========================
    # 测试4：深层递归
    # =========================
    print(_format_repr(
        t,
        "val",
        left=("val",),
        right=("val",)
    ))

    # =========================
    # 测试5：dict 配置
    # =========================
    print(_format_repr(
        t,
        {
            "val": lambda x: x,
            "left": ("val",),
            "right": ("val",)
        }
    ))

    # =========================
    # 测试6：混合 callable + dict
    # =========================
    print(_format_repr(
        t,
        lambda x: f"id={id(x)}",
        {
            "val": lambda x: x,
            "left": ("val",),
            "right": ("val",)
        }
    ))

    # =========================
    # 测试7：异常属性
    # =========================
    print(_format_repr(w, "ok", "bad"))

    # =========================
    # 测试8：深层复杂结构
    # =========================
    print(_format_repr(
        deep,
        lambda x: "root",
        {
            "val": lambda x: x,
            "left": (
                lambda x: "L",
                {
                    "val": lambda x: x,
                    "left": ("val",),
                    "right": ("val",)
                }
            ),
            "right": (
                lambda x: "R",
                {
                    "val": lambda x: x,
                    "right": ("val",)
                }
            )
        }
    ))