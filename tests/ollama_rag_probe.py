"""End-to-end local Ollama + RAG case-generator diagnostic."""

from __future__ import annotations

import json
import os
import tempfile
import time
import subprocess
import sys
import base64
from pathlib import Path

import requests

from agents.agent_io import AgentIO
from agents.case_generator_agent import CaseGeneratorAgent
from agents.ollama_config import DEFAULT_CODE_MODEL
from rag.retriever import RAGRetriever
from schemas.problem_context import ProblemContext
from tools.solution_runner import SolutionRunner


ROOT = Path(__file__).resolve().parent.parent
BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")


def validate_two_sum_semantics(code: str) -> tuple[bool, str]:
    """Verify the problem-specific promise in a separate interpreter."""
    checker = r'''
import base64
import json
import random
import sys

namespace = {"__builtins__": __builtins__}
code = base64.b64decode(sys.stdin.buffer.read()).decode("utf-8")
exec(compile(code, "<generated>", "exec"), namespace)
generator = namespace["case_generator"]
random.seed(20260809)
for scale in (2, 3, 10, 30, 100, 1000):
    for _ in range(3):
        case = generator(scale)
        values = case["input"]
        if isinstance(values, dict):
            nums, target = values["nums"], values["target"]
        else:
            nums, target = values
        pairs = [
            (i, j)
            for i in range(len(nums))
            for j in range(i + 1, len(nums))
            if nums[i] + nums[j] == target
        ]
        if len(pairs) != 1:
            raise ValueError(
                f"scale={scale}: expected exactly one valid pair, got {len(pairs)}. "
                "Do not derive target from positions after shuffling. Keep the "
                "intentional pair values, or preserve target=0 for an a/-a pair."
            )
print("TWO_SUM_VALID")
'''
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-c", checker],
            input=base64.b64encode(code.encode("utf-8")),
            capture_output=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        return False, "Two Sum 语义抽样超过 5 秒"
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).decode("utf-8", errors="replace")
        return False, detail.strip()[-1000:]
    return True, ""


def sample_generated_cases(code: str) -> list[dict]:
    """Materialize generated cases out-of-process, then attach oracle answers."""
    sampler = r'''
import base64
import json
import random
import sys

namespace = {"__builtins__": __builtins__}
code = base64.b64decode(sys.stdin.buffer.read()).decode("utf-8")
exec(compile(code, "<generated>", "exec"), namespace)
random.seed(20260809)
print(json.dumps([namespace["case_generator"](scale) for scale in (2, 10, 1000)]))
'''
    completed = subprocess.run(
        [sys.executable, "-I", "-c", sampler],
        input=base64.b64encode(code.encode("utf-8")),
        capture_output=True,
        timeout=5,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=True,
    )
    raw_cases = json.loads(completed.stdout.decode("utf-8"))
    cases = []
    for cid, case in enumerate(raw_cases):
        values = case["input"]
        if isinstance(values, dict):
            nums, target = values["nums"], values["target"]
        else:
            nums, target = values
        pairs = [
            [left, right]
            for left in range(len(nums))
            for right in range(left + 1, len(nums))
            if nums[left] + nums[right] == target
        ]
        if len(pairs) != 1:
            raise RuntimeError(f"sample {cid} is not uniquely solvable")
        cases.append({"cid": cid, "input": values, "expected": pairs[0]})
    return cases


def main() -> int:
    started = time.perf_counter()
    version = requests.get(f"{BASE_URL}/api/version", timeout=5).json()["version"]
    available = {
        item["name"] for item in requests.get(f"{BASE_URL}/api/tags", timeout=10).json()["models"]
    }
    model = os.getenv("OLLAMA_CODE_MODEL", DEFAULT_CODE_MODEL)
    if model not in available:
        raise RuntimeError(f"所选模型未安装: {model}")

    retriever = RAGRetriever(ROOT / "rag_db")
    rag_started = time.perf_counter()
    hits = retriever.search(
        "Two Sum 数组 哈希表 随机边界 唯一答案 测试规模",
        "case_generator",
        topk=3,
    )
    rag_seconds = time.perf_counter() - rag_started

    runner = SolutionRunner(ROOT / "tests" / "fixtures" / "two_sum_solution.py")
    struct = runner.build_solution_struct()
    struct.complexity_hint.time_complexity = "O(n)"
    struct.complexity_hint.space_complexity = "O(n)"
    struct.complexity_hint.estimated_n_limit = 100_000
    struct.complexity_hint.notes = "哈希表；需覆盖重复值、负数、边界和唯一答案。"

    with tempfile.TemporaryDirectory(prefix="ollama_rag_probe_") as output_dir:
        problem = ProblemContext(
            title="Two Sum",
            description=(
                "给定整数数组 nums 和整数 target，返回两个不同下标，使对应元素之和等于 target。"
                "每个输入恰好有一个答案。"
            ),
            examples=[{"input": {"nums": [2, 7, 11, 15], "target": 9}, "output": [0, 1]}],
            constraints="2 <= len(nums) <= 100000；元素和 target 均为整数。",
            tags=["array", "hash-table"],
            solution_struct=struct,
            problem_dir=Path(output_dir),
        )
        generation_started = time.perf_counter()
        try:
            code = CaseGeneratorAgent(
                problem,
                case_validator=validate_two_sum_semantics,
            ).run(dry_run=False)
        except Exception:
            for response_file in sorted((Path(output_dir) / "agent_logs").glob("AI_response_*.log")):
                print(f"FAILED_RESPONSE={response_file.name}")
                print(response_file.read_text(encoding="utf-8", errors="replace"))
            raise
        generation_seconds = time.perf_counter() - generation_started

    if code is None:
        raise RuntimeError("CaseGeneratorAgent 未返回代码")
    valid, error = AgentIO.validate_case_generator(code)
    if not valid:
        raise RuntimeError(error)

    generated_cases = sample_generated_cases(code)
    runner_started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="ollama_runner_probe_") as log_dir:
        run_results = runner.run(
            generated_cases,
            log_folder=log_dir,
            thread=2,
            timeout_s=2.0,
            skip_error=True,
        )
    runner_seconds = time.perf_counter() - runner_started
    right, valid_count = runner.summary_results(run_results, verbose=False)
    if (right, valid_count) != (len(generated_cases), len(generated_cases)):
        raise RuntimeError(f"generated case comparison failed: {right}/{valid_count}")

    loaded = requests.get(f"{BASE_URL}/api/ps", timeout=10).json().get("models", [])
    report = {
        "ollama_version": version,
        "code_model": model,
        "rag_counts": {item.name: item.count() for item in retriever.client.list_collections()},
        "rag_seconds": round(rag_seconds, 3),
        "rag_hits": [
            {
                "score": round(hit["score"], 4),
                "name": hit["metadata"].get("module_name", hit["metadata"].get("name", "")),
            }
            for hit in hits
        ],
        "generation_seconds": round(generation_seconds, 3),
        "runner_seconds": round(runner_seconds, 3),
        "runner_cases": len(generated_cases),
        "runner_right": right,
        "total_seconds": round(time.perf_counter() - started, 3),
        "loaded_models": [
            {
                "name": item["name"],
                "size_gib": round(item["size"] / 1024**3, 2),
                "vram_gib": round(item["size_vram"] / 1024**3, 2),
            }
            for item in loaded
        ],
        "validated": True,
    }
    print("PROBE_REPORT=" + json.dumps(report, ensure_ascii=False))
    print("GENERATED_CODE_BEGIN")
    print(code)
    print("GENERATED_CODE_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
