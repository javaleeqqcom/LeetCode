from __future__ import annotations

import functools
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .auto_tune import (
    AutoTuneConfig,
    AutoTuneDecision,
    AutoTuneProbe,
    create_probe_store,
    inspect_program,
    inspect_store,
    inspect_system,
    select_workers,
)
from .case_store import CaseStoreReader
from .common import digest_value
from .models import RunMetrics, RunReport
from .native_process import DEFAULT_MANAGER, ROOT
from .persistent_python import MAX_WORKERS


NATIVE_INCLUDE = ROOT / "native_runner" / "include"
WORKER_RUNTIME_HEADER = NATIVE_INCLUDE / "oj_cpp_worker_runtime.hpp"
JSON_HEADER = NATIVE_INCLUDE / "nlohmann" / "json.hpp"
MANAGER_SOURCE = ROOT / "native_runner" / "src" / "process_manager.cpp"
HARNESS_VERSION = "cpp-standard-v1"
CPP_EXTENSIONS = frozenset({".cpp", ".cc", ".cxx", ".c++"})
_PRIMITIVE_TYPES = {
    "int": "int",
    "long": "long",
    "long long": "long long",
    "unsigned": "unsigned int",
    "unsigned int": "unsigned int",
    "unsigned long": "unsigned long",
    "unsigned long long": "unsigned long long",
    "float": "float",
    "double": "double",
    "bool": "bool",
    "string": "std::string",
    "std::string": "std::string",
    "int32_t": "std::int32_t",
    "uint32_t": "std::uint32_t",
    "int64_t": "std::int64_t",
    "uint64_t": "std::uint64_t",
    "std::int32_t": "std::int32_t",
    "std::uint32_t": "std::uint32_t",
    "std::int64_t": "std::int64_t",
    "std::uint64_t": "std::uint64_t",
}


class CppSourceError(ValueError):
    """The source is outside the supported LeetCode C++ standard subset."""


class CppCompilationError(RuntimeError):
    """The configured C++ compiler rejected the generated worker."""


@dataclass(frozen=True)
class CppParameter:
    name: str
    cpp_type: str


@dataclass(frozen=True)
class CppMethod:
    name: str
    return_type: str
    parameters: tuple[CppParameter, ...]


@dataclass(frozen=True)
class CppBuildInfo:
    executable: Path
    cache_key: str
    compiler: Path
    compiler_family: str
    compiler_version: str
    language: str
    compile_seconds: float
    cache_hit: bool
    method: CppMethod


def _mask_non_code(source: str) -> str:
    """Mask comments and literals while preserving offsets and line breaks."""

    result = list(source)
    index = 0
    state = "code"
    quote = ""
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if state == "code":
            if char == "/" and following == "/":
                result[index] = result[index + 1] = " "
                index += 2
                state = "line_comment"
                continue
            if char == "/" and following == "*":
                result[index] = result[index + 1] = " "
                index += 2
                state = "block_comment"
                continue
            if char in {'"', "'"}:
                quote = char
                result[index] = " "
                index += 1
                state = "literal"
                continue
        elif state == "line_comment":
            if char == "\n":
                state = "code"
            else:
                result[index] = " "
            index += 1
            continue
        elif state == "block_comment":
            if char == "*" and following == "/":
                result[index] = result[index + 1] = " "
                index += 2
                state = "code"
                continue
            if char != "\n":
                result[index] = " "
            index += 1
            continue
        elif state == "literal":
            if char == "\\" and following:
                result[index] = " "
                if following != "\n":
                    result[index + 1] = " "
                index += 2
                continue
            if char == quote:
                result[index] = " "
                index += 1
                state = "code"
                continue
            if char != "\n":
                result[index] = " "
            index += 1
            continue
        index += 1
    return "".join(result)


def _matching(text: str, start: int, opening: str, closing: str) -> int:
    depth = 0
    for index in range(start, len(text)):
        if text[index] == opening:
            depth += 1
        elif text[index] == closing:
            depth -= 1
            if depth == 0:
                return index
    raise CppSourceError(f"unmatched {opening!r}")


