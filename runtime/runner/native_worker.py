from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

from runtime.runner.case_store import CaseStoreReader
from runtime.runner.common import BoundedWriter as _BoundedWriter
from runtime.runner.common import digest_value as _digest_value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker-id", type=int, required=True)
    parser.add_argument("--store", required=True)
    parser.add_argument("--solution", required=True)
    parser.add_argument("--method", required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--stop", type=int, required=True)
    parser.add_argument("--result-dir", required=True)
    parser.add_argument("--standard-mode", type=int, choices=(0, 1), default=0)
    args = parser.parse_args()

    started = time.perf_counter()
    if args.standard_mode:
        from runtime.runner.standard import (
            load_standard_solution,
            normalize_standard_output,
        )

        source = Path(args.solution).read_text(encoding="utf-8-sig")
        solution_class = load_standard_solution(source, args.method, args.solution)
        runner = module = custom_caller = None
        parse_output = normalize_standard_output
        values_equal = lambda expected, output: expected == output
    else:
        from tools.ai_prompts import _CUSTOM_CALLER_NAME
        from tools.args_parser import parse_output_to_standard
        from tools.solution_runner import SolutionRunner, _values_equal

        runner = SolutionRunner(args.solution, main_method=args.method)
        solution_class = runner.solution_class
        module = runner.solution_module
        custom_caller = (
            module.__dict__[_CUSTOM_CALLER_NAME] if runner.has_custom_caller else None
        )
        parse_output = parse_output_to_standard
        values_equal = _values_equal
    correct = wrong = errors = 0
    first_error = None
    digest = 0
    compute_seconds = decode_seconds = 0.0
    with CaseStoreReader(args.store) as store:
        if args.start < 0 or args.stop < args.start or args.stop > len(store):
            raise ValueError("invalid worker case range")
        for index in range(args.start, args.stop):
            decode_started = time.perf_counter()
            case = store[index]
            decode_seconds += time.perf_counter() - decode_started
            compute_started = time.perf_counter()
            output = None
            error = None
            is_wrong = False
            try:
                instance = solution_class()
                if args.standard_mode:
                    target = getattr(instance, args.method)
                elif custom_caller is not None:
                    caller = custom_caller
                    target = instance
                elif isinstance(case["input"], dict):
                    caller = module.__dict__["main_caller_kwargs"]
                    target = getattr(instance, runner.main_method)
                else:
                    caller = module.__dict__["main_caller_args"]
                    target = getattr(instance, runner.main_method)
                writer = _BoundedWriter()
                with contextlib.redirect_stdout(writer):
                    if args.standard_mode:
                        if isinstance(case["input"], dict):
                            raw_output = target(**case["input"])
                        else:
                            raw_output = target(*case["input"])
                    else:
                        raw_output = caller(target, case["input"])
                    output = parse_output(raw_output)
                if "expected" in case:
                    is_wrong = not values_equal(case["expected"], output)
            except BaseException as exc:
                error = f"{type(exc).__name__}: {exc}"
                errors += 1
                if first_error is None:
                    first_error = error
            else:
                if is_wrong:
                    wrong += 1
                else:
                    correct += 1
            compute_seconds += time.perf_counter() - compute_started
            digest ^= _digest_value(index, case.get("cid", index), output, error)

    rss = 0
    try:
        import psutil

        rss = psutil.Process().memory_info().rss
    except (ImportError, OSError):
        pass
    payload = {
        "worker_id": args.worker_id,
        "start": args.start,
        "stop": args.stop,
        "correct": correct,
        "wrong": wrong,
        "errors": errors,
        "first_error": first_error,
        "digest": f"{digest:032x}",
        "wall_seconds": time.perf_counter() - started,
        "compute_seconds": compute_seconds,
        "decode_seconds": decode_seconds,
        "rss_bytes": rss,
    }
    result_dir = Path(args.result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)
    result_path = result_dir / f"worker_{args.worker_id}.json"
    temporary_path = result_path.with_suffix(".json.writing")
    temporary_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary_path, result_path)
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except BaseException:
        details = traceback.format_exc()
        try:
            result_index = sys.argv.index("--result-dir") + 1
            worker_index = sys.argv.index("--worker-id") + 1
            error_dir = Path(sys.argv[result_index])
            error_dir.mkdir(parents=True, exist_ok=True)
            (error_dir / f"worker_{sys.argv[worker_index]}.error.txt").write_text(
                details, encoding="utf-8"
            )
        except BaseException:
            pass
        traceback.print_exc()
        exit_code = 1
    raise SystemExit(exit_code)
