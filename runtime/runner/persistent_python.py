from __future__ import annotations

import contextlib
import ctypes
import json
import math
import multiprocessing
import os
import platform
import queue
import sys
import tempfile
import time
import traceback
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .case_store import CaseStoreReader, CaseStoreWriter
from .common import BoundedWriter as _BoundedWriter
from .common import digest_value as _digest_value
from .models import RunMetrics, RunReport


MAX_WORKERS = 16


class _WorkerStatus(ctypes.Structure):
    _fields_ = [
        ("run_id", ctypes.c_longlong),
        ("task_id", ctypes.c_longlong),
        ("case_index", ctypes.c_longlong),
        ("started_at", ctypes.c_double),
    ]


@dataclass(frozen=True)
class _WorkerSpec:
    source_code: tuple[str, ...]
    solution_dir: str
    method_name: str | None
    has_custom_caller: bool
    standard_mode: bool


def _worker_main(
    worker_id: int,
    spec: _WorkerSpec,
    input_queue,
    result_queue,
    status_slot,
) -> None:
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[variable] = "1"
    loaded_at = time.perf_counter()
    reader: CaseStoreReader | None = None
    reader_path: str | None = None
    try:
        if spec.solution_dir not in sys.path:
            sys.path.insert(0, spec.solution_dir)
        if spec.standard_mode:
            from runtime.runner.standard import (
                load_standard_solution,
                normalize_standard_output,
            )

            module = None
            solution_class = load_standard_solution(
                spec.source_code[0], spec.method_name, "<oj-submission>"
            )
            custom_caller = None
            parse_output = normalize_standard_output
            values_equal = lambda expected, output: expected == output
        else:
            from tools.ai_prompts import _CUSTOM_CALLER_NAME
            from tools.args_parser import parse_output_to_standard
            from tools.solution_runner import _create_solution_module, _values_equal

            module = _create_solution_module(list(spec.source_code))
            solution_class = module.__dict__["Solution"]
            custom_caller = (
                module.__dict__[_CUSTOM_CALLER_NAME] if spec.has_custom_caller else None
            )
            parse_output = parse_output_to_standard
            values_equal = _values_equal
        result_queue.put(
            ("ready", worker_id, os.getpid(), time.perf_counter() - loaded_at)
        )
    except BaseException:
        result_queue.put(("boot_error", worker_id, traceback.format_exc()))
        return

    cached_instance: Any = None
    try:
        while True:
            message = input_queue.get()
            if not message or message[0] == "stop":
                return
            if message[0] == "release":
                release_run_id = message[1]
                if reader is not None:
                    reader.close()
                    reader = None
                    reader_path = None
                result_queue.put(("released", worker_id, release_run_id))
                continue
            (
                _,
                run_id,
                task_id,
                store_path,
                start,
                stop,
                capture_stdout,
                reuse_solution_instance,
                collect_results,
            ) = message
            if status_slot is not None:
                status_slot.run_id = run_id
                status_slot.task_id = task_id
            if reader_path != store_path:
                if reader is not None:
                    reader.close()
                reader = CaseStoreReader(store_path)
                reader_path = store_path

            chunk_results = []
            chunk_compute = 0.0
            chunk_decode = 0.0
            chunk_correct = chunk_wrong = chunk_errors = 0
            chunk_digest = 0
            try:
                for case_index in range(start, stop):
                    if status_slot is not None:
                        status_slot.case_index = case_index
                        status_slot.started_at = time.time()
                    decode_started = time.perf_counter()
                    assert reader is not None
                    case = reader[case_index]
                    chunk_decode += time.perf_counter() - decode_started

                    compute_started = time.perf_counter()
                    output = None
                    error = None
                    error_traceback = None
                    is_wrong = False
                    captured = ""
                    try:
                        if reuse_solution_instance:
                            if cached_instance is None:
                                cached_instance = solution_class()
                            instance = cached_instance
                        else:
                            instance = solution_class()
                        if spec.standard_mode:
                            target = getattr(instance, spec.method_name)
                            writer = _BoundedWriter()
                            output_context = (
                                contextlib.redirect_stdout(writer)
                                if capture_stdout
                                else contextlib.nullcontext()
                            )
                            with output_context:
                                if isinstance(case["input"], dict):
                                    raw_output = target(**case["input"])
                                else:
                                    raw_output = target(*case["input"])
                            if capture_stdout:
                                captured = writer.getvalue()
                            output = parse_output(raw_output)
                            if "expected" in case:
                                is_wrong = not values_equal(case["expected"], output)
                            elapsed = time.perf_counter() - compute_started
                            chunk_compute += elapsed
                            result_item = (
                                case_index,
                                case.get("cid", case_index),
                                output,
                                error,
                                error_traceback,
                                elapsed,
                                is_wrong,
                                captured,
                            )
                            if collect_results:
                                chunk_results.append(result_item)
                            if is_wrong:
                                chunk_wrong += 1
                            else:
                                chunk_correct += 1
                            chunk_digest ^= _digest_value(
                                case_index, case.get("cid", case_index), output, error
                            )
                            if status_slot is not None:
                                status_slot.started_at = 0.0
                            continue
                        if custom_caller is not None:
                            caller = custom_caller
                            target = instance
                        elif isinstance(case["input"], dict):
                            caller = module.__dict__["main_caller_kwargs"]
                            target = getattr(instance, spec.method_name)
                        else:
                            caller = module.__dict__["main_caller_args"]
                            target = getattr(instance, spec.method_name)

                        writer = _BoundedWriter()
                        output_context = (
                            contextlib.redirect_stdout(writer)
                            if capture_stdout
                            else contextlib.nullcontext()
                        )
                        with output_context:
                            raw_output = caller(target, case["input"])
                        if capture_stdout:
                            captured = writer.getvalue()
                        output = parse_output(raw_output)
                        if "expected" in case:
                            is_wrong = not values_equal(case["expected"], output)
                    except BaseException as exc:
                        error = f"{type(exc).__name__}: {exc}"
                        error_traceback = traceback.format_exc()
                    elapsed = time.perf_counter() - compute_started
                    chunk_compute += elapsed
                    result_item = (
                        case_index,
                        case.get("cid", case_index),
                        output,
                        error,
                        error_traceback,
                        elapsed,
                        is_wrong,
                        captured,
                    )
                    if collect_results:
                        chunk_results.append(result_item)
                    if error is not None:
                        chunk_errors += 1
                    elif is_wrong:
                        chunk_wrong += 1
                    else:
                        chunk_correct += 1
                    chunk_digest ^= _digest_value(
                        case_index, case.get("cid", case_index), output, error
                    )
                    if status_slot is not None:
                        status_slot.started_at = 0.0

                if collect_results:
                    result_queue.put(
                        (
                            "chunk",
                            worker_id,
                            run_id,
                            task_id,
                            chunk_results,
                            chunk_compute,
                            chunk_decode,
                        )
                    )
                else:
                    result_queue.put(
                        (
                            "chunk_summary",
                            worker_id,
                            run_id,
                            task_id,
                            stop - start,
                            chunk_correct,
                            chunk_wrong,
                            chunk_errors,
                            chunk_digest,
                            chunk_compute,
                            chunk_decode,
                        )
                    )
            except BaseException:
                result_queue.put(
                    ("task_error", worker_id, run_id, task_id, traceback.format_exc())
                )
            finally:
                if status_slot is not None:
                    status_slot.run_id = -1
                    status_slot.task_id = -1
                    status_slot.case_index = -1
                    status_slot.started_at = 0.0
    finally:
        if reader is not None:
            reader.close()