def _split_top_level(value: str, delimiter: str = ",") -> list[str]:
    parts: list[str] = []
    start = 0
    angle = paren = bracket = 0
    for index, char in enumerate(value):
        if char == "<":
            angle += 1
        elif char == ">":
            angle -= 1
        elif char == "(":
            paren += 1
        elif char == ")":
            paren -= 1
        elif char == "[":
            bracket += 1
        elif char == "]":
            bracket -= 1
        elif char == delimiter and angle == paren == bracket == 0:
            parts.append(value[start:index].strip())
            start = index + 1
    parts.append(value[start:].strip())
    return [part for part in parts if part]


def _strip_default(parameter: str) -> str:
    angle = paren = bracket = 0
    for index, char in enumerate(parameter):
        if char == "<":
            angle += 1
        elif char == ">":
            angle -= 1
        elif char == "(":
            paren += 1
        elif char == ")":
            paren -= 1
        elif char == "[":
            bracket += 1
        elif char == "]":
            bracket -= 1
        elif char == "=" and angle == paren == bracket == 0:
            return parameter[:index].strip()
    return parameter.strip()


def _normalize_cpp_type(raw_type: str, *, allow_void: bool = False) -> str:
    value = re.sub(r"\b(?:const|volatile|mutable|typename)\b", " ", raw_type)
    value = value.replace("&&", " ").replace("&", " ")
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\s*::\s*", "::", value)
    value = re.sub(r"\s*<\s*", "<", value)
    value = re.sub(r"\s*>\s*", ">", value)
    value = re.sub(r"\s*,\s*", ",", value)
    if "*" in value or "[" in value or "]" in value:
        raise CppSourceError(f"pointer/array type is not supported yet: {raw_type!r}")
    if value == "void" and allow_void:
        return value
    primitive = _PRIMITIVE_TYPES.get(value)
    if primitive:
        return primitive
    vector_match = re.fullmatch(r"(?:std::)?vector<(.+)>", value)
    if vector_match:
        element = _normalize_cpp_type(vector_match.group(1))
        return f"std::vector<{element}>"
    raise CppSourceError(f"unsupported C++ JSON type: {raw_type!r}")


def _parse_parameter(raw_parameter: str, index: int) -> CppParameter:
    parameter = _strip_default(raw_parameter)
    if parameter == "void":
        raise CppSourceError("void must be the only parameter")
    name_match = re.search(r"([A-Za-z_]\w*)\s*$", parameter)
    if not name_match:
        raise CppSourceError(f"parameter {index} requires a name")
    name = name_match.group(1)
    raw_type = parameter[: name_match.start()].strip()
    if not raw_type:
        raise CppSourceError(f"parameter {name!r} is missing a type")
    return CppParameter(name=name, cpp_type=_normalize_cpp_type(raw_type))


def _brace_depths(body: str) -> list[int]:
    depths = [0] * (len(body) + 1)
    depth = 0
    for index, char in enumerate(body):
        depths[index] = depth
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
    depths[len(body)] = depth
    return depths


def _access_at(body: str, position: int, depths: list[int]) -> str:
    access = "private"
    for match in re.finditer(r"\b(public|private|protected)\s*:", body[:position]):
        if depths[match.start()] == 0:
            access = match.group(1)
    return access


