import subprocess
import json
import os
from pathlib import Path

# ========= 配置 =========
CPP_FILE = "tools/solution.cpp"
EXE_FILE = "tools/solution.exe"

# 👉 头文件目录（关键）
INCLUDE_DIR = "396. Rotate Function"

# =======================
import select

def safe_readline(pipe, timeout=2):
    rlist, _, _ = select.select([pipe], [], [], timeout)
    if rlist:
        return pipe.readline()
    else:
        raise RuntimeError("❌ C++ 超时无响应")

def compile_cpp():
    print("🔧 编译 C++ ...")

    cmd = [
        "cl",
        "/EHsc",
        "/O2",
        "/utf-8",
        CPP_FILE,
        f'/I"{INCLUDE_DIR}"',   # 👈 关键：指定 include 路径
        f"/Fe:{EXE_FILE}"
    ]

    # Windows shell=True 才能正确解析 cl
    result = subprocess.run(
        " ".join(cmd),
        shell=True,
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("❌ 编译失败")

    print("✅ 编译成功")


class CppProcess:
    def __init__(self, exe_path):
        self.proc = subprocess.Popen(
            exe_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

    def run_case(self, input_data):
        # 发送 JSON
        line = json.dumps({"input": input_data})
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

        # 读取返回
        out = safe_readline(self.proc.stdout)
        if not out:
            raise RuntimeError("❌ C++ 无输出")

        result = json.loads(out)

        if "error" in result:
            raise RuntimeError(result["error"])

        return result["output"]

    def close(self):
        try:
            self.proc.stdin.write('{"cmd":"exit"}\n')
            self.proc.stdin.flush()
        except:
            pass
        self.proc.terminate()


def main():
    compile_cpp()

    print("🚀 启动 C++ 进程")
    cpp = CppProcess(EXE_FILE)

    # ===== 测试 =====
    test_cases = [
        [4, 3, 2, 6],
        [1, 2, 3, 4, 5],
        [100]
    ]

    for case in test_cases:
        res = cpp.run_case(case)
        print(f"input={case} → output={res}")

    cpp.close()


if __name__ == "__main__":
    main()