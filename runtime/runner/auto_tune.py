from __future__ import annotations

import ast
import json
import math
import os
import platform
import re
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .case_store import CaseStoreReader, CaseStoreWriter


GIB = 1024**3
PROFILE_SCHEMA_VERSION = 1
DEFAULT_PROFILE_PATH = Path(__file__).resolve().parents[2] / "build" / "auto_tune" / "host_profile.json"
DEFAULT_CANDIDATES = (1, 2, 4, 6, 8, 12, 16)


@dataclass(frozen=True)
class AutoTuneConfig:
    max_workers: int = 16
    memory_budget_bytes: int = 8 * GIB
    reserve_logical_cpus: int | None = None
    sample_cases: int = 8
    probe_timeout_s: float = 0.35
    expected_runs: int = 1
    min_cases_per_worker: int = 4
    candidates: tuple[int, ...] = DEFAULT_CANDIDATES
    profile_path: Path | None = DEFAULT_PROFILE_PATH
    enable_probe: bool = True

    def __post_init__(self) -> None:
        if not 1 <= self.max_workers <= 16:
            raise ValueError("max_workers must be between 1 and 16")
        if self.memory_budget_bytes <= 0:
            raise ValueError("memory_budget_bytes must be positive")
        if self.sample_cases <= 0:
            raise ValueError("sample_cases must be positive")
        if self.probe_timeout_s <= 0:
            raise ValueError("probe_timeout_s must be positive")
        if self.expected_runs <= 0:
            raise ValueError("expected_runs must be positive")
        if self.min_cases_per_worker <= 0:
            raise ValueError("min_cases_per_worker must be positive")
        if self.reserve_logical_cpus is not None and self.reserve_logical_cpus < 0:
            raise ValueError("reserve_logical_cpus cannot be negative")
        if not self.candidates or any(worker <= 0 for worker in self.candidates):
            raise ValueError("candidates must contain positive worker counts")


@dataclass(frozen=True)
class SystemFeatures:
    logical_cpus: int
    physical_cpus: int
    total_memory_bytes: int
    available_memory_bytes: int
    cpu_load_percent: float
    platform: str

    @property
    def fingerprint(self) -> str:
        return (
            f"{self.platform}|logical={self.logical_cpus}|physical={self.physical_cpus}"
            f"|memory_gib={round(self.total_memory_bytes / GIB)}"
        )


@dataclass(frozen=True)
class StoreFeatures:
    case_count: int
    file_size_bytes: int
    sampled_cases: int
    average_input_bytes: float
    p95_input_bytes: float
    maximum_input_bytes: int
    expected_fraction: float


@dataclass(frozen=True)
class ProgramFeatures:
    language: str
    source_bytes: int
    loop_count: int
    maximum_loop_depth: int
    branch_count: int
    recursive: bool
    complexity_score: float


@dataclass(frozen=True)
class AutoTuneProbe:
    backend_family: str
    sample_cases: int
    wall_seconds: float
    compute_seconds: float
    decode_seconds: float
    peak_rss_bytes: int
    timed_out: bool = False
    error: str | None = None


@dataclass(frozen=True)
class BackendProfile:
    startup_seconds: dict[int, float]
    parallel_efficiency: dict[int, float]


@dataclass(frozen=True)
class AutoTuneDecision:
    workers: int
    backend_family: str
    candidate_workers: tuple[int, ...]
    predicted_wall_seconds: dict[int, float]
    memory_limited_workers: int
    cpu_limited_workers: int
    estimated_total_compute_seconds: float
    estimated_total_decode_seconds: float
    reasons: tuple[str, ...]
    system: SystemFeatures
    store: StoreFeatures
    program: ProgramFeatures
    probe: AutoTuneProbe | None = None
    profile_source: str = "builtin"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["predicted_wall_seconds"] = {
            str(worker): seconds
            for worker, seconds in self.predicted_wall_seconds.items()
        }
        return payload


_BUILTIN_PROFILES = {
    "compiled": BackendProfile(
        startup_seconds={1: 0.030, 2: 0.034, 4: 0.042, 6: 0.050, 8: 0.060, 12: 0.080, 16: 0.100},
        parallel_efficiency={1: 1.00, 2: 0.92, 4: 0.78, 6: 0.69, 8: 0.60, 12: 0.46, 16: 0.34},
    ),
    "persistent_python": BackendProfile(
        startup_seconds={1: 0.080, 2: 0.140, 4: 0.250, 6: 0.350, 8: 0.460, 12: 0.670, 16: 0.880},
        parallel_efficiency={1: 1.00, 2: 0.90, 4: 0.80, 6: 0.72, 8: 0.64, 12: 0.50, 16: 0.40},
    ),
}


