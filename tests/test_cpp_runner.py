from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from runtime.runner import CaseStoreWriter, CompiledCppRunner
from runtime.runner.common import digest_value
from runtime.runner.cpp_process import (
    CppSourceError,
    _toolchain,
    parse_c_solution,
    parse_cpp_solution,
)
from runtime.runner.native_process import DEFAULT_MANAGER


ROOT = Path(__file__).resolve().parent.parent
CPP_FIXTURES = ROOT / "tests" / "fixtures" / "cpp"


def _compiler_available() -> bool:
    try:
        _toolchain(None)
    except (FileNotFoundError, RuntimeError):
        return False
    return True


CPP_RUNTIME_AVAILABLE = DEFAULT_MANAGER.is_file() and _compiler_available()


class CppSourceParserTests(unittest.TestCase):
    def test_parses_common_leetcode_cpp_types(self) -> None:
        source = (CPP_FIXTURES / "classic_algorithms.cpp").read_text(encoding="utf-8")
        vector_method = parse_cpp_solution(source, "vector_checksum")
        self.assertEqual(vector_method.return_type, "std::uint64_t")
        self.assertEqual(vector_method.parameters[0].cpp_type, "std::vector<int>")
        lcs_method = parse_cpp_solution(source, "lcs_length")
        self.assertEqual(
            [parameter.cpp_type for parameter in lcs_method.parameters],
            ["std::string", "std::string"],
        )

    def test_rejects_preprocessor_and_parses_scalar_c_abi(self) -> None:
        source = (CPP_FIXTURES / "invalid_include.cpp").read_text(encoding="utf-8")
        with self.assertRaisesRegex(CppSourceError, "preprocessor"):
            parse_cpp_solution(source, "solve")
        c_method = parse_c_solution(
            "long long gcd_value(long long left, long long right) { return left + right; }",
            "gcd_value",
        )
        self.assertEqual(c_method.return_type, "long long")
        self.assertEqual(len(c_method.parameters), 2)


@unittest.skipUnless(CPP_RUNTIME_AVAILABLE, "C++ manager/compiler is unavailable")
class CompiledCppRunnerTests(unittest.TestCase):
    def _store(self, directory: str, cases) -> Path:
        path = Path(directory) / "cases.ojbin"
        CaseStoreWriter.write(path, cases)
        return path

    def test_two_sum_supports_positional_and_named_json_inputs(self) -> None:
        cases = [
            {"cid": "positional", "input": ([2, 7, 11, 15], 9), "expected": [0, 1]},
            {
                "cid": "named",
                "input": {"nums": [3, 2, 4], "target": 6},
                "expected": [1, 2],
            },
            {"cid": "duplicate", "input": ([3, 3], 6), "expected": [0, 1]},
        ]
        with tempfile.TemporaryDirectory(prefix="cpp_runner_test_", dir=ROOT) as directory:
            store = self._store(directory, cases)
            runner = CompiledCppRunner(
                CPP_FIXTURES / "two_sum.cpp",
                "twoSum",
                workers=2,
                workspace=ROOT,
            )
            report = runner.run_store(store)
            expected_digest = 0
            for index, case in enumerate(cases):
                expected_digest ^= digest_value(
                    index, case["cid"], case["expected"], None
                )
            self.assertEqual(report.correct_count, len(cases))
            self.assertEqual(report.wrong_count, 0)
            self.assertEqual(report.error_count, 0)
            self.assertEqual(report.digest, f"{expected_digest:032x}")
            self.assertEqual(report.metrics.fallback_digest_cases, 0)
            self.assertLess(report.metrics.peak_worker_rss_bytes, 8 * 1024**3)

    def test_wrong_and_exception_results_use_compatible_fallback_digest(self) -> None:
        cases = [
            {"cid": 10, "input": ([1, 2], 3), "expected": 6},
            {"cid": 11, "input": ([4], 5), "expected": 9},
        ]
        with tempfile.TemporaryDirectory(prefix="cpp_fallback_test_", dir=ROOT) as directory:
            store = self._store(directory, cases)
            wrong = CompiledCppRunner(
                CPP_FIXTURES / "wrong_solution.cpp",
                "total",
                workers=1,
                workspace=ROOT,
            ).run_store(store)
            wrong_digest = 0
            for index, case in enumerate(cases):
                wrong_digest ^= digest_value(index, case["cid"], -1, None)
            self.assertEqual(wrong.wrong_count, len(cases))
            self.assertEqual(wrong.metrics.fallback_digest_cases, len(cases))
            self.assertEqual(wrong.digest, f"{wrong_digest:032x}")

            failed = CompiledCppRunner(
                CPP_FIXTURES / "throw_solution.cpp",
                "total",
                workers=1,
                workspace=ROOT,
            ).run_store(store)
            error = "RuntimeError: student failure"
            error_digest = 0
            for index, case in enumerate(cases):
                error_digest ^= digest_value(index, case["cid"], None, error)
            self.assertEqual(failed.error_count, len(cases))
            self.assertEqual(failed.metrics.fallback_digest_cases, len(cases))
            self.assertEqual(failed.digest, f"{error_digest:032x}")

    def test_compiled_artifact_is_reused(self) -> None:
        first = CompiledCppRunner(
            CPP_FIXTURES / "two_sum.cpp",
            "twoSum",
            workers=1,
            workspace=ROOT,
        )
        second = CompiledCppRunner(
            CPP_FIXTURES / "two_sum.cpp",
            "twoSum",
            workers=1,
            workspace=ROOT,
        )
        self.assertEqual(first.build_info.cache_key, second.build_info.cache_key)
        self.assertTrue(second.build_info.cache_hit)
        self.assertEqual(second.build_info.compile_seconds, 0.0)

    def test_scalar_c_function_uses_the_same_json_store(self) -> None:
        def expected(value: int, rounds: int) -> int:
            state = value & 0xFFFFFFFF
            for _ in range(rounds):
                state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
                state ^= state >> 13
            return state

        cases = [
            {
                "cid": index,
                "input": (index * 2654435761, 4),
                "expected": expected(index * 2654435761, 4),
            }
            for index in range(200)
        ]
        with tempfile.TemporaryDirectory(prefix="c_runner_test_", dir=ROOT) as directory:
            store = self._store(directory, cases)
            runner = CompiledCppRunner(
                ROOT / "tests" / "fixtures" / "c" / "integer_mix.c",
                "integer_mix",
                workers=2,
                workspace=ROOT,
            )
            report = runner.run_store(store)
            self.assertEqual(report.correct_count, len(cases))
            self.assertEqual(report.wrong_count, 0)
            self.assertEqual(report.error_count, 0)
            self.assertEqual(report.metrics.backend, "native_process_manager_standard_c")
            self.assertEqual(report.metrics.fallback_digest_cases, 0)

    def test_batch_timeout_terminates_infinite_cpp_loop(self) -> None:
        cases = [{"cid": 0, "input": (True, 7), "expected": 7}]
        with tempfile.TemporaryDirectory(prefix="cpp_timeout_test_", dir=ROOT) as directory:
            store = self._store(directory, cases)
            runner = CompiledCppRunner(
                CPP_FIXTURES / "hang_solution.cpp",
                "work",
                workers=1,
                workspace=ROOT,
            )
            started = time.perf_counter()
            with self.assertRaisesRegex(RuntimeError, r"native C\+\+ manager failed"):
                runner.run_store(store, batch_timeout_s=0.4)
            self.assertLess(time.perf_counter() - started, 4.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
