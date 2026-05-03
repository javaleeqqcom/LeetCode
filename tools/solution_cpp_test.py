import importlib
import inspect
import subprocess
import sys
from pathlib import Path
import sysconfig, subprocess

def compile_cpp(question_path: Path, bind_method):
    include_dirs = [
        question_path,
    ]
    include_flags = [f"/I{p.resolve()}" for p in include_dirs if p.exists()]

    print("🔧 编译 C++ (MSVC)...")

    ext_suffix = sysconfig.get_config_var('EXT_SUFFIX')
    out_file = Path("tools") / f"solution_cpp{ext_suffix}"
    out_file = out_file.resolve()

    inc = subprocess.getoutput("python -m pybind11 --includes")
    inc = [i.replace("-I", "/I") for i in inc.split()]

    py_inc = sysconfig.get_paths()['include']
    py_lib = sysconfig.get_config_var('LIBDIR')
    py_ver = sysconfig.get_python_version().replace(".", "")
    py_lib_name = f"python{py_ver}.lib"


    cmd = [
        "cl",
        "/O2", "/EHsc", "/LD",
        "tools/solution_cpp.cpp",
        f"/D_BIND_METHOD_={bind_method}",  # 👈 注入宏定义
        *include_flags,
        *inc,
        f"/I{py_inc}",
        "/link",
        f"/LIBPATH:{py_lib}",
        py_lib_name,
        f"/OUT:{out_file}"
    ]

    print("CMD:", " ".join(cmd))

    result = subprocess.run(cmd, capture_output=True, text=True)

    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("❌ 编译失败")

    # 🔍 查找所有生成文件
    print("📂 tools目录:")
    for f in Path("tools").glob("*solution_cpp*"):
        print("  ", f)

    if not out_file.exists():
        raise RuntimeError(f"❌ 未找到目标文件: {out_file}")

    print(f"✅ 编译成功: {out_file}")

def load_solution():
    import sys
    sys.path.insert(0, "tools")   # 👈 加这个
    return importlib.import_module("solution_cpp")

def get_main_method(obj):
    methods = [
        name for name, func in inspect.getmembers(obj, predicate=callable)
        if not name.startswith("__")
    ]
    if len(methods) != 1:
        raise ValueError(f"C++ Solution 必须只有一个 public 方法，但实际为：\n{methods}")
    return methods[0]

def run_case(obj, method_name, case):
    method = getattr(obj, method_name)
    return method(*case) if isinstance(case, tuple) else method(case)

def main():
    compile_cpp(Path("Question/396. Rotate Function"),"maxRotateFunction")

    mod = load_solution()
    obj = mod.Solution()

    method_name = get_main_method(obj)

    test_cases = [
        ([4,3,2,6],),
        ([1,2,3,4],),
        ([100],)
    ]

    for case in test_cases:
        res = run_case(obj, method_name, case)
        print(case, "→", res)

if __name__ == "__main__":
    main()