def inspect_system() -> SystemFeatures:
    logical = os.cpu_count() or 1
    physical = max(1, logical // 2)
    total_memory = available_memory = 8 * GIB
    cpu_load = 0.0
    try:
        import psutil

        physical = psutil.cpu_count(logical=False) or physical
        memory = psutil.virtual_memory()
        total_memory = int(memory.total)
        available_memory = int(memory.available)
        cpu_load = float(psutil.cpu_percent(interval=0.05))
    except Exception:
        # psutil is optional and can also be denied by a restricted token.
        pass
    return SystemFeatures(
        logical_cpus=logical,
        physical_cpus=physical,
        total_memory_bytes=total_memory,
        available_memory_bytes=available_memory,
        cpu_load_percent=cpu_load,
        platform=f"{platform.system()}-{platform.machine()}",
    )


def sample_indices(case_count: int, limit: int) -> tuple[int, ...]:
    if case_count <= 0:
        return ()
    count = min(case_count, limit)
    if count == 1:
        return (0,)
    return tuple(
        sorted(
            {
                min(case_count - 1, round(index * (case_count - 1) / (count - 1)))
                for index in range(count)
            }
        )
    )


def inspect_store(store_path: os.PathLike[str] | str, sample_limit: int = 32) -> StoreFeatures:
    path = Path(store_path).resolve()
    sizes: list[int] = []
    expected = 0
    with CaseStoreReader(path) as reader:
        count = len(reader)
        for index in sample_indices(count, sample_limit):
            case = reader[index]
            encoded = json.dumps(
                case["input"],
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
            sizes.append(len(encoded))
            expected += int("expected" in case)
    if not sizes:
        sizes = [0]
    sorted_sizes = sorted(sizes)
    p95_index = min(len(sorted_sizes) - 1, math.ceil(len(sorted_sizes) * 0.95) - 1)
    return StoreFeatures(
        case_count=count,
        file_size_bytes=path.stat().st_size,
        sampled_cases=min(count, sample_limit),
        average_input_bytes=statistics.fmean(sizes),
        p95_input_bytes=float(sorted_sizes[p95_index]),
        maximum_input_bytes=max(sizes),
        expected_fraction=(expected / min(count, sample_limit) if count else 0.0),
    )


def _python_loop_depth(tree: ast.AST) -> int:
    maximum = 0

    def visit(node: ast.AST, depth: int) -> None:
        nonlocal maximum
        is_loop = isinstance(node, (ast.For, ast.AsyncFor, ast.While))
        next_depth = depth + int(is_loop)
        maximum = max(maximum, next_depth)
        for child in ast.iter_child_nodes(node):
            visit(child, next_depth)

    visit(tree, 0)
    return maximum


def inspect_program(source: str, language: str, method_name: str | None = None) -> ProgramFeatures:
    if language == "python":
        try:
            tree = ast.parse(source)
        except SyntaxError:
            tree = ast.Module(body=[], type_ignores=[])
        loops = sum(isinstance(node, (ast.For, ast.AsyncFor, ast.While)) for node in ast.walk(tree))
        branches = sum(isinstance(node, (ast.If, ast.IfExp, ast.Match)) for node in ast.walk(tree))
        maximum_depth = _python_loop_depth(tree)
        recursive = bool(
            method_name
            and any(
                isinstance(node, ast.Call)
                and (
                    isinstance(node.func, ast.Name)
                    and node.func.id == method_name
                    or isinstance(node.func, ast.Attribute)
                    and node.func.attr == method_name
                )
                for node in ast.walk(tree)
            )
        )
    else:
        masked = _mask_c_like(source)
        loops = len(re.findall(r"\b(?:for|while)\s*\(", masked))
        branches = len(re.findall(r"\b(?:if|switch)\s*\(", masked))
        maximum_depth = _c_like_loop_depth(masked)
        recursive = bool(
            method_name
            and len(re.findall(rf"\b{re.escape(method_name)}\s*\(", masked)) > 1
        )
    complexity = 1.0 + loops * 0.35 + maximum_depth**2 * 1.5 + branches * 0.08
    if recursive:
        complexity *= 2.0
    return ProgramFeatures(
        language=language,
        source_bytes=len(source.encode("utf-8")),
        loop_count=loops,
        maximum_loop_depth=maximum_depth,
        branch_count=branches,
        recursive=recursive,
        complexity_score=complexity,
    )


def _mask_c_like(source: str) -> str:
    result = re.sub(r"//[^\n]*", "", source)
    result = re.sub(r"/\*.*?\*/", "", result, flags=re.DOTALL)
    result = re.sub(r'"(?:\\.|[^"\\])*"', '""', result)
    result = re.sub(r"'(?:\\.|[^'\\])*'", "''", result)
    return result


def _c_like_loop_depth(source: str) -> int:
    pending_loop = False
    stack: list[bool] = []
    depth = maximum = 0
    tokens = re.finditer(r"\b(?:for|while)\b|[{}]", source)
    for token in tokens:
        value = token.group(0)
        if value in {"for", "while"}:
            pending_loop = True
        elif value == "{":
            stack.append(pending_loop)
            if pending_loop:
                depth += 1
                maximum = max(maximum, depth)
            pending_loop = False
        elif value == "}":
            if stack and stack.pop():
                depth -= 1
            pending_loop = False
    return maximum


def create_probe_store(
    source_store: os.PathLike[str] | str,
    destination: os.PathLike[str] | str,
    sample_limit: int,
) -> int:
    with CaseStoreReader(source_store) as reader:
        indices = sample_indices(len(reader), sample_limit)
        cases = (reader[index] for index in indices)
        CaseStoreWriter.write(destination, cases)
    return len(indices)


def _profile_from_json(payload: dict[str, Any], backend_family: str) -> BackendProfile | None:
    backend = payload.get("backends", {}).get(backend_family)
    if not isinstance(backend, dict):
        return None
    try:
        startup = {int(key): float(value) for key, value in backend["startup_seconds"].items()}
        efficiency = {
            int(key): float(value)
            for key, value in backend["parallel_efficiency"].items()
        }
    except (KeyError, TypeError, ValueError):
        return None
    if (
        not startup
        or not efficiency
        or any(value < 0 for value in startup.values())
        or any(not 0 < value <= 1 for value in efficiency.values())
    ):
        return None
    return BackendProfile(startup, efficiency)


def load_backend_profile(
    config: AutoTuneConfig,
    backend_family: str,
    system: SystemFeatures,
) -> tuple[BackendProfile, str]:
    path = config.profile_path
    if path is not None and Path(path).is_file():
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            if (
                payload.get("schema_version") == PROFILE_SCHEMA_VERSION
                and payload.get("machine_fingerprint") == system.fingerprint
            ):
                profile = _profile_from_json(payload, backend_family)
                if profile is not None:
                    return profile, str(Path(path).resolve())
        except (OSError, json.JSONDecodeError):
            pass
    return _BUILTIN_PROFILES[backend_family], "builtin"


def _interpolate(values: dict[int, float], worker: int) -> float:
    if worker in values:
        return values[worker]
    keys = sorted(values)
    lower = max((key for key in keys if key < worker), default=keys[0])
    upper = min((key for key in keys if key > worker), default=keys[-1])
    if lower == upper:
        return values[lower]
    fraction = (worker - lower) / (upper - lower)
    return values[lower] + fraction * (values[upper] - values[lower])


def select_workers(
    *,
    backend_family: str,
    system: SystemFeatures,
    store: StoreFeatures,
    program: ProgramFeatures,
    config: AutoTuneConfig,
    probe: AutoTuneProbe | None = None,
    worker_memory_limit_bytes: int = 0,
) -> AutoTuneDecision:
    if backend_family not in _BUILTIN_PROFILES:
        raise ValueError(f"unsupported auto-tune backend: {backend_family}")
    reasons: list[str] = []
    reserve = config.reserve_logical_cpus
    if reserve is None:
        reserve = max(1, min(4, system.logical_cpus // 6))
    cpu_cap = max(1, system.logical_cpus - reserve)
    cpu_cap = min(cpu_cap, system.physical_cpus + max(1, system.physical_cpus // 3))
    cpu_cap = min(cpu_cap, config.max_workers)
    if system.cpu_load_percent >= 80.0:
        cpu_cap = max(1, min(cpu_cap, system.physical_cpus // 2))
        reasons.append("high_current_cpu_load")

    memory_budget = min(
        config.memory_budget_bytes,
        max(64 * 1024**2, int(system.available_memory_bytes * 0.75)),
    )
    default_worker_rss = 24 * 1024**2 if backend_family == "compiled" else 96 * 1024**2
    worker_rss = max(
        8 * 1024**2,
        probe.peak_rss_bytes if probe and probe.peak_rss_bytes else default_worker_rss,
        worker_memory_limit_bytes,
    )
    memory_cap = max(1, memory_budget // worker_rss)
    cases_per_worker = config.min_cases_per_worker
    if probe and probe.sample_cases > 0 and not probe.timed_out:
        measured_per_case = probe.compute_seconds / probe.sample_cases
        if measured_per_case >= 0.050:
            cases_per_worker = 1
        elif measured_per_case >= 0.010:
            cases_per_worker = min(cases_per_worker, 2)
    case_cap = max(1, math.ceil(store.case_count / cases_per_worker))
    hard_cap = min(cpu_cap, memory_cap, case_cap, config.max_workers)
    candidates = tuple(
        sorted(
            {
                1,
                *(worker for worker in config.candidates if worker <= hard_cap),
                hard_cap,
            }
        )
    )

    profile, profile_source = load_backend_profile(config, backend_family, system)
    if probe and probe.timed_out:
        reasons.extend(("probe_timed_out", "single_worker_limits_resource_blast_radius"))
        return AutoTuneDecision(
            workers=1,
            backend_family=backend_family,
            candidate_workers=candidates,
            predicted_wall_seconds={1: probe.wall_seconds},
            memory_limited_workers=memory_cap,
            cpu_limited_workers=cpu_cap,
            estimated_total_compute_seconds=probe.compute_seconds,
            estimated_total_decode_seconds=0.0,
            reasons=tuple(reasons),
            system=system,
            store=store,
            program=program,
            probe=probe,
            profile_source=profile_source,
        )

    if probe and probe.sample_cases > 0 and probe.error is None:
        scale = store.case_count / probe.sample_cases
        total_compute = max(0.0, probe.compute_seconds * scale)
        total_decode = max(0.0, probe.decode_seconds * scale)
        observed_startup = max(
            0.0, probe.wall_seconds - probe.compute_seconds - probe.decode_seconds
        )
        reasons.append("measured_representative_cases")
    else:
        language_factor = 2.0e-8 if backend_family == "compiled" else 8.0e-8
        total_compute = (
            store.case_count
            * max(1.0, store.average_input_bytes)
            * program.complexity_score
            * language_factor
        )
        total_decode = store.case_count * store.average_input_bytes * 1.2e-8
        observed_startup = 0.0
        reasons.append(
            "probe_failed_static_fallback"
            if probe and probe.error
            else "static_program_estimate"
        )

    predictions: dict[int, float] = {}
    for worker in candidates:
        startup = _interpolate(profile.startup_seconds, worker)
        if worker == 1 and observed_startup:
            startup = max(startup * 0.5, observed_startup)
        efficiency = max(0.05, min(1.0, _interpolate(profile.parallel_efficiency, worker)))
        predictions[worker] = (
            startup / config.expected_runs
            + total_compute / (worker * efficiency)
            + total_decode / (worker * max(0.50, efficiency))
        )
    selected = min(predictions, key=lambda worker: (predictions[worker], worker))
    best = predictions[selected]
    one = predictions.get(1, best)
    if selected != 1 and best > one * 0.95:
        selected = 1
        reasons.append("parallel_gain_below_five_percent")
    if selected == 1:
        reasons.append("startup_or_workload_favors_single_worker")
    else:
        reasons.append("predicted_parallel_wall_time_is_lower")
    if hard_cap == memory_cap:
        reasons.append("memory_budget_applied")
    if hard_cap == cpu_cap:
        reasons.append("desktop_cpu_reserve_applied")
    if hard_cap == case_cap:
        reasons.append("case_count_limits_workers")
    return AutoTuneDecision(
        workers=selected,
        backend_family=backend_family,
        candidate_workers=candidates,
        predicted_wall_seconds=predictions,
        memory_limited_workers=memory_cap,
        cpu_limited_workers=cpu_cap,
        estimated_total_compute_seconds=total_compute,
        estimated_total_decode_seconds=total_decode,
        reasons=tuple(reasons),
        system=system,
        store=store,
        program=program,
        probe=probe,
        profile_source=profile_source,
    )


def write_calibration_profile(
    path: os.PathLike[str] | str,
    *,
    system: SystemFeatures,
    backend_profiles: dict[str, BackendProfile],
    metadata: dict[str, Any] | None = None,
) -> Path:
    destination = Path(path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "machine_fingerprint": system.fingerprint,
        "system": asdict(system),
        "backends": {
            name: {
                "startup_seconds": {
                    str(worker): seconds
                    for worker, seconds in profile.startup_seconds.items()
                },
                "parallel_efficiency": {
                    str(worker): efficiency
                    for worker, efficiency in profile.parallel_efficiency.items()
                },
            }
            for name, profile in backend_profiles.items()
        },
        "metadata": metadata or {},
    }
    temporary = destination.with_suffix(destination.suffix + ".writing")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(temporary, destination)
    return destination


__all__ = [
    "AutoTuneConfig",
    "AutoTuneDecision",
    "AutoTuneProbe",
    "BackendProfile",
    "ProgramFeatures",
    "StoreFeatures",
    "SystemFeatures",
    "create_probe_store",
    "inspect_program",
    "inspect_store",
    "inspect_system",
    "select_workers",
    "write_calibration_profile",
]
