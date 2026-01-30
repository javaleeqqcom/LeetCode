# solution_runner.py
import os,sys
from datetime import datetime
from io import StringIO
from typing import Type, Any, Dict, List, get_origin, get_args, Union, Optional
import inspect
import ast


def load_parser_registry():
    """从 base_init 和 custom_init 加载解析器"""
    registry = {}
    try:
        from base_init import base_input_parser_registry
        registry.update(base_input_parser_registry)
    except ImportError:
        pass

    try:
        from custom_init import input_parser_registry
        registry.update(input_parser_registry)
    except ImportError:
        pass

    return registry


def get_parser_key(annotation) -> tuple[str, ...]:
    if annotation is inspect.Parameter.empty:
        return ("str",)

    if isinstance(annotation, str):
        s = annotation.strip()
        if s.startswith("Optional[") and s.endswith("]"):
            s = s[9:-1].strip()
        elif s.startswith("Union[") and s.endswith("]"):
            parts = [p.strip() for p in s[6:-1].split(",")]
            non_none = [p for p in parts if p not in ("None", "type(None)")]
            if len(non_none) == 1:
                s = non_none[0]
        s = s.split(".")[-1]
        if "[" in s and "]" in s:
            s = s.split("[")[0]
        return (s,)

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Union:
        non_none = [arg for arg in args if arg is not type(None)]
        if len(non_none) == 1:
            return get_parser_key(non_none[0])
    
    if origin in (list, List):
        return ("list",)
    if origin in (dict, Dict):
        return ("dict",)

    if isinstance(annotation, type):
        return (annotation.__name__,)

    return (str(annotation),)


def parse_input_file(filepath: str, param_names: List[str]) -> Dict[str, str]:
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [line.rstrip() for line in f]

    if not lines:
        raise ValueError("Input file is empty.")

    has_eq = any('=' in line for line in lines if line.strip())

    if not has_eq:
        non_empty = [line for line in lines if line.strip()]
        if len(non_empty) != len(param_names):
            raise ValueError(f"Positional lines ({len(non_empty)}) != params ({len(param_names)})")
        return {name: line.strip() for name, line in zip(param_names, non_empty)}

    # 支持多行赋值
    data = {}
    current_key = None
    current_lines = []

    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            continue
        if '=' in stripped:
            if current_key is not None:
                data[current_key] = '\n'.join(current_lines).strip()
            key_part, val_part = stripped.split('=', 1)
            current_key = key_part.strip()
            current_lines = [val_part]
        else:
            if current_key is None:
                raise ValueError(f"Line before assignment: {stripped}")
            current_lines.append(stripped)

    if current_key is not None:
        data[current_key] = '\n'.join(current_lines).strip()

    return data


def capture_print_and_result(func, *args, **kwargs):
    old_stdout = sys.stdout
    captured = StringIO()
    sys.stdout = captured
    try:
        result = func(*args, **kwargs)
    finally:
        sys.stdout = old_stdout
    return captured.getvalue(), result


def run_solution_from_file(SolutionClass: Type[Any], input_file: str, method_name: str = None):
    """
    评测入口函数
    :param SolutionClass: 学生定义的 Solution 类
    :param input_file: 输入文件路径
    :param method_name: 可选，方法名
    """
    import sys
    from io import StringIO

    # 获取方法
    methods = [name for name, _ in inspect.getmembers(SolutionClass, predicate=inspect.isfunction)
               if not name.startswith('_') and name != '__init__']

    if method_name is None:
        if len(methods) == 1:
            method_name = methods[0]
        else:
            raise ValueError(f"Please specify method_name. Candidates: {methods}")

    if not hasattr(SolutionClass, method_name):
        raise AttributeError(f"Method '{method_name}' not found.")

    func = getattr(SolutionClass, method_name)
    sig = inspect.signature(func)
    param_names = [name for name in sig.parameters.keys() if name != 'self']
    params = {name: sig.parameters[name] for name in param_names}

    # 解析输入
    raw_inputs = parse_input_file(input_file, param_names)
    parser_registry = load_parser_registry()

    converted = {}
    for name in param_names:
        if name not in raw_inputs:
            raise ValueError(f"Missing parameter: {name}")
        raw_str = raw_inputs[name]
        param = params[name]
        key = get_parser_key(param.annotation)

        if key in parser_registry:
            converter = parser_registry[key]
            converted[name] = converter([raw_str])
        else:
            # fallback to literal_eval
            converted[name] = ast.literal_eval(raw_str)

    # 执行
    obj = SolutionClass()
    printed, result = capture_print_and_result(func, obj, **converted)

    # 输出
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_filename = f"{base_name}_{timestamp}.log"

    with open(log_filename, 'w', encoding='utf-8') as f:
        if printed:
            f.write("=== Captured print() output ===\n")
            f.write(printed)
            f.write("\n")
        f.write("=== Final return value ===\n")
        f.write(str(result))
        f.write("\n")

    print(f"✅ Output saved to: {log_filename}")
    print(f"Return: {result}")
    return result