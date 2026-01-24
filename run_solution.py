import sys
import os
import importlib.util
from datetime import datetime
from typing import Any, List, Dict
from io import StringIO
from custom_init import *

def parse_input_file(filepath: str) -> tuple[bool, AnyClass]:
    """解析输入文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [line.rstrip() for line in f if line.strip()]

    # 关键！需要重构的地方！


def capture_print_and_result(func, *args, **kwargs):
    """捕获 print 输出和函数返回值"""
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
    if len(sys.argv) != 4:
        print("Usage: python run_solution.py <solution_file.py> <input_file.txt> <method_name>")
        sys.exit(1)

    solution_file = sys.argv[1]
    method_name = sys.argv[2]
    input_file = sys.argv[3]

    if not os.path.isfile(solution_file):
        raise FileNotFoundError(f"Solution file not found: {solution_file}")
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # ✅ 安全加载模块
    try:
        spec = importlib.util.spec_from_file_location("solution_module", solution_file)
        if spec is None:
            raise ImportError(f"Cannot create ModuleSpec from {solution_file}")
        
        module = importlib.util.module_from_spec(spec)
        if module is None:
            raise ImportError("Failed to create module from spec")

        # 执行模块
        if spec.loader is None:
            raise ImportError("Module loader is None")
        spec.loader.exec_module(module)

    except Exception as e:
        raise ImportError(f"Failed to load solution module: {e}")

    if not hasattr(module, 'Solution'):
        raise AttributeError("The solution file must define a class named 'Solution'.")

    obj = module.Solution()

    if not hasattr(obj, method_name):
        raise AttributeError(f"Method '{method_name}' not found in Solution class.")

    func = getattr(obj, method_name)

    # 解析输入
    is_named, data = parse_input_file(input_file)

    # 调用函数
    if is_named:
        printed, result = capture_print_and_result(func, **data)
    else:
        printed, result = capture_print_and_result(func, *data)

    # 生成日志文件名
    base_name = os.path.splitext(os.path.basename(solution_file))[0]
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_filename = f"{base_name}_{timestamp}.log"

    # 写入日志
    with open(log_filename, 'w', encoding='utf-8') as logf:
        if printed:
            logf.write("=== Captured print() output ===\n")
            logf.write(printed)
            logf.write("\n")
        logf.write("=== Final return value ===\n")
        logf.write(str(result))
        logf.write("\n")

    print(f"✅ Execution completed. Output saved to: {log_filename}")
    print(f"Return value: {result}")


if __name__ == "__main__":
    main()