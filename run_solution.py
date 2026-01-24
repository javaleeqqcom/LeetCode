import sys
import os
import importlib.util
import inspect
from datetime import datetime
from io import StringIO
from typing import get_origin, get_args, Union, Optional, Any


def load_parser_registry():
    """加载 base_init 和 custom_init 中的解析器注册表"""
    registry = {}

    # 加载 base_init.py
    base_spec = importlib.util.spec_from_file_location("base_init", "base_init.py")
    if base_spec and base_spec.loader:
        base_mod = importlib.util.module_from_spec(base_spec)
        base_spec.loader.exec_module(base_mod)
        if hasattr(base_mod, 'base_input_parser_registry'):
            registry.update(base_mod.base_input_parser_registry)

    # 加载 custom_init.py
    custom_spec = importlib.util.spec_from_file_location("custom_init", "custom_init.py")
    if custom_spec and custom_spec.loader:
        custom_mod = importlib.util.module_from_spec(custom_spec)
        custom_spec.loader.exec_module(custom_mod)
        if hasattr(custom_mod, 'input_parser_registry'):
            registry.update(custom_mod.input_parser_registry)

    return registry


def get_parser_key(annotation) -> tuple[str, ...]:
    # （此处插入上面定义的 get_parser_key 函数）
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


def parse_input_file(filepath: str, param_names: list[str]) -> dict[str, str]:
    """读取输入文件，返回 {param_name: raw_string}"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [line.rstrip() for line in f if line.strip()]

    if not lines:
        raise ValueError("Input file is empty.")

    has_eq = any('=' in line for line in lines)

    raw_data = {}
    if has_eq:
        for line in lines:
            if '=' not in line:
                raise ValueError(f"Line missing '=': {line}")
            key, val = line.split('=', 1)
            raw_data[key.strip()] = val.strip()
    else:
        if len(lines) != len(param_names):
            raise ValueError(f"Positional input lines ({len(lines)}) != parameters ({len(param_names)})")
        for name, line in zip(param_names, lines):
            raw_data[name] = line.strip()

    return raw_data


def find_candidate_method(cls):
    methods = []
    for name, _ in inspect.getmembers(cls, predicate=inspect.isfunction):
        if not name.startswith('__') or name in ('__init__', '__call__'):
            continue
        methods.append(name)
    if len(methods) == 1:
        return methods[0]
    elif len(methods) == 0:
        raise AttributeError("No public method found in Solution class.")
    else:
        raise AttributeError(f"Multiple public methods: {methods}. Please specify one.")


def capture_print_and_result(func, *args, **kwargs):
    old_stdout = sys.stdout
    captured_output = StringIO()
    sys.stdout = captured_output
    try:
        result = func(*args, **kwargs)
    finally:
        sys.stdout = old_stdout
    printed = captured_output.getvalue()
    return printed, result


def main():
    if len(sys.argv) < 3:
        print("Usage: python run_solution.py <solution.py> <input.txt> [method_name]")
        sys.exit(1)

    solution_file = sys.argv[1]
    input_file = sys.argv[2]
    method_name = sys.argv[3] if len(sys.argv) > 3 else None

    # 加载解析器
    parser_registry = load_parser_registry()

    # 加载学生 solution
    spec = importlib.util.spec_from_file_location("solution", solution_file)
    if not spec or not spec.loader:
        raise ImportError(f"Cannot load {solution_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, 'Solution'):
        raise AttributeError("Missing 'Solution' class.")

    SolutionClass = module.Solution

    # 推断或获取方法名
    if method_name is None:
        method_name = find_candidate_method(SolutionClass)

    func = getattr(SolutionClass, method_name)
    sig = inspect.signature(func)

    # 获取参数名（跳过 self）
    param_names = [name for name in sig.parameters.keys() if name != 'self']
    params = {name: sig.parameters[name] for name in param_names}

    # 读取原始输入
    raw_inputs = parse_input_file(input_file, param_names)

    # 转换每个参数
    converted_args = {}
    for name in param_names:
        if name not in raw_inputs:
            raise ValueError(f"Missing parameter: {name}")
        raw_str = raw_inputs[name]
        param = params[name]
        key = get_parser_key(param.annotation)

        # 查找匹配的解析器
        if key in parser_registry:
            converter = parser_registry[key]
            try:
                converted_args[name] = converter([raw_str])
            except Exception as e:
                raise ValueError(f"Failed to parse '{name}' with key {key}: {e}")
        else:
            # 无匹配解析器，尝试 literal_eval
            import ast
            try:
                converted_args[name] = ast.literal_eval(raw_str)
            except Exception as e:
                raise ValueError(f"No parser for {key}, and literal_eval failed on '{raw_str}': {e}")

    # 执行
    obj = SolutionClass()
    printed, result = capture_print_and_result(func, obj, **converted_args)

    # 输出日志
    base_name = os.path.splitext(os.path.basename(solution_file))[0]
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


if __name__ == "__main__":
    main()