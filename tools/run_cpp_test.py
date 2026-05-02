import subprocess
import json
import os
from pathlib import Path
import threading
import queue

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

        # 用队列接收输出
        self.q = queue.Queue()

        def _reader():
            while True:
                line = self.proc.stdout.readline()
                if not line:
                    break
                self.q.put(line)

        def _reader_err():
            while True:
                line = self.proc.stderr.readline()
                if not line:
                    break
                print("C++ ERR:", line.strip())

        self.t = threading.Thread(target=_reader, daemon=True)
        self.t.start()
        
        threading.Thread(target=_reader_err, daemon=True).start()

    def run_case(self, input_data, timeout=2):
        # 发送
        line = json.dumps({"input": input_data})
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

        try:
            out = self.q.get(timeout=timeout)
        except queue.Empty:
            raise RuntimeError("❌ C++ 超时无响应")

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


$inc = (python -m pybind11 --includes) -split " "
$inc = $inc | ForEach-Object { $_ -replace "-I", "/I" }

$py_inc = python -c "import sysconfig; print(sysconfig.get_paths()['include'])"
$py_lib = python -c "import sysconfig; print(sysconfig.get_config_var('LIBDIR'))"

cl /O2 /EHsc /LD tools/solution.cpp `
    $inc `
    /I"$py_inc" `
    /link /LIBPATH:"$py_lib" python314.lib /OUT:solution_cpp.pyd