"""Calibrate and validate the ``workers='auto'`` policy on this host.

The calibration is intentionally separate from unit tests: it launches up to
16 processes and should be run while the machine is otherwise reasonably idle.
It writes a machine-fingerprinted profile consumed by both persistent CPython
and compiled C/C++ runners.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

from runtime.runner import (
    AutoTuneConfig,
    CaseStoreWriter,
    CompiledCppRunner,
    PersistentPythonRunner,
)
from runtime.runner.auto_tune import (
    BackendProfile,
    DEFAULT_PROFILE_PATH,
    inspect_system,
    write_calibration_profile,
)


FIXTURES = ROOT / "tests" / "fixtures"
PYTHON_CLASSICS = FIXTURES / "benchmarks" / "classic_algorithms.py"
CPP_CLASSICS = FIXTURES / "cpp" / "classic_algorithms.cpp"
PYTHON_TLE = FIXTURES / "tle_solution.py"
CPP_TLE = FIXTURES / "cpp" / "hang_solution.cpp"
DEFAULT_OUTPUT = ROOT / "benchmark_results" / "auto_tune_calibration_final.json"


def _median(values: list[float]) -> float:
    return float(statistics.median(values))


def _smooth_startup(values: dict[int, float]) -> dict[int, float]:
    result: dict[int, float] = {}
    floor = 0.001
    for worker in sorted(values):
        floor = max(floor, values[worker])
        result[worker] = floor
    return result


def _efficiency(wall: dict[int, float], startup: dict[int, float]) -> dict[int, float]:
    phase_one = max(0.001, wall[1] - startup.get(1, 0.0))
    result = {1: 1.0}
    for worker in sorted(value for value in wall if value != 1):
        phase = max(0.001, wall[worker] - startup.get(worker, 0.0))
        # Keep each measured point independent. Real desktop scheduling can
        # have a local sweet spot; forcing a monotone curve lets one noisy
        # worker count incorrectly poison every larger candidate.
        result[worker] = min(1.0, max(0.08, phase_one / (worker * phase)))
    return result


def _write_stores(directory: Path) -> tuple[Path, Path, Path]:
    tiny = directory / "tiny.ojbin"
    python_heavy = directory / "python_heavy_lcs.ojbin"
    compiled_heavy = directory / "compiled_heavy_lcs.ojbin"
    CaseStoreWriter.write(
        tiny,
        (
            {
                "cid": index,
                "input": (index * 2_654_435_761, 4),
                "expected": _integer_mix(index * 2_654_435_761, 4),
            }
            for index in range(256)
        ),
    )
    text = "abcdefghijklmnop" * 16  # 256 characters, O(n^2) per case.
    CaseStoreWriter.write(
        python_heavy,
        (
            {"cid": index, "input": (text, text), "expected": len(text)}
            for index in range(256)
        ),
    )
    text = "abcdefghijklmnop" * 128  # Native workers need a larger signal.
    CaseStoreWriter.write(
        compiled_heavy,
        (
            {"cid": index, "input": (text, text), "expected": len(text)}
            for index in range(256)
        ),
    )
    return tiny, python_heavy, compiled_heavy


def _integer_mix(value: int, rounds: int) -> int:
    state = value & 0xFFFFFFFF
    for _ in range(rounds):
        state = (state * 1_664_525 + 1_013_904_223) & 0xFFFFFFFF
        state ^= state >> 13
    return state


def _calibrate_python(
    heavy_store: Path, workers: tuple[int, ...], repeats: int
) -> tuple[BackendProfile, list[dict[str, Any]]]:
    raw: list[dict[str, Any]] = []
    startup_samples: dict[int, list[float]] = {worker: [] for worker in workers}
    wall_samples: dict[int, list[float]] = {worker: [] for worker in workers}
    digest: str | None = None
    for worker in workers:
        for repeat in range(repeats):
            with PersistentPythonRunner(
                PYTHON_CLASSICS,
                main_method="lcs_length",
                workers=worker,
                capture_stdout=False,
                standard_mode=True,
            ) as runner:
                report = runner.run_store(
                    heavy_store, collect_results=False, profile_worker=True
                )
                digest = digest or report.digest
                if report.digest != digest:
                    raise AssertionError("persistent Python calibration digest mismatch")
                startup_samples[worker].append(runner.pool_startup_seconds)
                wall_samples[worker].append(report.metrics.wall_seconds)
                raw.append(
                    {
                        "backend": "persistent_python",
                        "workers": worker,
                        "repeat": repeat,
                        "startup_seconds": runner.pool_startup_seconds,
                        "wall_seconds": report.metrics.wall_seconds,
                        "compute_seconds": report.metrics.worker_compute_seconds,
                        "rss_bytes": report.metrics.peak_worker_rss_bytes,
                    }
                )
        print(f"calibrated persistent Python: {worker} workers", flush=True)
    startup = _smooth_startup(
        {worker: _median(values) for worker, values in startup_samples.items()}
    )
    wall = {worker: _median(values) for worker, values in wall_samples.items()}
    # The persistent pool startup is paid before RunMetrics.wall_seconds.
    phase_startup = {worker: 0.0 for worker in workers}
    return BackendProfile(startup, _efficiency(wall, phase_startup)), raw


def _calibrate_compiled(
    tiny_store: Path,
    heavy_store: Path,
    workers: tuple[int, ...],
    repeats: int,
) -> tuple[BackendProfile, list[dict[str, Any]]]:
    raw: list[dict[str, Any]] = []
    startup_samples: dict[int, list[float]] = {worker: [] for worker in workers}
    wall_samples: dict[int, list[float]] = {worker: [] for worker in workers}
    tiny_runner = CompiledCppRunner(
        CPP_CLASSICS, "integer_mix", workers=1, workspace=ROOT
    )
    heavy_runner = CompiledCppRunner(
        CPP_CLASSICS, "lcs_length", workers=1, workspace=ROOT
    )
    digest: str | None = None
    for worker in workers:
        for repeat in range(repeats):
            tiny = tiny_runner._run_store_with_workers(tiny_store, workers=worker)
            report = heavy_runner._run_store_with_workers(heavy_store, workers=worker)
            digest = digest or report.digest
            if report.digest != digest:
                raise AssertionError("compiled C++ calibration digest mismatch")
            startup_samples[worker].append(tiny.metrics.wall_seconds)
            wall_samples[worker].append(report.metrics.wall_seconds)
            raw.append(
                {
                    "backend": "compiled",
                    "workers": worker,
                    "repeat": repeat,
                    "startup_seconds": tiny.metrics.wall_seconds,
                    "wall_seconds": report.metrics.wall_seconds,
                    "compute_seconds": report.metrics.worker_compute_seconds,
                    "rss_bytes": report.metrics.peak_worker_rss_bytes,
                }
            )
        print(f"calibrated compiled C++: {worker} workers", flush=True)
    startup = _smooth_startup(
        {worker: _median(values) for worker, values in startup_samples.items()}
    )
    wall = {worker: _median(values) for worker, values in wall_samples.items()}
    return BackendProfile(startup, _efficiency(wall, startup)), raw


def _validate_auto(
    profile_path: Path, python_store: Path, compiled_store: Path
) -> dict[str, dict[str, Any]]:
    config = AutoTuneConfig(profile_path=profile_path, sample_cases=8)
    with PersistentPythonRunner(
        PYTHON_CLASSICS,
        main_method="lcs_length",
        workers="auto",
        capture_stdout=False,
        standard_mode=True,
        auto_tune_config=config,
    ) as runner:
        python_report = runner.run_store(python_store, collect_results=False)
    cpp_report = CompiledCppRunner(
        CPP_CLASSICS,
        "lcs_length",
        workers="auto",
        workspace=ROOT,
        auto_tune_config=config,
    ).run_store(compiled_store)
    return {
        "persistent_python": {
            "workers": python_report.metrics.workers,
            "wall_seconds": python_report.metrics.wall_seconds,
            "correct": python_report.correct_count,
            "decision": python_report.auto_tune,
        },
        "compiled": {
            "workers": cpp_report.metrics.workers,
            "wall_seconds": cpp_report.metrics.wall_seconds,
            "correct": cpp_report.correct_count,
            "decision": cpp_report.auto_tune,
        },
    }


def _validate_tle(profile_path: Path, directory: Path) -> dict[str, Any]:
    store = directory / "tle.ojbin"
    CaseStoreWriter.write(
        store, [{"cid": "hang", "input": (True, 7), "expected": 7}]
    )
    config = AutoTuneConfig(
        profile_path=profile_path, sample_cases=1, probe_timeout_s=0.15
    )
    with PersistentPythonRunner(
        PYTHON_TLE,
        main_method="work",
        workers="auto",
        standard_mode=True,
        auto_tune_config=config,
    ) as runner:
        python_report = runner.run_store(store, timeout_s=0.15)
    cpp_runner = CompiledCppRunner(
        CPP_TLE,
        "work",
        workers="auto",
        workspace=ROOT,
        auto_tune_config=config,
    )
    cpp_terminated = False
    started = time.perf_counter()
    try:
        cpp_runner.run_store(store, batch_timeout_s=0.2)
    except RuntimeError:
        cpp_terminated = True
    return {
        "python": {
            "workers": python_report.metrics.workers,
            "timed_out_cases": python_report.metrics.timed_out_cases,
            "probe_reason": python_report.auto_tune["reasons"],
        },
        "cpp": {
            "workers": cpp_runner.last_auto_tune.workers,
            "terminated": cpp_terminated,
            "elapsed_seconds": time.perf_counter() - started,
            "probe_reason": list(cpp_runner.last_auto_tune.reasons),
        },
    }


def calibrate(
    *,
    workers: tuple[int, ...],
    repeats: int,
    profile_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    if not workers or workers[0] != 1 or any(not 1 <= value <= 16 for value in workers):
        raise ValueError("workers must start with 1 and stay within 1..16")
    if repeats <= 0:
        raise ValueError("repeats must be positive")
    system = inspect_system()
    with tempfile.TemporaryDirectory(prefix="oj_auto_calibration_", dir=ROOT) as name:
        directory = Path(name)
        tiny_store, python_store, compiled_store = _write_stores(directory)
        python_profile, python_raw = _calibrate_python(
            python_store, workers, repeats
        )
        compiled_profile, compiled_raw = _calibrate_compiled(
            tiny_store, compiled_store, workers, repeats
        )
        write_calibration_profile(
            profile_path,
            system=system,
            backend_profiles={
                "persistent_python": python_profile,
                "compiled": compiled_profile,
            },
            metadata={"repeats": repeats, "workers": list(workers)},
        )
        auto_validation = _validate_auto(
            profile_path, python_store, compiled_store
        )
        tle_validation = _validate_tle(profile_path, directory)
    payload = {
        "schema_version": 1,
        "system": system.__dict__,
        "profile_path": str(profile_path.resolve()),
        "workers": list(workers),
        "repeats": repeats,
        "profiles": {
            "persistent_python": {
                "startup_seconds": python_profile.startup_seconds,
                "parallel_efficiency": python_profile.parallel_efficiency,
            },
            "compiled": {
                "startup_seconds": compiled_profile.startup_seconds,
                "parallel_efficiency": compiled_profile.parallel_efficiency,
            },
        },
        "raw_measurements": python_raw + compiled_raw,
        "auto_validation": auto_validation,
        "tle_validation": tle_validation,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", default="1,2,4,6,8,12,16")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    workers = tuple(sorted({int(value) for value in args.workers.split(",")}))
    result = calibrate(
        workers=workers,
        repeats=args.repeats,
        profile_path=args.profile,
        output_path=args.output,
    )
    print(json.dumps(result["auto_validation"], ensure_ascii=False, indent=2))
    print(f"profile: {Path(args.profile).resolve()}")
    print(f"report:  {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
