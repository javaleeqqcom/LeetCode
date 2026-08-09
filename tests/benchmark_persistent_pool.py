"""Control experiment: reuse a long-lived Python process pool.

This intentionally bypasses SolutionRunner's per-run worker startup while
keeping Windows ``spawn`` and argument pickling costs. It helps separate
startup overhead from algorithm parallelism.
"""

from __future__ import annotations

import copy
import json
import multiprocessing
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

from tests.benchmark_parallel import SCENARIOS, WORKERS, build_cases
from tests.fixtures.benchmarks.classic_algorithms import Solution


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "benchmark_results" / "persistent_pool_control.json"
CONTROL_SCENARIOS = tuple(
    scenario
    for scenario in SCENARIOS
    if scenario.scale_label == "large"
) + (SCENARIOS[0],)

_SOLUTION: Solution | None = None
_THREAD_SOLUTION = Solution()


def initialize_worker() -> None:
    global _SOLUTION
    _SOLUTION = Solution()


def execute_task(task: tuple[str, Any]) -> Any:
    method_name, case_input = task
    assert _SOLUTION is not None
    return getattr(_SOLUTION, method_name)(*case_input)


def execute_thread_task(task: tuple[str, Any]) -> Any:
    method_name, case_input = task
    # A process receives a private unpickled copy; make thread semantics match.
    return getattr(_THREAD_SOLUTION, method_name)(*copy.deepcopy(case_input))


def run_direct(method_name: str, cases: list[dict]) -> tuple[float, list[Any]]:
    solution = Solution()
    started = time.perf_counter()
    outputs = [
        getattr(solution, method_name)(*copy.deepcopy(case["input"]))
        for case in cases
    ]
    return time.perf_counter() - started, outputs


def main() -> int:
    ctx = multiprocessing.get_context("spawn")
    scenario_data = []
    results = []
    for scenario in CONTROL_SCENARIOS:
        cases = build_cases(scenario)
        direct_runs = [run_direct(scenario.method, cases) for _ in range(2)]
        direct_wall = statistics.median(item[0] for item in direct_runs)
        results.append({
            "algorithm": scenario.algorithm,
            "scale_label": scenario.scale_label,
            "scale": scenario.scale,
            "case_count": scenario.case_count,
            "direct_seconds": direct_wall,
        })
        scenario_data.append((scenario, cases, direct_runs[0][1]))

    # Create only one pool at a time, so the process count never exceeds the
    # largest explicitly tested worker count.
    for workers in WORKERS:
        if workers == 1:
            continue
        with ctx.Pool(processes=workers, initializer=initialize_worker) as pool:
            pool.map(execute_task, [("sieve_count", (10,))] * workers)
            for scenario_result, (scenario, cases, reference) in zip(
                results, scenario_data
            ):
                tasks = [(scenario.method, case["input"]) for case in cases]
                chunksize = max(1, len(tasks) // (workers * 4))
                walls = []
                for _ in range(2):
                    started = time.perf_counter()
                    outputs = pool.map(execute_task, tasks, chunksize=chunksize)
                    walls.append(time.perf_counter() - started)
                    if outputs != reference:
                        raise AssertionError(
                            f"persistent pool output mismatch: {scenario.algorithm}"
                        )
                wall = statistics.median(walls)
                scenario_result[f"pool_{workers}_seconds"] = wall
                scenario_result[f"pool_{workers}_speedup"] = (
                    scenario_result["direct_seconds"] / wall
                )

    for workers in WORKERS:
        if workers == 1:
            continue
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for scenario_result, (scenario, cases, reference) in zip(
                results, scenario_data
            ):
                tasks = [(scenario.method, case["input"]) for case in cases]
                walls = []
                for _ in range(2):
                    started = time.perf_counter()
                    outputs = list(executor.map(execute_thread_task, tasks))
                    walls.append(time.perf_counter() - started)
                    if outputs != reference:
                        raise AssertionError(
                            f"thread pool output mismatch: {scenario.algorithm}"
                        )
                wall = statistics.median(walls)
                scenario_result[f"thread_{workers}_seconds"] = wall
                scenario_result[f"thread_{workers}_speedup"] = (
                    scenario_result["direct_seconds"] / wall
                )

    for scenario_result in results:
        print(json.dumps(scenario_result, ensure_ascii=False), flush=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
