"""Paired A/B benchmark for framework-only Runtime optimizations.

The two modes execute in the same persistent worker pool and alternate order on
every repeat.  This reduces the effect of process startup, temperature, and
background Windows activity when deciding whether an optimization regresses a
CPU-heavy OJ workload.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import statistics
import tempfile
from pathlib import Path
from typing import Any

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

from runtime.runner import CaseStoreWriter, PersistentPythonRunner
from runtime.runner.common import DIGEST_BACKEND, DIGEST_SCHEME
from tests.benchmark_runner_backends import DEFAULT_SCENARIOS, SOLUTION_FILE, iter_cases


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "benchmark_results"
WORKERS = (1, 4, 8, 16)
MODES = {
    "full_digest_profiled": {
        "use_precomputed_digest": False,
        "profile_worker": True,
    },
    "phase_a": {
        "use_precomputed_digest": True,
        "profile_worker": False,
    },
}


def benchmark(
    scenario_name: str,
    repeats: int,
    worker_values: tuple[int, ...],
) -> dict[str, Any]:
    scenario = next(item for item in DEFAULT_SCENARIOS if item.name == scenario_name)
    measurements: list[dict[str, Any]] = []
    expected_digest: str | None = None

    with tempfile.TemporaryDirectory(prefix="runtime_accel_benchmark_") as directory:
        store_path = Path(directory) / f"{scenario.name}.ojbin"
        CaseStoreWriter.write(store_path, iter_cases(scenario))
        for workers in worker_values:
            with PersistentPythonRunner(
                SOLUTION_FILE,
                main_method=scenario.method,
                workers=workers,
                capture_stdout=False,
                standard_mode=True,
            ) as runner:
                # Populate imports, mmap pages, and worker-side caches before timing.
                warmup = runner.run_store(
                    store_path,
                    collect_results=False,
                    **MODES["phase_a"],
                )
                expected_digest = expected_digest or warmup.digest
                if warmup.digest != expected_digest:
                    raise AssertionError("warm-up result digest mismatch")

                for repeat in range(repeats):
                    order = (
                        ("full_digest_profiled", "phase_a")
                        if repeat % 2 == 0
                        else ("phase_a", "full_digest_profiled")
                    )
                    for sequence, mode in enumerate(order):
                        report = runner.run_store(
                            store_path,
                            collect_results=False,
                            **MODES[mode],
                        )
                        if report.digest != expected_digest:
                            raise AssertionError(
                                f"result digest mismatch: {workers}/{repeat}/{mode}"
                            )
                        measurements.append(
                            {
                                "workers": workers,
                                "repeat": repeat,
                                "sequence": sequence,
                                "mode": mode,
                                "wall_seconds": report.metrics.wall_seconds,
                                "throughput": report.metrics.throughput_cases_per_second,
                                "worker_compute_seconds": (
                                    report.metrics.worker_compute_seconds
                                ),
                                "worker_decode_seconds": report.metrics.worker_decode_seconds,
                                "digest": report.digest,
                            }
                        )
            print(f"completed paired {scenario.name} with {workers} workers", flush=True)

    summary = []
    for workers in worker_values:
        by_mode: dict[str, dict[str, Any]] = {}
        for mode in MODES:
            values = [
                item["wall_seconds"]
                for item in measurements
                if item["workers"] == workers and item["mode"] == mode
            ]
            by_mode[mode] = {
                "median_seconds": statistics.median(values),
                "min_seconds": min(values),
                "max_seconds": max(values),
            }
        baseline = by_mode["full_digest_profiled"]["median_seconds"]
        optimized = by_mode["phase_a"]["median_seconds"]
        summary.append(
            {
                "workers": workers,
                **by_mode,
                "phase_a_speedup": baseline / optimized,
                "phase_a_change_percent": (baseline / optimized - 1.0) * 100.0,
            }
        )
    return {
        "metadata": {
            "scenario": scenario.name,
            "case_count": scenario.case_count,
            "workers": list(worker_values),
            "repeats": repeats,
            "logical_cpus": os.cpu_count(),
            "process_limit": 16,
            "paired_alternating_order": True,
            "warm_pool": True,
            "digest_backend": DIGEST_BACKEND,
            "digest_scheme": DIGEST_SCHEME,
            "modes": MODES,
        },
        "measurements": measurements,
        "summary": summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="lcs_128")
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--workers", action="append", type=int, choices=WORKERS)
    parser.add_argument("--output-suffix", default="")
    args = parser.parse_args()
    if args.repeats <= 0:
        parser.error("--repeats must be positive")
    if args.scenario not in {item.name for item in DEFAULT_SCENARIOS}:
        parser.error(f"unknown scenario: {args.scenario}")
    worker_values = tuple(dict.fromkeys(args.workers or WORKERS))
    payload = benchmark(args.scenario, args.repeats, worker_values)

    safe_suffix = "".join(
        character
        for character in args.output_suffix
        if character.isalnum() or character in "-_"
    )
    suffix = f"_{safe_suffix}" if safe_suffix else ""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"runtime_accel_paired{suffix}.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