def parse_cpp_solution(source: str, main_method: str | None = None) -> CppMethod:
    masked = _mask_non_code(source)
    if re.search(r"^\s*#", masked, re.MULTILINE):
        raise CppSourceError(
            "preprocessor directives are not accepted in standard mode; "
            "the harness already provides common LeetCode headers"
        )
    if re.search(r"\bmain\s*\(", masked):
        raise CppSourceError("student source must not define main()")
    classes = list(re.finditer(r"\bclass\s+Solution\b[^;{]*\{", masked))
    if len(classes) != 1:
        raise CppSourceError("standard C++ mode requires exactly one class Solution")
    class_open = masked.find("{", classes[0].start())
    class_close = _matching(masked, class_open, "{", "}")
    body = masked[class_open + 1 : class_close]
    depths = _brace_depths(body)
    candidates: list[CppMethod] = []

    for name_match in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", body):
        if depths[name_match.start()] != 0:
            continue
        name = name_match.group(1)
        if name in {"Solution", "operator"}:
            continue
        open_paren = body.find("(", name_match.start())
        close_paren = _matching(body, open_paren, "(", ")")
        suffix = close_paren + 1
        qualifier = re.compile(r"\s*(?:const\b|noexcept\b|override\b|final\b)*\s*")
        suffix = qualifier.match(body, suffix).end()
        if suffix >= len(body) or body[suffix] != "{":
            continue
        if _access_at(body, name_match.start(), depths) != "public":
            continue
        boundary = max(
            body.rfind(";", 0, name_match.start()),
            body.rfind("}", 0, name_match.start()),
            body.rfind("{", 0, name_match.start()),
        )
        raw_return = body[boundary + 1 : name_match.start()].strip()
        raw_return = re.sub(
            r"^(?:public|private|protected)\s*:\s*", "", raw_return
        ).strip()
        if not raw_return:
            continue
        return_type = _normalize_cpp_type(raw_return, allow_void=True)
        if return_type == "void":
            raise CppSourceError("void/mutating LeetCode methods are not supported yet")
        raw_parameters = body[open_paren + 1 : close_paren].strip()
        parameters = (
            tuple(
                _parse_parameter(item, index)
                for index, item in enumerate(_split_top_level(raw_parameters))
            )
            if raw_parameters and raw_parameters != "void"
            else ()
        )
        candidates.append(CppMethod(name, return_type, parameters))

    if main_method is not None:
        matching = [candidate for candidate in candidates if candidate.name == main_method]
        if len(matching) != 1:
            raise CppSourceError(
                f"expected exactly one public Solution::{main_method} definition"
            )
        return matching[0]
    if len(candidates) != 1:
        names = ", ".join(candidate.name for candidate in candidates) or "none"
        raise CppSourceError(
            "main_method is required when Solution does not have exactly one "
            f"supported public method (found: {names})"
        )
    return candidates[0]


def parse_c_solution(source: str, main_method: str | None = None) -> CppMethod:
    """Parse the phase-one C ABI: one global function with scalar JSON types."""

    masked = _mask_non_code(source)
    if re.search(r"^\s*#", masked, re.MULTILINE):
        raise CppSourceError(
            "preprocessor directives are not accepted in standard C mode"
        )
    if re.search(r"\bmain\s*\(", masked):
        raise CppSourceError("student source must not define main()")
    depths = _brace_depths(masked)
    candidates: list[CppMethod] = []
    for name_match in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", masked):
        if depths[name_match.start()] != 0:
            continue
        name = name_match.group(1)
        open_paren = masked.find("(", name_match.start())
        close_paren = _matching(masked, open_paren, "(", ")")
        suffix = close_paren + 1
        while suffix < len(masked) and masked[suffix].isspace():
            suffix += 1
        if suffix >= len(masked) or masked[suffix] != "{":
            continue
        boundary = max(
            masked.rfind(";", 0, name_match.start()),
            masked.rfind("}", 0, name_match.start()),
            masked.rfind("{", 0, name_match.start()),
        )
        raw_return = masked[boundary + 1 : name_match.start()].strip()
        if not raw_return:
            continue
        return_type = _normalize_cpp_type(raw_return, allow_void=True)
        if return_type == "void" or return_type.startswith("std::"):
            raise CppSourceError(
                "standard C mode currently requires a scalar non-void return type"
            )
        raw_parameters = masked[open_paren + 1 : close_paren].strip()
        parameters = (
            tuple(
                _parse_parameter(item, index)
                for index, item in enumerate(_split_top_level(raw_parameters))
            )
            if raw_parameters and raw_parameters != "void"
            else ()
        )
        if any(parameter.cpp_type.startswith("std::") for parameter in parameters):
            raise CppSourceError(
                "C arrays/strings and returnSize conventions are not supported yet"
            )
        candidates.append(CppMethod(name, return_type, parameters))

    if main_method is not None:
        matching = [candidate for candidate in candidates if candidate.name == main_method]
        if len(matching) != 1:
            raise CppSourceError(
                f"expected exactly one global C function named {main_method}"
            )
        return matching[0]
    if len(candidates) != 1:
        names = ", ".join(candidate.name for candidate in candidates) or "none"
        raise CppSourceError(
            "main_method is required when the C source does not have exactly one "
            f"supported global function (found: {names})"
        )
    return candidates[0]


@dataclass(frozen=True)
class _Toolchain:
    compiler: Path
    family: str
    environment: dict[str, str]


