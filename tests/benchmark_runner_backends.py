"""Compare the legacy runner with the persistent mmap-backed runner.

The default matrix is intentionally bounded so it is safe to run on a normal
Windows desktop.  ``--include-million`` adds a one-million-case streaming test
for the persistent backend only; the legacy backend is skipped because every
legacy worker deserializes the complete test set.
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import multiprocessing
import os
import random
import statistics
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

from runtime.runner import CaseStoreWriter, NativeProcessRunner, PersistentPythonRunner
from runtime.runner.common import DIGEST_BACKEND, DIGEST_SCHEME, digest_value
from runtime.runner.native_process import DEFAULT_MANAGER
from tests.fixtures.benchmarks.classic_algorithms import Solution as BenchmarkSolution


ROOT = Path(__file__).resolve().parent.parent
SOLUTION_FILE = ROOT / "tests" / "fixtures" / "benchmarks" / "classic_algorithms.py"
OUTPUT_DIR = ROOT / "benchmark_results"
WORKERS = (1, 2, 4, 6, 8, 12, 16)
PYPY_EXECUTABLE = Path(r"C:\Users\john\anaconda3\envs\oj-pypy\python.exe")
REFERENCE_SOLUTION = BenchmarkSolution()


@dataclass(frozen=True)
class Scenario:
    name: str
    method: str
    case_count: int
    scale: int
    legacy_enabled: bool = True


@dataclass
class Measurement:
    scenario: str
    backend: str
    workers: int
    repeat: int
    wall_seconds: float
    throughput: float
    startup_seconds: float
    peak_worker_rss_bytes: int
    worker_compute_seconds: float
    worker_decode_seconds: float
    digest: str


DEFAULT_SCENARIOS = (
    Scenario("tiny_10k", "integer_mix", 10_000, 4),
    Scenario("tiny_100k", "integer_mix", 100_000, 4),
    Scenario("vector_10k", "vector_checksum", 10_000, 64),
    Scenario("lcs_128", "lcs_length", 128, 400),
)
MILLION_SCENARIO = Scenario(
    "tiny_1m", "integer_mix", 1_000_000, 4, legacy_enabled=False
)


def _random_text(size: int, seed: int) -> str:
    rng = random.Random(seed)
    return "".join(rng.choice("abcdefghijklmno") for _ in range(size))


def iter_cases(scenario: Scenario) -> Iterable[dict[str, Any]]:
    for index in range(scenario.case_count):
        if scenario.method == "integer_mix":
            case_input = (index * 2654435761, scenario.scale)
        elif scenario.method == "vector_checksum":
            case_input = ([((index + item * 17) % 2001) - 1000 for item in range(scenario.scale)],)
        elif scenario.method == "lcs_length":
            case_input = (
                _random_text(scenario.scale, index * 2 + 11),
                _random_text(scenario.scale, index * 2 + 12),
            )
        else:
            raise ValueError(scenario.method)
        expected = getattr(REFERENCE_SOLUTION, scenario.method)(*case_input)
        yield {"cid": index, "input": case_input, "expected": expected}


def _digest_result(index: int, cid: Any, output: Any, error: Any) -> int:
    return digest_value(index, cid, output, error)


def legacy_digest(results: list[dict[str, Any]]) -> str:
    digest = 0
    for index, result in enumerate(results):
        digest ^= _digest_result(
            index,
            result.get("cid", index),
            result.get("output"),
            result.get("error"),
        )
    return f"{digest:032x}"


def benchmark_scenario(
    scenario: Scenario,
    repeats: int,
    stores_dir: Path,
    backends: set[str],
    use_precomputed_digest: bool,
    worker_values: tuple[int, ...],
) -> list[Measurement]:
    store_path = stores_dir / f"{scenario.name}.ojbin"
    CaseStoreWriter.write(store_path, iter_cases(scenario))
    measurements: list[Measurement] = []
    expected_digest: str | None = None

    legacy_cases = (
        list(iter_cases(scenario))
        if scenario.legacy_enabled and "legacy" in backends
        else None
    )
    for workers in worker_values:
        if legacy_cases is not None and "legacy" in backends:
            from tools.solution_runner import SolutionRunner

            legacy = SolutionRunner(SOLUTION_FILE, main_method=scenario.method)
            for repeat in range(repeats):
                gc.collect()
                started = time.perf_counter()
                results = legacy.run(
                    legacy_cases,
                    log_wrong=False,
                    thread=workers,
                    timeout_s=None,
                    log_folder=str(stores_dir / "logs"),
                )
                wall = time.perf_counter() - started
                digest = legacy_digest(results)
                expected_digest = expected_digest or digest
                if digest != expected_digest:
                    raise AssertionError(
                        f"legacy digest mismatch: {scenario.name}/{workers}"
                    )
                measurements.append(
                    Measurement(
                        scenario.name,
                        "legacy_python",
                        workers,
                        repeat,
                        wall,
                        scenario.case_count / wall,
                        0.0,
                        0,
                        sum(float(item.get("elapsed", 0.0)) for item in results),
                        0.0,
                        digest,
                    )
                )

        if "persistent" in backends:
            with PersistentPythonRunner(
                SOLUTION_FILE,
                main_method=scenario.method,
                workers=workers,
                capture_stdout=False,
                standard_mode=True,
            ) as persistent:
                for repeat in range(repeats):
                    gc.collect()
                    report = persistent.run_store(
                        store_path,
                        collect_results=False,
                        use_precomputed_digest=use_precomputed_digest,
                    )
                    expected_digest = expected_digest or report.digest
                    if report.digest != expected_digest:
                        raise AssertionError(
                            f"persistent digest mismatch: {scenario.name}/{workers}"
                        )
                    measurements.append(
                        Measurement(
                            scenario.name,
                            report.metrics.backend,
                            workers,
                            repeat,
                            report.metrics.wall_seconds,
                            report.metrics.throughput_cases_per_second,
                            persistent.pool_startup_seconds,
                            report.metrics.peak_worker_rss_bytes,
                            report.metrics.worker_compute_seconds,
                            report.metrics.worker_decode_seconds,
                            report.digest,
                        )
                    )

        if DEFAULT_MANAGER.is_file() and backends.intersection(
            {"native-cpython", "native-pypy"}
        ):
            interpreters = []
            if "native-cpython" in backends:
                interpreters.append(("cpython", Path(os.sys.executable)))
            if "native-pypy" in backends and PYPY_EXECUTABLE.is_file():
                interpreters.append(("pypy", PYPY_EXECUTABLE))
            for _, interpreter in interpreters:
                native = NativeProcessRunner(
                    SOLUTION_FILE,
                    scenario.method,
                    workers=workers,
                    manager_path=DEFAULT_MANAGER,
                    python_executable=interpreter,
                    memory_limit_mb=512,
                    workspace=ROOT,
                    standard_mode=True,
                )
                for repeat in range(repeats):
                    gc.collect()
                    report = native.run_store(store_path)
                    expected_digest = expected_digest or report.digest
                    if report.digest != expected_digest:
                        raise AssertionError(
                            f"native digest mismatch: {scenario.name}/{workers}/"
                            f"{report.metrics.backend}"
                        )
                    measurements.append(
                        Measurement(
                            scenario.name,
                            report.metrics.backend,
                            workers,
                            repeat,
                            report.metrics.wall_seconds,
                            report.metrics.throughput_cases_per_second,
                            0.0,
                            report.metrics.peak_worker_rss_bytes,
                            report.metrics.worker_compute_seconds,
                            report.metrics.worker_decode_seconds,
                            report.digest,
                        )
                    )
        print(f"completed {scenario.name} with {workers} workers", flush=True)
    return measurements


def summarize(measurements: list[Measurement]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, int], list[Measurement]] = {}
    for item in measurements:
        groups.setdefault((item.scenario, item.backend, item.workers), []).append(item)
    summary = []
    for key in sorted(groups):
        scenario, backend, workers = key
        values = groups[key]
        summary.append(
            {
                "scenario": scenario,
                "backend": backend,
                "workers": workers,
                "wall_median_seconds": statistics.median(v.wall_seconds for v in values),
                "throughput_median": statistics.median(v.throughput for v in values),
                "startup_median_seconds": statistics.median(v.startup_seconds for v in values),
                "peak_worker_rss_bytes": max(v.peak_worker_rss_bytes for v in values),
                "worker_compute_median_seconds": statistics.median(
                    v.worker_compute_seconds for v in values
                ),
                "worker_decode_median_seconds": statistics.median(
                    v.worker_decode_seconds for v in values
                ),
                "digest": values[0].digest,
            }
        )
    lookup = {
        (item["scenario"], item["backend"], item["workers"]): item for item in summary
    }
    for item in summary:
        baseline = lookup.get((item["scenario"], item["backend"], 1))
        item["backend_speedup"] = (
            baseline["wall_median_seconds"] / item["wall_median_seconds"]
            if baseline
            else None
        )
        legacy = lookup.get((item["scenario"], "legacy_python", item["workers"]))
        item["vs_legacy_speedup"] = (
            legacy["wall_median_seconds"] / item["wall_median_seconds"]
            if legacy and item["backend"] != "legacy_python"
            else None
        )
    return summary


def write_outputs(
    measurements: list[Measurement],
    summary: list[dict[str, Any]],
    repeats: int,
    output_suffix: str,
    use_precomputed_digest: bool,
    worker_values: tuple[int, ...],
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe_suffix = "".join(
        character for character in output_suffix if character.isalnum() or character in "-_"
    )
    suffix = f"_{safe_suffix}" if safe_suffix else ""
    output_path = OUTPUT_DIR / f"runner_backend_comparison{suffix}.json"
    metadata = {
        "workers": list(worker_values),
        "repeats": repeats,
        "logical_cpus": os.cpu_count(),
        "process_limit": 16,
        "digest_backend": DIGEST_BACKEND,
        "digest_scheme": DIGEST_SCHEME,
        "use_precomputed_digest": use_precomputed_digest,
    }
    output_path.write_text(
        json.dumps(
            {
                "metadata": metadata,
                "measurements": [asdict(item) for item in measurements],
                "summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    write_markdown_output(output_path.with_suffix(".md"), metadata, summary)
    print(f"wrote {output_path}")


def write_markdown_output(
    output_path: Path,
    metadata: dict[str, Any],
    summary: list[dict[str, Any]],
) -> None:
    """Write a compact, reproducible scaling report beside the raw JSON."""

    backend_names = {
        "legacy_python": "Legacy Python",
        "persistent_cpython_standard": "Persistent CPython",
        "persistent_pypy_standard": "Persistent PyPy",
        "native_process_manager_standard_cpython": "C++ manager + CPython",
        "native_process_manager_standard_pypy": "C++ manager + PyPy",
    }
    lines = [
        "# Runner backend scaling",
        "",
        (
            f"- Workers: `{metadata['workers']}`; repeats: {metadata['repeats']}; "
            f"logical CPUs: {metadata['logical_cpus']}; configured maximum: "
            f"{metadata['process_limit']}."
        ),
        "- Each cell is `median wall seconds (speedup against the same backend at 1 worker)`.",
        "- Persistent rows are warm-pool timings; their one-time pool/source startup is reported separately.",
        "- Native and legacy rows include their per-run process startup; every row includes communication and result digest validation.",
    ]
    scenarios = list(dict.fromkeys(item["scenario"] for item in summary))
    workers = metadata["workers"]
    for scenario in scenarios:
        lines.extend(
            [
                "",
                f"## {scenario}",
                "",
                "| Backend | " + " | ".join(str(worker) for worker in workers) + " | Best | Pool startup at best | Peak RSS |",
                "|---|" + "---:|" * len(workers) + "---:|---:|---:|",
            ]
        )
        scenario_rows = [item for item in summary if item["scenario"] == scenario]
        by_backend: dict[str, dict[int, dict[str, Any]]] = {}
        for item in scenario_rows:
            by_backend.setdefault(item["backend"], {})[item["workers"]] = item
        for backend, rows in sorted(by_backend.items()):
            values = []
            for worker in workers:
                item = rows.get(worker)
                values.append(
                    "—"
                    if item is None
                    else (
                        f"{item['wall_median_seconds']:.4f} "
                        f"({item['backend_speedup']:.2f}×)"
                    )
                )
            best = min(rows.values(), key=lambda item: item["wall_median_seconds"])
            peak_rss = max(item["peak_worker_rss_bytes"] for item in rows.values())
            rss_label = "n/a" if not peak_rss else f"{peak_rss / 1024**2:.0f} MiB"
            startup = best["startup_median_seconds"]
            startup_label = "n/a" if not startup else f"{startup:.4f}s"
            lines.append(
                f"| {backend_names.get(backend, backend)} | "
                + " | ".join(values)
                + f" | {best['workers']} workers / {best['wall_median_seconds']:.4f}s"
                + f" | {startup_label} | {rss_label} |"
            )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--include-million", action="store_true")
    parser.add_argument("--scenario", action="append")
    parser.add_argument(
        "--backend",
        action="append",
        choices=("legacy", "persistent", "native-cpython", "native-pypy"),
    )
    parser.add_argument("--output-suffix", default="")
    parser.add_argument("--no-precomputed-digest", action="store_true")
    parser.add_argument("--workers", action="append", type=int, choices=WORKERS)
    args = parser.parse_args()
    if args.repeats <= 0:
        parser.error("--repeats must be positive")
    scenarios = list(DEFAULT_SCENARIOS)
    if args.include_million:
        scenarios.append(MILLION_SCENARIO)
    if args.scenario:
        selected = set(args.scenario)
        scenarios = [scenario for scenario in scenarios if scenario.name in selected]
        if not scenarios:
            parser.error("no scenario matched --scenario")
    backends = set(
        args.backend
        or ("legacy", "persistent", "native-cpython", "native-pypy")
    )
    worker_values = tuple(dict.fromkeys(args.workers or WORKERS))

    all_measurements: list[Measurement] = []
    with tempfile.TemporaryDirectory(prefix="runner_backend_benchmark_") as directory:
        stores_dir = Path(directory)
        for scenario in scenarios:
            all_measurements.extend(
                benchmark_scenario(
                    scenario,
                    args.repeats,
                    stores_dir,
                    backends,
                    not args.no_precomputed_digest,
                    worker_values,
                )
            )
    write_outputs(
        all_measurements,
        summarize(all_measurements),
        args.repeats,
        args.output_suffix,
        not args.no_precomputed_digest,
        worker_values,
    )
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
