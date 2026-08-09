from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from .case_store import CaseStoreReader
from .models import RunMetrics, RunReport
from .persistent_python import MAX_WORKERS


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANAGER = ROOT / "build" / "native_runner" / "oj_native_manager.exe"
WORKER_SCRIPT = Path(__file__).resolve().with_name("native_worker.py")


class NativeProcessRunner:
    """Python facade for the independently built Windows process manager.

    Version 1 uses balanced static ranges.  Its Job Object enforces process and
    per-process memory limits, but restricted filesystem tokens and network
    isolation are deliberately not claimed yet.
    """

    def __init__(
        self,
        solution_file: os.PathLike[str] | str,
        main_method: str,
        *,
        workers: int,
        manager_path: os.PathLike[str] | str = DEFAULT_MANAGER,
        python_executable: os.PathLike[str] | str = sys.executable,
        memory_limit_mb: int = 512,
        workspace: os.PathLike[str] | str | None = None,
        standard_mode: bool = False,
    ) -> None:
        if not 1 <= workers <= MAX_WORKERS:
            raise ValueError(f"workers must be between 1 and {MAX_WORKERS}")
        self.solution_file = Path(solution_file).resolve()
        self.main_method = main_method
        self.workers = workers
        self.manager_path = Path(manager_path).resolve()
        self.python_executable = Path(python_executable).resolve()
        self.interpreter_name = (
            "pypy"
            if "pypy" in str(self.python_executable).lower()
            else "cpython"
        )
        self.memory_limit_mb = memory_limit_mb
        self.standard_mode = standard_mode
        self.workspace = Path(workspace or ROOT).resolve()
        if not self.manager_path.is_file():
            raise FileNotFoundError(
                f"native manager is not built: {self.manager_path}"
            )

    def run_store(
        self,
        store_path: os.PathLike[str] | str,
        *,
        batch_timeout_s: float | None = None,
    ) -> RunReport:
        store_path = Path(store_path).resolve()
        with CaseStoreReader(store_path) as store:
            case_count = len(store)
        with tempfile.TemporaryDirectory(
            prefix="oj_native_results_", dir=self.workspace
        ) as result_directory:
            result_path = Path(result_directory)
            command = [
                str(self.manager_path),
                "--python",
                str(self.python_executable),
                "--worker-script",
                str(WORKER_SCRIPT),
                "--store",
                str(store_path),
                "--solution",
                str(self.solution_file),
                "--method",
                self.main_method,
                "--result-dir",
                str(result_path),
                "--workspace",
                str(self.workspace),
                "--case-count",
                str(case_count),
                "--workers",
                str(self.workers),
                "--memory-mb",
                str(self.memory_limit_mb),
                "--timeout-ms",
                str(int(batch_timeout_s * 1000) if batch_timeout_s else 0),
                "--standard-mode",
                "1" if self.standard_mode else "0",
            ]
            started = time.perf_counter()
            completed = subprocess.run(
                command,
                cwd=self.workspace,
                text=True,
                encoding="utf-8",
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
                    f"native manager failed ({completed.returncode}):\n"
                    f"{completed.stdout}\n{completed.stderr}\n{worker_errors}"
                )
            worker_files = sorted(result_path.glob("worker_*.json"))
            expected_workers = min(self.workers, max(1, case_count))
            if len(worker_files) != expected_workers:
                raise RuntimeError(
                    f"expected {expected_workers} native results, got {len(worker_files)}"
                )
            worker_results: list[dict[str, Any]] = [
                json.loads(path.read_text(encoding="utf-8")) for path in worker_files
            ]

        digest = 0
        for item in worker_results:
            digest ^= int(item["digest"], 16)
        correct = sum(item["correct"] for item in worker_results)
        wrong = sum(item["wrong"] for item in worker_results)
        errors = sum(item["errors"] for item in worker_results)
        metrics = RunMetrics(
            backend=(
                f"native_process_manager_standard_{self.interpreter_name}"
                if self.standard_mode
                else f"native_process_manager_{self.interpreter_name}"
            ),
            workers=self.workers,
            case_count=case_count,
            wall_seconds=wall_seconds,
            throughput_cases_per_second=(case_count / wall_seconds if wall_seconds else 0.0),
            pool_startup_seconds=0.0,
            worker_compute_seconds=sum(item["compute_seconds"] for item in worker_results),
            worker_decode_seconds=sum(item["decode_seconds"] for item in worker_results),
            peak_worker_rss_bytes=sum(item["rss_bytes"] for item in worker_results),
        )
        return RunReport(
            metrics=metrics,
            correct_count=correct,
            wrong_count=wrong,
            error_count=errors,
            digest=f"{digest:032x}",
            results=None,
        )