def _configured_msvc(compiler: Path) -> _Toolchain | None:
    """Load vcvars for an explicit MSVC executable, including VS previews."""
    compiler = compiler.resolve()
    if not compiler.is_file():
        return None
    try:
        vc_root = compiler.parents[6]
    except IndexError:
        return None
    vcvars = vc_root / "Auxiliary" / "Build" / "vcvars64.bat"
    if not vcvars.is_file():
        return None
    try:
        completed = subprocess.run(
            ["cmd.exe", "/d", "/c", "call", str(vcvars), ">nul", "&&", "set"],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    environment = os.environ.copy()
    for line in completed.stdout.splitlines():
        if "=" not in line or line.startswith("="):
            continue
        key, value = line.split("=", 1)
        environment[key.upper()] = value
    return _Toolchain(compiler, "msvc", environment)


@functools.lru_cache(maxsize=1)
def _msvc_toolchain() -> _Toolchain | None:
    if os.name != "nt":
        return None
    # Developer Command Prompt environments already contain the exact MSVC
    # toolset selected by vcvars.  Prefer it, including preview Visual Studio
    # releases that older setuptools discovery code may not recognize yet.
    current = shutil.which("cl.exe")
    if current:
        return _Toolchain(Path(current).resolve(), "msvc", os.environ.copy())
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from setuptools._distutils._msvccompiler import _get_vc_env

            configured = _get_vc_env("x64")
    except (ImportError, OSError, RuntimeError, ValueError):
        configured = None
    if configured is not None:
        environment = os.environ.copy()
        for key, value in configured.items():
            environment[key.upper()] = value
        located = shutil.which("cl.exe", path=environment.get("PATH"))
        if located:
            return _Toolchain(Path(located).resolve(), "msvc", environment)

    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    candidates = sorted(
        program_files.glob(
            "Microsoft Visual Studio/*/*/VC/Tools/MSVC/*/bin/Hostx64/x64/cl.exe"
        ),
        reverse=True,
    )
    for compiler in candidates:
        toolchain = _configured_msvc(compiler)
        if toolchain is not None:
            return toolchain
    return None


def _gnu_toolchain(candidate: os.PathLike[str] | str) -> _Toolchain | None:
    located = shutil.which(str(candidate))
    path = Path(located or candidate).resolve()
    if not path.is_file():
        return None
    environment = os.environ.copy()
    environment["PATH"] = os.pathsep.join(
        (str(path.parent), environment.get("PATH", ""))
    )
    family = "clang" if "clang" in path.name.lower() else "gnu"
    return _Toolchain(path, family, environment)


def _toolchain(configured: os.PathLike[str] | str | None) -> _Toolchain:
    if configured is not None:
        if Path(str(configured)).name.lower() in {"cl", "cl.exe"}:
            explicit = Path(str(configured))
            if explicit.is_file():
                selected = _configured_msvc(explicit)
                if selected is not None:
                    return selected
            msvc = _msvc_toolchain()
            if msvc is None:
                raise FileNotFoundError("the configured MSVC x64 environment is unavailable")
            return msvc
        candidate = _gnu_toolchain(configured)
        if candidate is not None:
            return candidate
        raise FileNotFoundError(f"configured C++ compiler does not exist: {configured}")
    if os.environ.get("CXX"):
        return _toolchain(os.environ["CXX"])
    msvc = _msvc_toolchain()
    if msvc is not None:
        return msvc
    for candidate in (
        "g++",
        "clang++",
        Path(sys.prefix) / "Library" / "mingw-w64" / "bin" / "g++.exe",
    ):
        toolchain = _gnu_toolchain(candidate)
        if toolchain is not None:
            return toolchain
    raise FileNotFoundError(
        "a C++17 compiler was not found; pass compiler=... or configure CXX"
    )


def _compiler_version(toolchain: _Toolchain) -> str:
    arguments = (
        [str(toolchain.compiler), "/Bv"]
        if toolchain.family == "msvc"
        else [str(toolchain.compiler), "--version"]
    )
    completed = subprocess.run(
        arguments,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=10,
        env=toolchain.environment,
        check=False,
    )
    output = "\n".join((completed.stdout, completed.stderr)).strip()
    if not output:
        raise CppCompilationError(f"cannot query compiler version: {completed.stderr}")
    version_lines = [line.strip() for line in output.splitlines() if line.strip()]
    if toolchain.family == "msvc":
        for line in version_lines:
            if "Compiler Version" in line:
                return line
    return version_lines[0]


def _generate_worker_source(source: str, method: CppMethod, language: str) -> str:
    conversions = []
    names = []
    for index, parameter in enumerate(method.parameters):
        local_name = f"oj_arg_{index}"
        names.append(local_name)
        conversions.append(
            f"    auto {local_name} = oj_cpp_runtime::argument("
            f'input, {index}, "{parameter.name}").get<{parameter.cpp_type}>();'
        )
    argument_list = ", ".join(names)
    student_definition = (
        [source.rstrip()]
        if language == "cpp"
        else [
            "extern \"C\" "
            + method.return_type
            + " "
            + method.name
            + "("
            + ", ".join(parameter.cpp_type for parameter in method.parameters)
            + ");"
        ]
    )
    solution_setup = ["    Solution solution;"] if language == "cpp" else []
    target = f"solution.{method.name}" if language == "cpp" else method.name
    return "\n".join(
        [
            "#include <oj_cpp_worker_runtime.hpp>",
            "#include <algorithm>",
            "#include <array>",
            "#include <bitset>",
            "#include <climits>",
            "#include <cmath>",
            "#include <cstdint>",
            "#include <cstdlib>",
            "#include <cstring>",
            "#include <deque>",
            "#include <functional>",
            "#include <limits>",
            "#include <list>",
            "#include <map>",
            "#include <numeric>",
            "#include <queue>",
            "#include <set>",
            "#include <stack>",
            "#include <string>",
            "#include <unordered_map>",
            "#include <unordered_set>",
            "#include <utility>",
            "#include <tuple>",
            "#include <vector>",
            "using namespace std;",
            "",
            *student_definition,
            "",
            "static oj_cpp_runtime::json oj_invoke(const oj_cpp_runtime::json& input) {",
            *conversions,
            *solution_setup,
            f"    auto oj_output = {target}({argument_list});",
            "    return oj_cpp_runtime::json(oj_output);",
            "}",
            "",
            "int main(int argc, char** argv) {",
            "    return oj_cpp_runtime::worker_main(argc, argv, oj_invoke);",
            "}",
            "",
        ]
    )


def build_native_manager(
    manager_path: os.PathLike[str] | str = DEFAULT_MANAGER,
    *,
    compiler: os.PathLike[str] | str | None = None,
    force: bool = False,
    timeout_s: float = 60.0,
    _selected_toolchain: _Toolchain | None = None,
) -> float:
    """Build the trusted Windows process manager and return compile seconds."""

    destination = Path(manager_path).resolve()
    if (
        destination.is_file()
        and not force
        and destination.stat().st_mtime_ns >= MANAGER_SOURCE.stat().st_mtime_ns
    ):
        return 0.0
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    toolchain = _selected_toolchain or _toolchain(compiler)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f"{destination.stem}.{os.getpid()}.writing{destination.suffix}"
    )
    if toolchain.family == "msvc":
        command = [
            str(toolchain.compiler),
            "/nologo",
            "/std:c++17",
            "/EHsc",
            "/O2",
            "/DNOMINMAX",
            "/DWIN32_LEAN_AND_MEAN",
            str(MANAGER_SOURCE),
            f"/Fo{destination.parent / 'process_manager.obj'}",
            f"/Fe{temporary}",
        ]
    else:
        command = [
            str(toolchain.compiler),
            str(MANAGER_SOURCE),
            "-std=c++17",
            "-O2",
            "-DNOMINMAX",
            "-DWIN32_LEAN_AND_MEAN",
            "-o",
            str(temporary),
            "-static-libgcc",
            "-static-libstdc++",
        ]
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout_s,
            env=toolchain.environment,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        temporary.unlink(missing_ok=True)
        raise CppCompilationError(
            f"native manager compilation exceeded {timeout_s:.1f}s"
        ) from exc
    elapsed = time.perf_counter() - started
    if completed.returncode != 0 or not temporary.is_file():
        temporary.unlink(missing_ok=True)
        details = (completed.stderr or completed.stdout).strip()
        raise CppCompilationError(
            f"native manager compilation failed ({completed.returncode}):\n{details}"
        )
    os.replace(temporary, destination)
    return elapsed


