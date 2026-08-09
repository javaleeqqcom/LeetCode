"""Benchmark SolutionRunner with 1 to 16 worker processes.

Run from the repository root:
    python -m tests.benchmark_parallel --repeats 3
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
import math
import multiprocessing
import os
import platform
import random
import statistics
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

# Avoid hidden nested BLAS/OpenMP parallelism in every worker process.
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

from tools.solution_runner import SolutionRunner


ROOT = Path(__file__).resolve().parent.parent
SOLUTION_FILE = ROOT / "tests" / "fixtures" / "benchmarks" / "classic_algorithms.py"
OUTPUT_DIR = ROOT / "benchmark_results"
WORKERS = (1, 2, 4, 6, 8, 12, 16)


@dataclass(frozen=True)
class Scenario:
    algorithm: str
    method: str
    scale_label: str
    scale: int
    case_count: int


@dataclass
class RunRecord:
    algorithm: str
    scale_label: str
    scale: int
    case_count: int
    workers: int
    repeat: int
    wall_seconds: float
    summed_case_seconds: float
    throughput_cases_per_second: float


SCENARIOS = (
    Scenario("binary_search", "binary_search", "small", 1_000, 64),
    Scenario("binary_search", "binary_search", "medium", 10_000, 32),
    Scenario("binary_search", "binary_search", "large", 100_000, 24),
    Scenario("sort", "sort_checksum", "small", 2_000, 64),
    Scenario("sort", "sort_checksum", "medium", 20_000, 32),
    Scenario("sort", "sort_checksum", "large", 100_000, 24),
    Scenario("sieve", "sieve_count", "small", 50_000, 64),
    Scenario("sieve", "sieve_count", "medium", 200_000, 32),
    Scenario("sieve", "sieve_count", "large", 800_000, 24),
    Scenario("lcs", "lcs_length", "small", 100, 64),
    Scenario("lcs", "lcs_length", "medium", 400, 32),
    Scenario("lcs", "lcs_length", "large", 1_000, 24),
    Scenario("matrix", "matrix_multiply_checksum", "small", 20, 64),
    Scenario("matrix", "matrix_multiply_checksum", "medium", 50, 32),
    Scenario("matrix", "matrix_multiply_checksum", "large", 100, 24),
)


def _random_ints(size: int, seed: int) -> list[int]:
    rng = random.Random(seed)
    return [rng.randrange(-10**9, 10**9) for _ in range(size)]


def _random_text(size: int, seed: int) -> str:
    rng = random.Random(seed)
    alphabet = "abcdefghijklmno"
    return "".join(rng.choice(alphabet) for _ in range(size))


def build_cases(scenario: Scenario) -> list[dict[str, Any]]:
    cases = []
    for cid in range(scenario.case_count):
        seed = 10_000 + cid * 97 + scenario.scale
        if scenario.algorithm == "binary_search":
            nums = list(range(scenario.scale))
            target = (seed * 37) % scenario.scale
            case_input = (nums, target)
        elif scenario.algorithm == "sort":
            case_input = (_random_ints(scenario.scale, seed),)
        elif scenario.algorithm == "sieve":
            case_input = (scenario.scale + cid % 17,)
        elif scenario.algorithm == "lcs":
            case_input = (
                _random_text(scenario.scale, seed),
                _random_text(scenario.scale, seed + 1),
            )
        elif scenario.algorithm == "matrix":
            case_input = (scenario.scale, seed)
        else:
            raise ValueError(scenario.algorithm)
        cases.append({"cid": cid, "input": case_input})
    return cases


def normalized_outputs(results: list[dict]) -> list[Any]:
    ordered = sorted(results, key=lambda item: item["cid"])
    errors = [item for item in ordered if "error" in item]
    if errors:
        raise RuntimeError(f"benchmark case failed: {errors[0]}")
    return [item["output"] for item in ordered]


def benchmark_scenario(
    scenario: Scenario,
    repeats: int,
    log_dir: str,
) -> list[RunRecord]:
    cases = build_cases(scenario)
    runner = SolutionRunner(SOLUTION_FILE, main_method=scenario.method)
    records: list[RunRecord] = []
    reference_outputs: list[Any] | None = None

    # Warm the dynamic module and Python allocator outside measured sections.
    warmup = runner.run(cases[:1], log_folder=log_dir, log_wrong=False)
    normalized_outputs(warmup)

    for repeat in range(repeats):
        worker_order = WORKERS if repeat % 2 == 0 else tuple(reversed(WORKERS))
        for workers in worker_order:
            gc.collect()
            started = time.perf_counter()
            results = runner.run(
                cases,
                log_folder=log_dir,
                log_wrong=False,
                thread=workers,
                timeout_s=None,
            )
            wall_seconds = time.perf_counter() - started
            outputs = normalized_outputs(results)
            if reference_outputs is None:
                reference_outputs = outputs
            elif outputs != reference_outputs:
                raise AssertionError(
                    f"output mismatch for {scenario.algorithm}/{scenario.scale_label} "
                    f"with {workers} workers"
                )
            summed_case_seconds = sum(float(item.get("elapsed", 0.0)) for item in results)
            records.append(
                RunRecord(
                    algorithm=scenario.algorithm,
                    scale_label=scenario.scale_label,
                    scale=scenario.scale,
                    case_count=scenario.case_count,
                    workers=workers,
                    repeat=repeat,
                    wall_seconds=wall_seconds,
                    summed_case_seconds=summed_case_seconds,
                    throughput_cases_per_second=scenario.case_count / wall_seconds,
                )
            )
            print(
                f"{scenario.algorithm:13s} {scenario.scale_label:6s} "
                f"n={scenario.scale:<7d} cases={scenario.case_count:<3d} "
                f"workers={workers} repeat={repeat + 1}/{repeats} "
                f"wall={wall_seconds:.3f}s",
                flush=True,
            )
    return records


def summarize(records: list[RunRecord]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, int, int, int], list[RunRecord]] = {}
    for record in records:
        key = (
            record.algorithm,
            record.scale_label,
            record.scale,
            record.case_count,
            record.workers,
        )
        groups.setdefault(key, []).append(record)

    median_walls = {
        key: statistics.median(item.wall_seconds for item in items)
        for key, items in groups.items()
    }
    summary = []
    for key in sorted(groups):
        algorithm, scale_label, scale, case_count, workers = key
        items = groups[key]
        baseline_key = (algorithm, scale_label, scale, case_count, 1)
        wall = median_walls[key]
        baseline = median_walls[baseline_key]
        speedup = baseline / wall
        summary.append(
            {
                "algorithm": algorithm,
                "scale_label": scale_label,
                "scale": scale,
                "case_count": case_count,
                "workers": workers,
                "wall_median_seconds": wall,
                "wall_min_seconds": min(item.wall_seconds for item in items),
                "summed_case_median_seconds": statistics.median(
                    item.summed_case_seconds for item in items
                ),
                "throughput_median_cases_per_second": statistics.median(
                    item.throughput_cases_per_second for item in items
                ),
                "speedup": speedup,
                "parallel_efficiency": speedup / workers,
            }
        )
    return summary


def geometric_mean(values: list[float]) -> float:
    return math.exp(sum(math.log(value) for value in values) / len(values))


def write_outputs(
    records: list[RunRecord],
    summary: list[dict[str, Any]],
    repeats: int,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "python": sys.version,
        "platform": platform.platform(),
        "logical_cpu_count": os.cpu_count(),
        "tested_workers": list(WORKERS),
        "repeats": repeats,
        "measurement": "median wall time; process startup and JSON transport included",
    }
    json_path = OUTPUT_DIR / "parallel_scaling.json"
    json_path.write_text(
        json.dumps(
            {
                "metadata": metadata,
                "runs": [asdict(record) for record in records],
                "summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    csv_path = OUTPUT_DIR / "parallel_scaling.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)

    mean_speedups = {
        workers: geometric_mean(
            [item["speedup"] for item in summary if item["workers"] == workers]
        )
        for workers in WORKERS
    }
    speedup_text = "; ".join(
        f"{workers} workers = {mean_speedups[workers]:.2f}x"
        for workers in WORKERS
        if workers != 1
    )
    headers = ["Algorithm", "Scale", "n", "Cases", "1 worker (s)"]
    for workers in WORKERS:
        if workers != 1:
            headers.extend([f"{workers} workers (s)", f"{workers}x speedup"])
    lines = [
        "# SolutionRunner 1/2/4/6/8/12/16 worker benchmark",
        "",
        f"- Repeats: {repeats}; each value is the median wall time.",
        "- Includes process startup, source loading, JSON/shared-memory transport and result collection.",
        f"- Geometric-mean speedup: {speedup_text}.",
        "",
        "| " + " | ".join(headers) + " |",
        "|---|---:|---:|---:|---:|" + "---:|---:|" * (len(WORKERS) - 1),
    ]
    by_scenario: dict[tuple[str, str], dict[int, dict[str, Any]]] = {}
    for item in summary:
        by_scenario.setdefault(
            (item["algorithm"], item["scale_label"]), {}
        )[item["workers"]] = item
    for (algorithm, scale_label), values in by_scenario.items():
        one = values[1]
        row = [
            algorithm,
            scale_label,
            str(one["scale"]),
            str(one["case_count"]),
            f"{one['wall_median_seconds']:.3f}",
        ]
        for workers in WORKERS:
            if workers == 1:
                continue
            item = values[workers]
            row.extend(
                [f"{item['wall_median_seconds']:.3f}", f"{item['speedup']:.2f}x"]
            )
        lines.append("| " + " | ".join(row) + " |")
    markdown_path = OUTPUT_DIR / "parallel_scaling.md"
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nWrote {json_path}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {markdown_path}")
    print("Geometric-mean speedup: " + ", ".join(
        f"{workers} workers={mean_speedups[workers]:.3f}x"
        for workers in WORKERS
        if workers != 1
    ))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.repeats <= 0:
        parser.error("--repeats must be positive")
    logical_cpu_count = os.cpu_count() or 1
    if max(WORKERS) > logical_cpu_count:
        raise RuntimeError(
            f"benchmark requests {max(WORKERS)} workers on "
            f"{logical_cpu_count} logical processors"
        )

    all_records: list[RunRecord] = []
    with tempfile.TemporaryDirectory(prefix="parallel_benchmark_logs_") as log_dir:
        for index, scenario in enumerate(SCENARIOS, start=1):
            print(
                f"\n[{index}/{len(SCENARIOS)}] {scenario.algorithm}/"
                f"{scenario.scale_label}",
                flush=True,
            )
            all_records.extend(benchmark_scenario(scenario, args.repeats, log_dir))
    write_outputs(all_records, summarize(all_records), args.repeats)
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