class PersistentPythonRunner:
    """Long-lived worker processes for independent Python OJ cases.

    Source code and dependencies are loaded once per worker.  Each call only
    distributes ranges into an mmap-backed case store.  The legacy runner is
    intentionally not modified, so both implementations remain benchmarkable.
    """

    def __init__(
        self,
        solution_file: os.PathLike[str] | str,
        main_method: str | None = None,
        *,
        workers: int = 1,
        capture_stdout: bool = True,
        reuse_solution_instance: bool = False,
        standard_mode: bool = False,
        start: bool = True,
    ) -> None:
        if not isinstance(workers, int) or not 1 <= workers <= MAX_WORKERS:
            raise ValueError(f"workers must be between 1 and {MAX_WORKERS}")
        self.solution_file = Path(solution_file).resolve()
        if standard_mode:
            if main_method is None:
                raise ValueError("standard_mode requires an explicit main_method")
            from .standard import validate_standard_source

            student_code = self.solution_file.read_text(encoding="utf-8-sig")
            validate_standard_source(student_code, main_method)
            source_code = (student_code,)
            resolved_method = main_method
            has_custom_caller = False
        else:
            from tools.solution_runner import SolutionRunner

            legacy = SolutionRunner(solution_file, main_method=main_method)
            if legacy.main_method is None and not legacy.has_custom_caller:
                raise ValueError("multiple methods require conversion.py/custom_caller")
            source_code = tuple(legacy.source_code_lst)
            resolved_method = legacy.main_method
            has_custom_caller = legacy.has_custom_caller
        self.workers = workers
        self.capture_stdout = capture_stdout
        self.reuse_solution_instance = reuse_solution_instance
        self.standard_mode = standard_mode
        self.interpreter_name = platform.python_implementation().lower()
        self._spec = _WorkerSpec(
            source_code=source_code,
            solution_dir=str(self.solution_file.parent),
            method_name=resolved_method,
            has_custom_caller=has_custom_caller,
            standard_mode=standard_mode,
        )
        self._context = multiprocessing.get_context("spawn")
        self._result_queue = None
        self._input_queues: list[Any] = []
        self._statuses: list[Any] = []
        self._processes: list[Any] = []
        self._started = False
        self._run_id = 0
        self.pool_startup_seconds = 0.0
        if start:
            self.start()

    def _spawn_worker(self, worker_id: int) -> None:
        input_queue = self._context.Queue(maxsize=2)
        status = (
            None
            if self.interpreter_name == "pypy"
            else self._context.RawValue(_WorkerStatus, -1, -1, -1, 0.0)
        )
        process = self._context.Process(
            target=_worker_main,
            args=(worker_id, self._spec, input_queue, self._result_queue, status),
            name=f"oj-python-worker-{worker_id}",
        )
        process.start()
        if worker_id == len(self._processes):
            self._input_queues.append(input_queue)
            self._statuses.append(status)
            self._processes.append(process)
        else:
            old_queue = self._input_queues[worker_id]
            old_queue.close()
            self._input_queues[worker_id] = input_queue
            self._statuses[worker_id] = status
            self._processes[worker_id] = process

    def start(self) -> None:
        if self._started:
            return
        started_at = time.perf_counter()
        self._result_queue = self._context.Queue()
        for worker_id in range(self.workers):
            self._spawn_worker(worker_id)
        ready = set()
        boot_deadline = time.monotonic() + 30.0
        while len(ready) < self.workers:
            remaining = boot_deadline - time.monotonic()
            if remaining <= 0:
                self.close()
                raise TimeoutError("workers did not finish bootstrapping within 30 seconds")
            try:
                message = self._result_queue.get(timeout=min(0.25, remaining))
            except queue.Empty:
                for worker_id, process in enumerate(self._processes):
                    if worker_id not in ready and not process.is_alive():
                        self.close()
                        raise RuntimeError(
                            f"worker {worker_id} exited during bootstrap: {process.exitcode}"
                        )
                continue
            if message[0] == "ready":
                ready.add(message[1])
            elif message[0] == "boot_error":
                self.close()
                raise RuntimeError(f"worker {message[1]} boot failed:\n{message[2]}")
        self.pool_startup_seconds = time.perf_counter() - started_at
        self._started = True

    def _restart_worker(self, worker_id: int) -> None:
        process = self._processes[worker_id]
        if process.is_alive():
            process.terminate()
        process.join(timeout=2.0)
        self._spawn_worker(worker_id)

    @staticmethod
    def create_case_store(
        cases: Iterable[Mapping[str, Any]], path: os.PathLike[str] | str
    ):
        return CaseStoreWriter.write(path, cases)

    def _sample_worker_rss(self) -> int:
        try:
            import psutil
        except ImportError:
            return 0
        total = 0
        for process in self._processes:
            if process.is_alive():
                try:
                    total += psutil.Process(process.pid).memory_info().rss
                except (psutil.Error, OSError):
                    pass
        return total

    def _release_store(self, run_id: int) -> None:
        """Close worker mmap handles so Windows can delete temporary stores."""
        waiting = {
            worker_id
            for worker_id, process in enumerate(self._processes)
            if process.is_alive()
        }
        for worker_id in waiting:
            self._input_queues[worker_id].put(("release", run_id))
        deadline = time.monotonic() + 10.0
        while waiting:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"workers did not release case store: {sorted(waiting)}")
            try:
                message = self._result_queue.get(timeout=min(0.25, remaining))
            except queue.Empty:
                for worker_id in list(waiting):
                    if not self._processes[worker_id].is_alive():
                        waiting.remove(worker_id)
                continue
            if (
                message[0] == "released"
                and message[2] == run_id
                and message[1] in waiting
            ):
                waiting.remove(message[1])

    def run_store(
        self,
        store_path: os.PathLike[str] | str,
        *,
        chunk_size: int | None = None,
        timeout_s: float | None = None,
        collect_results: bool = True,
        max_task_retries: int = 2,
    ) -> RunReport:
        if timeout_s is not None and timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        if timeout_s is not None and self.interpreter_name == "pypy":
            raise NotImplementedError(
                "per-case timeout status is unavailable in PyPy on Windows; "
                "use the native Job Object batch timeout"
            )
        if not self._started:
            self.start()
        store_path = str(Path(store_path).resolve())
        with CaseStoreReader(store_path) as reader:
            case_count = len(reader)
        if chunk_size is None:
            # Four waves per worker balance heterogeneous OJ cases without
            # paying hundreds of Queue round-trips.  Benchmarks with two waves
            # improved a few micro-cases but regressed LCS tail latency.
            chunk_size = max(1, min(16384, math.ceil(case_count / (self.workers * 4))))
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")

        self._run_id += 1
        run_id = self._run_id
        pending = deque(
            (start, min(start + chunk_size, case_count), 0)
            for start in range(0, case_count, chunk_size)
        )
        idle = set(range(self.workers))
        inflight: dict[int, tuple[int, int, int, int]] = {}
        next_task_id = 0
        result_slots: list[dict[str, Any] | None] | None = (
            [None] * case_count if collect_results else None
        )
        correct_count = wrong_count = error_count = timed_out_cases = 0
        completed_count = 0
        worker_compute = worker_decode = 0.0
        digest_xor = 0
        worker_restarts = 0
        peak_rss = self._sample_worker_rss()

        def record_result(item: tuple[Any, ...]) -> None:
            nonlocal correct_count, wrong_count, error_count, completed_count, digest_xor
            index, cid, output, error, error_traceback, elapsed, wrong, stdout = item
            compact = {
                "index": index,
                "cid": cid,
                "output": output,
                "elapsed": elapsed,
                "wrong": bool(wrong),
            }
            if error is not None:
                compact["error"] = error
                compact["traceback"] = error_traceback
                error_count += 1
            elif wrong:
                wrong_count += 1
            else:
                correct_count += 1
            if stdout:
                compact["stdout"] = stdout
            if result_slots is not None:
                result_slots[index] = compact
            digest_xor ^= _digest_value(index, cid, output, error)
            completed_count += 1

        def dispatch() -> None:
            nonlocal next_task_id
            while pending and idle:
                worker_id = min(idle)
                idle.remove(worker_id)
                start, stop, retries = pending.popleft()
                task_id = next_task_id
                next_task_id += 1
                inflight[worker_id] = (task_id, start, stop, retries)
                self._input_queues[worker_id].put(
                    (
                        "task",
                        run_id,
                        task_id,
                        store_path,
                        start,
                        stop,
                        self.capture_stdout,
                        self.reuse_solution_instance,
                        collect_results,
                    )
                )

        def recover_worker(worker_id: int, timed_out_index: int | None = None) -> None:
            nonlocal worker_restarts, timed_out_cases
            task_id, start, stop, retries = inflight.pop(worker_id)
            if retries >= max_task_retries and timed_out_index is None:
                raise RuntimeError(
                    f"worker {worker_id} repeatedly failed task {task_id} [{start}, {stop})"
                )
            if timed_out_index is None:
                pending.appendleft((start, stop, retries + 1))
            else:
                if start <= timed_out_index < stop:
                    if start < timed_out_index:
                        pending.appendleft((start, timed_out_index, retries + 1))
                    if timed_out_index + 1 < stop:
                        pending.appendleft((timed_out_index + 1, stop, retries + 1))
                    record_result(
                        (
                            timed_out_index,
                            timed_out_index,
                            None,
                            "Time Limit Exceeded (TLE)",
                            f"case exceeded {timeout_s} seconds",
                            timeout_s,
                            False,
                            "",
                        )
                    )
                    timed_out_cases += 1
                else:
                    pending.appendleft((start, stop, retries + 1))
            self._restart_worker(worker_id)
            worker_restarts += 1
            idle.add(worker_id)

        wall_started = time.perf_counter()
        dispatch()
        try:
            while completed_count < case_count:
                try:
                    message = self._result_queue.get(timeout=0.05)
                except queue.Empty:
                    message = None
                if message is not None:
                    kind = message[0]
                    if kind == "chunk":
                        _, worker_id, message_run, task_id, items, compute, decode = message
                        current = inflight.get(worker_id)
                        if (
                            message_run == run_id
                            and current is not None
                            and current[0] == task_id
                        ):
                            inflight.pop(worker_id)
                            idle.add(worker_id)
                            worker_compute += compute
                            worker_decode += decode
                            for item in items:
                                record_result(item)
                    elif kind == "chunk_summary":
                        (
                            _,
                            worker_id,
                            message_run,
                            task_id,
                            processed,
                            chunk_correct,
                            chunk_wrong,
                            chunk_errors,
                            chunk_digest,
                            compute,
                            decode,
                        ) = message
                        current = inflight.get(worker_id)
                        if (
                            message_run == run_id
                            and current is not None
                            and current[0] == task_id
                        ):
                            inflight.pop(worker_id)
                            idle.add(worker_id)
                            correct_count += chunk_correct
                            wrong_count += chunk_wrong
                            error_count += chunk_errors
                            completed_count += processed
                            digest_xor ^= chunk_digest
                            worker_compute += compute
                            worker_decode += decode
                    elif kind in {"task_error", "boot_error"}:
                        worker_id = message[1]
                        if worker_id in inflight:
                            recover_worker(worker_id)

                now = time.time()
                for worker_id in list(inflight):
                    process = self._processes[worker_id]
                    if not process.is_alive():
                        recover_worker(worker_id)
                        continue
                    status = self._statuses[worker_id]
                    if (
                        timeout_s is not None
                        and status is not None
                        and status.run_id == run_id
                        and status.started_at > 0
                        and now - status.started_at > timeout_s
                    ):
                        recover_worker(worker_id, int(status.case_index))
                dispatch()
                peak_rss = max(peak_rss, self._sample_worker_rss())
                if not pending and not inflight and completed_count < case_count:
                    raise RuntimeError(
                        f"scheduler stopped after {completed_count}/{case_count} cases"
                    )
        except BaseException:
            self.close()
            raise

        wall_seconds = time.perf_counter() - wall_started
        results = None
        if result_slots is not None:
            if any(item is None for item in result_slots):
                raise RuntimeError("one or more result slots were not written")
            results = [item for item in result_slots if item is not None]
        metrics = RunMetrics(
            backend=(
                f"persistent_{self.interpreter_name}_standard"
                if self.standard_mode
                else f"persistent_{self.interpreter_name}"
            ),
            workers=self.workers,
            case_count=case_count,
            wall_seconds=wall_seconds,
            throughput_cases_per_second=(case_count / wall_seconds if wall_seconds else 0.0),
            pool_startup_seconds=self.pool_startup_seconds,
            worker_compute_seconds=worker_compute,
            worker_decode_seconds=worker_decode,
            peak_worker_rss_bytes=peak_rss,
            worker_restarts=worker_restarts,
            timed_out_cases=timed_out_cases,
        )
        self._release_store(run_id)
        return RunReport(
            metrics=metrics,
            correct_count=correct_count,
            wrong_count=wrong_count,
            error_count=error_count,
            digest=f"{digest_xor:032x}",
            results=results,
        )

    def run(
        self,
        cases: Iterable[Mapping[str, Any]],
        *,
        chunk_size: int | None = None,
        timeout_s: float | None = None,
        collect_results: bool = True,
    ) -> RunReport:
        with tempfile.TemporaryDirectory(prefix="oj_runner_cases_") as directory:
            store_path = Path(directory) / "cases.ojbin"
            CaseStoreWriter.write(store_path, cases)
            return self.run_store(
                store_path,
                chunk_size=chunk_size,
                timeout_s=timeout_s,
                collect_results=collect_results,
            )

    def close(self) -> None:
        for input_queue in self._input_queues:
            try:
                input_queue.put(("stop",), timeout=0.05)
            except (queue.Full, ValueError, OSError):
                pass
        for process in self._processes:
            process.join(timeout=1.0)
            if process.is_alive():
                process.terminate()
                process.join(timeout=2.0)
        for input_queue in self._input_queues:
            try:
                input_queue.close()
            except (ValueError, OSError):
                pass
        if self._result_queue is not None:
            try:
                self._result_queue.close()
            except (ValueError, OSError):
                pass
        self._input_queues = []
        self._statuses = []
        self._processes = []
        self._result_queue = None
        self._started = False

    def __enter__(self) -> "PersistentPythonRunner":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
