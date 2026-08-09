"""Benchmark compiled C/C++ OJ workers against persistent CPython.

All backends consume the same versioned ``.ojbin`` store generated from
language-neutral JSON cases. Compiled timings exclude compilation but include
the native manager and worker process startup; compilation and cache state are
reported separately.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import random
import statistics
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

from runtime.runner import CaseStoreWriter, CompiledCppRunner, PersistentPythonRunner
from tests.fixtures.benchmarks.classic_algorithms import Solution as ReferenceSolution


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "benchmark_results"
PYTHON_SOLUTION = ROOT / "tests" / "fixtures" / "benchmarks" / "classic_algorithms.py"
CPP_SOLUTION = ROOT / "tests" / "fixtures" / "cpp" / "classic_algorithms.cpp"
C_SOLUTION = ROOT / "tests" / "fixtures" / "c" / "integer_mix.c"
WORKERS = (1, 4, 8, 16)
REFERENCE = ReferenceSolution()


@dataclass(frozen=True)
class Scenario:
    name: str
    method: str
    case_count: int
    scale: int
    python_enabled: bool = True


@dataclass
class Measurement:
    scenario: str
    backend: str
    workers: int
    repeat: int
    wall_seconds: float
    throughput: float
    startup_seconds: float
    compile_seconds: float
    artifact_cache_hit: bool
    peak_worker_rss_bytes: int
    digest: str


SCENARIOS = (
    Scenario("integer_mix_10k", "integer_mix", 10_000, 4),
    Scenario("integer_mix_100k", "integer_mix", 100_000, 4),
    Scenario("vector_checksum_10k_n64", "vector_checksum", 10_000, 64),
    Scenario("binary_search_10k_n256", "binary_search", 10_000, 256),
    Scenario("sort_checksum_2k_n512", "sort_checksum", 2_000, 512),
    Scenario("sieve_count_512_n5k", "sieve_count", 512, 5_000),
    Scenario("lcs_128_n400", "lcs_length", 128, 400),
    # Same-string LCS keeps expected generation O(n), while the submitted
    # algorithm still performs its full O(n^2) DP. This isolates native
    # multi-process scaling without spending minutes in the Python reference.
    Scenario("lcs_8192_n400_compiled", "lcs_length", 8_192, 400, False),
    Scenario("matrix_64_n32", "matrix_multiply_checksum", 64, 32),
)
DEFAULT_SCENARIOS = tuple(scenario for scenario in SCENARIOS if scenario.python_enabled)


def _random_text(size: int, seed: int) -> str:
    generator = random.Random(seed)
    return "".join(generator.choice("abcdefghijklmno") for _ in range(size))


def iter_cases(scenario: Scenario) -> Iterable[dict[str, Any]]:
    for index in range(scenario.case_count):
        if scenario.method == "integer_mix":
            case_input = (index * 2654435761, scenario.scale)
        elif scenario.method == "vector_checksum":
            case_input = (
                [
                    ((index + item * 17) % 2001) - 1000
                    for item in range(scenario.scale)
                ],
            )
        elif scenario.method == "binary_search":
            values = [item * 2 - scenario.scale for item in range(scenario.scale)]
            target = values[index % len(values)] if index % 4 else scenario.scale * 3
            case_input = (values, target)
        elif scenario.method == "sort_checksum":
            case_input = (
                [
                    ((index * 97 + item * 7919) % 200_003) - 100_001
                    for item in range(scenario.scale)
                ],
            )
        elif scenario.method == "sieve_count":
            case_input = (scenario.scale + index % 251,)
        elif scenario.method == "lcs_length":
            left = _random_text(scenario.scale, index * 2 + 11)
            right = (
                left
                if scenario.name.endswith("_compiled")
                else _random_text(scenario.scale, index * 2 + 12)
            )
            case_input = (left, right)
        elif scenario.method == "matrix_multiply_checksum":
            case_input = (scenario.scale, index % 19)
        else:
            raise ValueError(scenario.method)
        expected = (
            scenario.scale
            if scenario.name == "lcs_8192_n400_compiled"
            else getattr(REFERENCE, scenario.method)(*case_input)
        )
        yield {"cid": index, "input": case_input, "expected": expected}


def benchmark_scenario(
    scenario: Scenario,
    store_path: Path,
    repeats: int,
    worker_values: tuple[int, ...],
    backends: set[str],
    force_rebuild: bool,
    rebuilt_methods: set[tuple[str, str]],
) -> list[Measurement]:
    measurements: list[Measurement] = []
    expected_digest: str | None = None
    backend_sources = []
    if "cpp" in backends:
        backend_sources.append(("cpp", CPP_SOLUTION))
    if "c" in backends and scenario.method == "integer_mix":
        backend_sources.append(("c", C_SOLUTION))

    for workers in worker_values:
        if "python" in backends and scenario.python_enabled:
            with PersistentPythonRunner(
                PYTHON_SOLUTION,
                main_method=scenario.method,
                workers=workers,
                capture_stdout=False,
                standard_mode=True,
            ) as runner:
                for repeat in range(repeats):
                    report = runner.run_store(store_path, collect_results=False)
                    expected_digest = expected_digest or report.digest
                    if report.digest != expected_digest:
                        raise AssertionError(
                            f"Python digest mismatch: {scenario.name}/{workers}"
                        )
                    measurements.append(
                        Measurement(
                            scenario.name,
                            report.metrics.backend,
                            workers,
                            repeat,
                            report.metrics.wall_seconds,
                            report.metrics.throughput_cases_per_second,
                            runner.pool_startup_seconds,
                            0.0,
                            False,
                            report.metrics.peak_worker_rss_bytes,
                            report.digest,
                        )
                    )

        for language, source in backend_sources:
            rebuild_key = (language, scenario.method)
            rebuild = force_rebuild and rebuild_key not in rebuilt_methods
            runner = CompiledCppRunner(
                source,
                scenario.method,
                workers=workers,
                workspace=ROOT,
                force_rebuild=rebuild,
            )
            rebuilt_methods.add(rebuild_key)
            for repeat in range(repeats):
                report = runner.run_store(store_path)
                expected_digest = expected_digest or report.digest
                if report.digest != expected_digest:
                    raise AssertionError(
                        f"{language} digest mismatch: {scenario.name}/{workers}"
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
                        report.metrics.compile_seconds if repeat == 0 else 0.0,
                        report.metrics.artifact_cache_hit,
                        report.metrics.peak_worker_rss_bytes,
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
    for (scenario, backend, workers), values in sorted(groups.items()):
        summary.append(
            {
                "scenario": scenario,
                "backend": backend,
                "workers": workers,
                "wall_median_seconds": statistics.median(
                    value.wall_seconds for value in values
                ),
                "throughput_median": statistics.median(
                    value.throughput for value in values
                ),
                "startup_seconds": max(value.startup_seconds for value in values),
                "compile_seconds": max(value.compile_seconds for value in values),
                "peak_worker_rss_bytes": max(
                    value.peak_worker_rss_bytes for value in values
                ),
                "digest": values[0].digest,
            }
        )
    lookup = {
        (item["scenario"], item["backend"], item["workers"]): item
        for item in summary
    }
    for item in summary:
        baseline = lookup.get((item["scenario"], item["backend"], 1))
        item["backend_speedup"] = (
            baseline["wall_median_seconds"] / item["wall_median_seconds"]
            if baseline
            else None
        )
        python = lookup.get(
            (item["scenario"], "persistent_cpython_standard", item["workers"])
        )
        item["vs_python_speedup"] = (
            python["wall_median_seconds"] / item["wall_median_seconds"]
            if python and item["backend"] != "persistent_cpython_standard"
            else None
        )
    return summary


def write_outputs(
    measurements: list[Measurement],
    summary: list[dict[str, Any]],
    repeats: int,
    workers: tuple[int, ...],
    suffix: str,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe_suffix = "".join(
        character for character in suffix if character.isalnum() or character in "-_"
    )
    appendix = f"_{safe_suffix}" if safe_suffix else ""
    path = OUTPUT_DIR / f"compiled_language_scaling{appendix}.json"
    metadata = {
        "workers": list(workers),
        "repeats": repeats,
        "logical_cpus": os.cpu_count(),
        "process_limit": 16,
        "compiled_wall_excludes_compilation": True,
        "compiled_wall_includes_manager_and_worker_startup": True,
    }
    path.write_text(
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

    lines = [
        "# C/C++ and Python OJ scaling",
        "",
        f"Workers: `{list(workers)}`; repeats: `{repeats}`.",
        "Compiled wall time excludes compilation and includes native process startup.",
    ]
    for scenario in dict.fromkeys(item["scenario"] for item in summary):
        lines.extend(
            [
                "",
                f"## {scenario}",
                "",
                "| Backend | "
                + " | ".join(str(worker) for worker in workers)
                + " | Compile |",
                "|---|" + "---:|" * len(workers) + "---:|",
            ]
        )
        rows: dict[str, dict[int, dict[str, Any]]] = {}
        for item in summary:
            if item["scenario"] == scenario:
                rows.setdefault(item["backend"], {})[item["workers"]] = item
        for backend, values in sorted(rows.items()):
            cells = []
            for worker in workers:
                item = values.get(worker)
                cells.append(
                    "—"
                    if item is None
                    else f"{item['wall_median_seconds']:.4f}s ({item['backend_speedup']:.2f}×)"
                )
            compile_seconds = max(
                item["compile_seconds"] for item in values.values()
            )
            lines.append(
                f"| {backend} | "
                + " | ".join(cells)
                + f" | {compile_seconds:.3f}s |"
            )
    path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--scenario", action="append")
    parser.add_argument("--backend", action="append", choices=("python", "cpp", "c"))
    parser.add_argument("--workers", action="append", type=int, choices=WORKERS)
    parser.add_argument("--force-rebuild", action="store_true")
    parser.add_argument("--output-suffix", default="")
    args = parser.parse_args()
    if args.repeats <= 0:
        parser.error("--repeats must be positive")
    selected_scenarios = list(DEFAULT_SCENARIOS)
    if args.scenario:
        names = set(args.scenario)
        selected_scenarios = [item for item in SCENARIOS if item.name in names]
        if not selected_scenarios:
            parser.error("no scenario matched --scenario")
    backends = set(args.backend or ("python", "cpp", "c"))
    worker_values = tuple(dict.fromkeys(args.workers or WORKERS))
    measurements: list[Measurement] = []
    rebuilt_methods: set[tuple[str, str]] = set()
    with tempfile.TemporaryDirectory(prefix="compiled_benchmark_") as directory:
        stores = Path(directory)
        for scenario in selected_scenarios:
            store = stores / f"{scenario.name}.ojbin"
            CaseStoreWriter.write(store, iter_cases(scenario))
            measurements.extend(
                benchmark_scenario(
                    scenario,
                    store,
                    args.repeats,
                    worker_values,
                    backends,
                    args.force_rebuild,
                    rebuilt_methods,
                )
            )
    write_outputs(
        measurements,
        summarize(measurements),
        args.repeats,
        worker_values,
        args.output_suffix,
    )
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