class CompiledCppRunner:
    """Compile and execute the base-JSON LeetCode C/C++ standard subset.

    Compilation is cached by source, parsed ABI, compiler identity, flags and
    harness contents. The compiled executable is then launched by the same
    Windows Job Object manager used by the Python native backend.
    """

    def __init__(
        self,
        solution_file: os.PathLike[str] | str,
        main_method: str | None = None,
        *,
        workers: int | str = 1,
        manager_path: os.PathLike[str] | str = DEFAULT_MANAGER,
        compiler: os.PathLike[str] | str | None = None,
        memory_limit_mb: int = 512,
        workspace: os.PathLike[str] | str | None = None,
        compile_timeout_s: float = 90.0,
        force_rebuild: bool = False,
        auto_tune_config: AutoTuneConfig | None = None,
    ) -> None:
        auto_workers = isinstance(workers, str) and workers.lower() == "auto"
        if not auto_workers and (
            not isinstance(workers, int) or not 1 <= workers <= MAX_WORKERS
        ):
            raise ValueError(f"workers must be between 1 and {MAX_WORKERS}")
        self.solution_file = Path(solution_file).resolve()
        suffix = self.solution_file.suffix.lower()
        if suffix not in CPP_EXTENSIONS and suffix != ".c":
            raise CppSourceError(
                f"unsupported C++ source extension: {self.solution_file.suffix}"
            )
        self.source = self.solution_file.read_text(encoding="utf-8-sig")
        self.language = "c" if suffix == ".c" else "cpp"
        self.method = (
            parse_c_solution(self.source, main_method)
            if self.language == "c"
            else parse_cpp_solution(self.source, main_method)
        )
        self.workers = 1 if auto_workers else workers
        self._auto_workers = auto_workers
        self.auto_tune_config = auto_tune_config or AutoTuneConfig()
        self.last_auto_tune: AutoTuneDecision | None = None
        self.manager_path = Path(manager_path).resolve()
        self._toolchain = _toolchain(compiler)
        if self.language == "c" and self._toolchain.family != "msvc":
            raise CppSourceError(
                "phase-one C compilation currently requires the MSVC toolchain"
            )
        self.compiler = self._toolchain.compiler
        self.memory_limit_mb = memory_limit_mb
        self.workspace = Path(workspace or ROOT).resolve()
        self.compile_timeout_s = compile_timeout_s
        if memory_limit_mb < 64:
            raise ValueError("memory_limit_mb must be at least 64")
        if compile_timeout_s <= 0:
            raise ValueError("compile_timeout_s must be positive")
        self.manager_compile_seconds = build_native_manager(
            self.manager_path,
            timeout_s=compile_timeout_s,
            _selected_toolchain=self._toolchain,
        )
        self.build_info = self._build(force_rebuild)

    def _build(self, force_rebuild: bool) -> CppBuildInfo:
        version = _compiler_version(self._toolchain)
        generated = _generate_worker_source(self.source, self.method, self.language)
        flags = (
            ("/std:c++17", "/O2", "/DNDEBUG", "/EHsc", "/utf-8", "Psapi.lib")
            if self._toolchain.family == "msvc"
            else (
                "-std=c++17",
                "-O2",
                "-DNDEBUG",
                "-static-libgcc",
                "-static-libstdc++",
                "-lpsapi",
            )
        )
        digest = hashlib.sha256()
        for value in (
            HARNESS_VERSION.encode(),
            self.language.encode("ascii"),
            generated.encode("utf-8"),
            WORKER_RUNTIME_HEADER.read_bytes(),
            JSON_HEADER.read_bytes(),
            str(self.compiler).encode("utf-8"),
            self._toolchain.family.encode("ascii"),
            version.encode("utf-8"),
            "\0".join(flags).encode("ascii"),
        ):
            digest.update(len(value).to_bytes(8, "little"))
            digest.update(value)
        cache_key = digest.hexdigest()
        build_dir = self.workspace / "build" / "cpp_runner" / "cache" / cache_key
        executable = build_dir / "oj_cpp_worker.exe"
        if executable.is_file() and not force_rebuild:
            return CppBuildInfo(
                executable,
                cache_key,
                self.compiler,
                self._toolchain.family,
                version,
                self.language,
                0.0,
                True,
                self.method,
            )

        build_dir.mkdir(parents=True, exist_ok=True)
        generated_path = build_dir / "worker.cpp"
        generated_path.write_text(generated, encoding="utf-8")
        c_source_path: Path | None = None
        if self.language == "c":
            c_source_path = build_dir / "student.c"
            c_source_path.write_text(self.source, encoding="utf-8")
        temporary_executable = build_dir / f"oj_cpp_worker.{os.getpid()}.writing.exe"
        if self._toolchain.family == "msvc":
            command = [
                str(self.compiler),
                "/nologo",
                "/std:c++17",
                "/O2",
                "/DNDEBUG",
                "/EHsc",
                "/utf-8",
                f"/I{NATIVE_INCLUDE}",
                str(generated_path),
                *([str(c_source_path)] if c_source_path is not None else []),
                *(
                    []
                    if c_source_path is not None
                    else [f"/Fo{build_dir / 'worker.obj'}"]
                ),
                f"/Fd{build_dir / 'worker.pdb'}",
                f"/Fe{temporary_executable}",
                "/link",
                "Psapi.lib",
            ]
        else:
            command = [
                str(self.compiler),
                str(generated_path),
                "-std=c++17",
                "-O2",
                "-DNDEBUG",
                "-I",
                str(NATIVE_INCLUDE),
                "-o",
                str(temporary_executable),
                "-static-libgcc",
                "-static-libstdc++",
                "-lpsapi",
            ]
        started = time.perf_counter()
        compile_working_directory = (
            build_dir if c_source_path is not None else self.workspace
        )
        try:
            completed = subprocess.run(
                command,
                cwd=compile_working_directory,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=self.compile_timeout_s,
                env=self._toolchain.environment,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            temporary_executable.unlink(missing_ok=True)
            raise CppCompilationError(
                f"C++ compilation exceeded {self.compile_timeout_s:.1f}s"
            ) from exc
        compile_seconds = time.perf_counter() - started
        if completed.returncode != 0 or not temporary_executable.is_file():
            temporary_executable.unlink(missing_ok=True)
            details = (completed.stderr or completed.stdout).strip()
            raise CppCompilationError(
                f"C++ compilation failed ({completed.returncode}):\n{details}"
            )
        os.replace(temporary_executable, executable)
        metadata = {
            "cache_key": cache_key,
            "compiler": str(self.compiler),
            "compiler_family": self._toolchain.family,
            "compiler_version": version,
            "language": self.language,
            "compile_seconds": compile_seconds,
            "method": asdict(self.method),
            "source": str(self.solution_file),
            "flags": list(flags),
        }
        (build_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return CppBuildInfo(
            executable,
            cache_key,
            self.compiler,
            self._toolchain.family,
            version,
            self.language,
            compile_seconds,
            False,
            self.method,
        )

    def run_store(
        self,
        store_path: os.PathLike[str] | str,
        *,
        batch_timeout_s: float | None = None,
    ) -> RunReport:
        if not self._auto_workers:
            return self._run_store_with_workers(
                store_path,
                workers=self.workers,
                batch_timeout_s=batch_timeout_s,
            )

        config = self.auto_tune_config
        resolved_store = Path(store_path).resolve()
        system = inspect_system()
        store = inspect_store(resolved_store)
        program = inspect_program(self.source, self.language, self.method.name)
        probe: AutoTuneProbe | None = None
        if config.enable_probe and store.case_count:
            with tempfile.TemporaryDirectory(
                prefix="oj_cpp_auto_probe_", dir=self.workspace
            ) as directory:
                probe_store = Path(directory) / "probe.ojbin"
                sampled = create_probe_store(
                    resolved_store, probe_store, config.sample_cases
                )
                try:
                    probe_report = self._run_store_with_workers(
                        probe_store,
                        workers=1,
                        # The Python backend enforces this limit per case;
                        # the native manager currently exposes a batch limit.
                        batch_timeout_s=config.probe_timeout_s * sampled,
                        include_compile_metrics=False,
                    )
                    probe = AutoTuneProbe(
                        backend_family="compiled",
                        sample_cases=sampled,
                        wall_seconds=probe_report.metrics.wall_seconds,
                        compute_seconds=probe_report.metrics.worker_compute_seconds,
                        decode_seconds=probe_report.metrics.worker_decode_seconds,
                        peak_rss_bytes=probe_report.metrics.peak_worker_rss_bytes,
                    )
                except Exception as exc:
                    probe = AutoTuneProbe(
                        backend_family="compiled",
                        sample_cases=sampled,
                        wall_seconds=config.probe_timeout_s * sampled,
                        compute_seconds=0.0,
                        decode_seconds=0.0,
                        peak_rss_bytes=0,
                        timed_out=True,
                        error=f"{type(exc).__name__}: {exc}",
                    )
        decision = select_workers(
            backend_family="compiled",
            system=system,
            store=store,
            program=program,
            config=config,
            probe=probe,
            worker_memory_limit_bytes=self.memory_limit_mb * 1024**2,
        )
        self.workers = decision.workers
        self.last_auto_tune = decision
        report = self._run_store_with_workers(
            resolved_store,
            workers=decision.workers,
            batch_timeout_s=batch_timeout_s,
        )
        report.auto_tune = decision.to_dict()
        return report

    def _run_store_with_workers(
        self,
        store_path: os.PathLike[str] | str,
        *,
        workers: int,
        batch_timeout_s: float | None = None,
        include_compile_metrics: bool = True,
    ) -> RunReport:
        if batch_timeout_s is not None and batch_timeout_s <= 0:
            raise ValueError("batch_timeout_s must be positive")
        store_path = Path(store_path).resolve()
        with CaseStoreReader(store_path) as store:
            case_count = len(store)
        with tempfile.TemporaryDirectory(
            prefix="oj_cpp_results_", dir=self.workspace
        ) as result_directory:
            result_path = Path(result_directory)
            command = [
                str(self.manager_path),
                "--worker-executable",
                str(self.build_info.executable),
                "--store",
                str(store_path),
                "--solution",
                str(self.solution_file),
                "--method",
                self.method.name,
                "--result-dir",
                str(result_path),
                "--workspace",
                str(self.workspace),
                "--case-count",
                str(case_count),
                "--workers",
                str(workers),
                "--memory-mb",
                str(self.memory_limit_mb),
                "--timeout-ms",
                str(int(batch_timeout_s * 1000) if batch_timeout_s else 0),
                "--standard-mode",
                "1",
            ]
            started = time.perf_counter()
            completed = subprocess.run(
                command,
                cwd=self.workspace,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=(batch_timeout_s + 5.0 if batch_timeout_s else None),
                check=False,
            )
            wall_seconds = time.perf_counter() - started
            if completed.returncode != 0:
                worker_errors = "\n".join(
                    path.read_text(encoding="utf-8", errors="replace")
                    for path in sorted(result_path.glob("worker_*.error.txt"))
                )
                raise RuntimeError(
                    f"native C++ manager failed ({completed.returncode}):\n"
                    f"{completed.stdout}\n{completed.stderr}\n{worker_errors}"
                )
            worker_files = sorted(result_path.glob("worker_*.json"))
            expected_workers = min(workers, max(1, case_count))
            if len(worker_files) != expected_workers:
                raise RuntimeError(
                    f"expected {expected_workers} C++ results, got {len(worker_files)}"
                )
            worker_results = [
                json.loads(path.read_text(encoding="utf-8")) for path in worker_files
            ]

        digest = 0
        fallback_count = 0
        for item in worker_results:
            digest ^= int(item["digest"], 16)
            for fallback in item.get("fallback_results", ()):
                digest ^= digest_value(
                    int(fallback["index"]),
                    fallback["cid"],
                    fallback.get("output"),
                    fallback.get("error"),
                )
                fallback_count += 1
        correct = sum(int(item["correct"]) for item in worker_results)
        wrong = sum(int(item["wrong"]) for item in worker_results)
        errors = sum(int(item["errors"]) for item in worker_results)
        if correct + wrong + errors != case_count:
            raise RuntimeError("C++ workers returned an invalid completed-case count")
        metrics = RunMetrics(
            backend=f"native_process_manager_standard_{self.language}",
            workers=workers,
            case_count=case_count,
            wall_seconds=wall_seconds,
            throughput_cases_per_second=(case_count / wall_seconds if wall_seconds else 0.0),
            pool_startup_seconds=0.0,
            worker_compute_seconds=sum(
                float(item["compute_seconds"]) for item in worker_results
            ),
            worker_decode_seconds=sum(
                float(item["decode_seconds"]) for item in worker_results
            ),
            peak_worker_rss_bytes=sum(int(item["rss_bytes"]) for item in worker_results),
            compile_seconds=(
                self.manager_compile_seconds + self.build_info.compile_seconds
                if include_compile_metrics
                else 0.0
            ),
            artifact_cache_hit=self.build_info.cache_hit,
            fallback_digest_cases=fallback_count,
        )
        return RunReport(
            metrics=metrics,
            correct_count=correct,
            wrong_count=wrong,
            error_count=errors,
            digest=f"{digest:032x}",
            results=None,
        )
