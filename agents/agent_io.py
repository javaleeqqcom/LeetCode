# agents/agent_io.py
from pathlib import Path
from typing import List, Optional, Dict, Set, Tuple
from langchain_core.messages import BaseMessage
import ast
import re
import sys
import subprocess
import base64

class AgentIO:

    SAFE_GENERATOR_IMPORTS = {
        "bisect", "collections", "functools", "heapq", "itertools",
        "json", "math", "numpy", "random", "statistics", "string", "typing",
    }
    BLOCKED_GENERATOR_CALLS = {
        "breakpoint", "compile", "eval", "exec", "input", "open", "__import__",
    }

    # ========== 基础工具（原有） ==========
    @classmethod
    def get_auto_dir(cls, problem_dir: Path) -> Path:
        path = problem_dir / "auto"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def get_log_dir(cls, problem_dir: Path) -> Path:
        path = problem_dir / "agent_logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def next_index(cls, problem_dir: Path, prefix="case_generator_") -> int:
        auto_dir = cls.get_auto_dir(problem_dir)
        max_id = -1
        for f in auto_dir.glob(f"{prefix}*.py"):
            m = re.match(rf"{prefix}(\d+)\.py", f.name)
            if m:
                max_id = max(max_id, int(m.group(1)))
        return max_id + 1

    @classmethod
    def clean_llm_code(cls, text: str) -> str:
        # 部分本地模型会偶发返回孤立 UTF-16 surrogate；它能通过 ast.parse，
        # 但在保存或送入独立解释器时触发 UnicodeEncodeError。
        text = text.encode("utf-8", errors="replace").decode("utf-8").strip()
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S) # 去除思考过程
        m = re.search(r"```(?:python)?\s*(.*?)\s*```", text, flags=re.S) # 提取Python代码框内部
        if m:
            return m.group(1).strip()
        pos = text.find("def ")
        if pos >= 0:
            return text[pos:]
        return text

    # ========== 剪贴板支持（保留） ==========
    @staticmethod
    def copy_to_clipboard(text: str) -> bool:
        """跨平台复制到剪贴板，成功返回 True，失败返回 False"""
        try:
            if sys.platform == "win32":
                subprocess.run(['clip'], input=text.encode('utf-16-le'), check=True)
            elif sys.platform == "darwin":
                subprocess.run(['pbcopy'], input=text.encode('utf-8'), check=True)
            else:
                tool = 'xclip' if subprocess.run(['which', 'xclip'], capture_output=True).returncode == 0 else 'xsel'
                args = [tool, '-selection', 'clipboard'] if tool == 'xclip' else [tool, '--clipboard', '--input']
                subprocess.run(args, input=text.encode('utf-8'), check=True)
            return True
        except Exception as e:
            print(f"复制到剪贴板失败: {e}")
            return False
        
    @staticmethod
    def send_messages_to_clipboard(messages: List[BaseMessage], problem_dir: Path) -> bool:
        """
        将消息列表序列化为文本并复制到剪贴板。
        若复制失败，则自动保存到日志文件并返回 False。
        """
        text = "\n\n".join(str(m.content) for m in messages)
        if AgentIO.copy_to_clipboard(text):
            return True
        # 复制失败时写入临时日志
        log_dir = AgentIO.get_log_dir(problem_dir)
        log_path = log_dir / f"manual_prompt_{Path(problem_dir).name}.log"
        log_path.write_text(text, encoding="utf-8")
        print(f"剪贴板操作失败，已将 Prompt 保存至: {log_path}")
        return False
    
    # ========== 新增：剪贴板读取（无损处理各种平台编码） ==========
    @staticmethod
    def paste_from_clipboard() -> str:
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        "Get-Clipboard"
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace"
                )

                return result.stdout.strip()

            elif sys.platform == "darwin":
                # macOS 使用 pbpaste，系统默认采用 utf-8 编码
                result = subprocess.run(
                    ["pbpaste"],
                    capture_output=True,
                    text=True
                )
                return result.stdout

            else:
                # Linux 自动检测 xclip 或 xsel
                is_xclip = subprocess.run(['which', 'xclip'], capture_output=True).returncode == 0
                if is_xclip:
                    args = ['xclip', '-selection', 'clipboard', '-o']
                else:
                    args = ['xsel', '--clipboard', '--output']
                
                result = subprocess.run(args, capture_output=True, check=True)
                return result.stdout.decode('utf-8')
        except Exception as e:
            print(f"从剪贴板读取失败: {e}")
            return ""
    
    # ========== 新增：Import 自动修复 ==========
    # 符号 → 模块路径（空元组表示 import 模块本身）
    IMPORT_SYMBOLS = {
        # 标准库模块
        "random": (),
        "math": (),
        "heapq": (),
        "bisect": (),
        "itertools": (),
        "collections": (),
        "functools": (),
        "typing": (),
        # 三方库
        "numpy": (),
        # typing 常见导出
        "List": ("typing",),
        "Dict": ("typing",),
        "Tuple": ("typing",),
        "Set": ("typing",),
        "Optional": ("typing",),
        "Union": ("typing",),
        "Any": ("typing",),
        # collections 导出
        "Counter": ("collections",),
        "defaultdict": ("collections",),
        "deque": ("collections",),
        "OrderedDict": ("collections",),
        # functools 导出
        "lru_cache": ("functools",),
        "cache": ("functools",),
        # itertools 导出
        "product": ("itertools",),
        "combinations": ("itertools",),
        "permutations": ("itertools",),
        "accumulate": ("itertools",),
        # 其他常见库可继续扩展...
    }

    # 别名 → 实际模块名
    ALIASES = {
        "np": "numpy",
        "pd": "pandas",
    } # 待改进：将来采用 RAG 匹配最可能的别名->实际模块的映射

    @classmethod
    def auto_fix_imports(cls, code: str) -> str:
        """
        分析代码 AST，自动补齐缺失的 import 语句。
        规则：
        - 收集已导入名称（含别名）和所有用到的名称（Name节点 + Attribute最左名称）
        - 对照 IMPORT_SYMBOLS 与 ALIASES 找出缺失项
        - 合并同源 from 导入，添加 import / import ... as ... 语句
        - 保留 shebang 和编码声明行
        - 若代码存在语法错误，直接返回原代码
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code

        # 1. 收集已导入名称
        imported_names: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    imported_names.add(name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imported_names.add(name)

        # 2. 收集所有用到的名称
        used_names: Set[str] = set()

        class NameCollector(ast.NodeVisitor):
            def visit_Name(self, node):
                used_names.add(node.id)
                self.generic_visit(node)

            def visit_Attribute(self, node):
                # 递归获取最左侧 Name
                left = node
                while isinstance(left, ast.Attribute):
                    left = left.value
                if isinstance(left, ast.Name):
                    used_names.add(left.id)
                self.generic_visit(node)

        NameCollector().visit(tree)

        # 3. 确定需要补的导入
        # 结构：from_imports: dict[module_path, set[name]]
        from_imports: Dict[tuple, Set[str]] = {}
        normal_imports: List[str] = []      # 普通 import 或 import as

        for name in sorted(used_names):
            if name in imported_names:
                continue

            # 处理别名
            if name in cls.ALIASES:
                actual_module = cls.ALIASES[name]
                # 检查 actual_module 或 name 是否已导入
                if actual_module not in imported_names and name not in imported_names:
                    normal_imports.append(f"import {actual_module} as {name}")
                continue

            # 处理普通符号
            if name not in cls.IMPORT_SYMBOLS:
                continue

            path_tuple = cls.IMPORT_SYMBOLS[name]
            if not path_tuple:
                # import 模块本身
                if name not in imported_names:
                    normal_imports.append(f"import {name}")
            else:
                # from 导入
                if name not in imported_names:
                    from_imports.setdefault(path_tuple, set()).add(name)

        # 4. 生成补齐文本
        lines = []
        for path_tuple, names in from_imports.items():
            module_path = ".".join(path_tuple)
            names_str = ", ".join(sorted(names))
            lines.append(f"from {module_path} import {names_str}")
        for imp in sorted(normal_imports):
            lines.append(imp)

        if not lines:
            return code

        prepend = "\n".join(lines) + "\n"

        # 5. 插入到文件头，保留 shebang / coding
        code_lines = code.splitlines(True)
        insert_idx = 0
        if code_lines and code_lines[0].startswith("#!"):
            insert_idx = 1
        if len(code_lines) > insert_idx and code_lines[insert_idx].startswith("#") and "coding" in code_lines[insert_idx]:
            insert_idx += 1

        return "".join(code_lines[:insert_idx]) + prepend + "".join(code_lines[insert_idx:])

    # ========== 新增：沙箱验证 case_generator ==========
    @classmethod
    def validate_case_generator(cls, code: str) -> Tuple[bool, str]:
        """
        在安全命名空间中执行代码，并调用 case_generator(10) 验证：
        - 能成功执行
        - 返回值为 dict
        - 包含 "input" 键
        - 没有抛出异常
        返回 (是否通过, 错误信息)
        """
        try:
            tree = ast.parse(code, filename="<agent_fix>", mode="exec")
        except Exception as e:
            return False, f"语法错误: {e}"

        definitions = {
            node.name for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        if "case_generator" not in definitions:
            return False, "未定义 case_generator 函数"

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".", 1)[0] for alias in node.names}
                disallowed = roots - cls.SAFE_GENERATOR_IMPORTS
                if disallowed:
                    return False, f"不允许导入模块: {sorted(disallowed)}"
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".", 1)[0]
                if root not in cls.SAFE_GENERATOR_IMPORTS:
                    return False, f"不允许导入模块: {root or '<relative>'}"
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in cls.BLOCKED_GENERATOR_CALLS
            ):
                return False, f"不允许调用: {node.func.id}"
            elif (
                isinstance(node, ast.If)
                and isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name)
                and node.test.left.id == "__name__"
            ):
                return False, "禁止生成 main/__name__ 执行入口"
            elif (
                isinstance(node, ast.While)
                and isinstance(node.test, ast.Constant)
                and node.test.value is True
            ):
                return False, "禁止 while True 无界拒绝采样；请直接构造合法样例"

        # 在独立解释器中执行，设置硬超时；生成代码不会污染 Agent 主进程。
        validator = r'''
import base64
import json
import sys

code = base64.b64decode(sys.stdin.buffer.read()).decode("utf-8")
namespace = {"__builtins__": __builtins__}
exec(compile(code, "<case_generator>", "exec"), namespace)
generator = namespace["case_generator"]
for scale in (0, 1, 1.5, 10.5, 100, 1000):
    result = generator(scale)
    if not isinstance(result, dict):
        raise TypeError(f"scale={scale}: expected dict, got {type(result).__name__}")
    if "input" not in result:
        raise ValueError(f"scale={scale}: missing input")
    reserved = {"output", "error", "traceback", "elapsed", "cid"} & result.keys()
    if reserved:
        raise ValueError(f"scale={scale}: reserved keys are not allowed: {sorted(reserved)}")
    if not isinstance(result["input"], (tuple, list, dict)):
        raise TypeError(f"scale={scale}: input must be tuple/list/dict")
    json.dumps(result, ensure_ascii=False)
print("CASE_GENERATOR_VALID")
'''
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            completed = subprocess.run(
                [sys.executable, "-I", "-c", validator],
                input=base64.b64encode(code.encode("utf-8")),
                capture_output=True,
                timeout=5,
                creationflags=creation_flags,
            )
        except subprocess.TimeoutExpired:
            return False, "生成器验证超过 5 秒，可能存在死循环或不合理开销"
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).decode(
                "utf-8", errors="replace"
            ).strip()
            return False, f"隔离执行失败: {detail[-1000:]}"
        if b"CASE_GENERATOR_VALID" not in completed.stdout:
            return False, "隔离执行未返回成功标记"
        return True, ""
