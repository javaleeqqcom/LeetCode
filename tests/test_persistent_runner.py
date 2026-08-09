from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from runtime.runner import CaseStoreReader, CaseStoreWriter, PersistentPythonRunner
from runtime.runner.standard import StandardSourceError, validate_standard_source


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"


class CaseStoreTests(unittest.TestCase):
    def test_streaming_round_trip(self) -> None:
        with tempfile.TemporaryDirectory(prefix="case_store_test_") as directory:
            path = Path(directory) / "cases.ojbin"
            info = CaseStoreWriter.write(
                path,
                (
                    {"cid": f"case-{index}", "input": ([index, 1], 2), "expected": index + 3}
                    for index in range(10)
                ),
            )
            self.assertEqual(info.case_count, 10)
            with CaseStoreReader(path) as reader:
                self.assertEqual(len(reader), 10)
                self.assertEqual(reader[3]["cid"], "case-3")
                self.assertEqual(reader[3]["input"], ([3, 1], 2))
                self.assertEqual(reader[-1]["expected"], 12)


class PersistentRunnerTests(unittest.TestCase):
    def test_standard_mode_avoids_legacy_runtime_dependencies(self) -> None:
        runner = PersistentPythonRunner(
            FIXTURES / "basic_solution.py",
            main_method="total",
            workers=2,
            standard_mode=True,
        )
        try:
            report = runner.run(
                [
                    {"cid": index, "input": ([index, 1], 2), "expected": index + 3}
                    for index in range(20)
                ]
            )
            self.assertEqual(report.correct_count, 20)
            self.assertEqual(report.metrics.backend, "persistent_cpython_standard")
        finally:
            runner.close()

    def test_standard_mode_rejects_system_imports(self) -> None:
        with self.assertRaises(StandardSourceError):
            validate_standard_source(
                "import os\nclass Solution:\n    def run(self): return 1\n", "run"
            )

    def test_workers_are_reused_across_runs(self) -> None:
        runner = PersistentPythonRunner(
            FIXTURES / "basic_solution.py", workers=2, capture_stdout=True
        )
        try:
            original_pids = [process.pid for process in runner._processes]
            cases = [
                {"cid": index, "input": ([index, 1], 2), "expected": index + 3}
                for index in range(48)
            ]
            first = runner.run(cases, chunk_size=3)
            second = runner.run(cases, chunk_size=4)
            self.assertEqual(first.correct_count, len(cases))
            self.assertEqual(second.correct_count, len(cases))
            self.assertEqual(first.digest, second.digest)
            self.assertEqual(original_pids, [process.pid for process in runner._processes])
            self.assertEqual(first.metrics.worker_restarts, 0)
        finally:
            runner.close()

    def test_timeout_restarts_only_the_affected_worker(self) -> None:
        runner = PersistentPythonRunner(FIXTURES / "slow_solution.py", workers=2)
        try:
            report = runner.run(
                [
                    {"cid": "hang", "input": (True, 0), "expected": 0},
                    {"cid": "ok", "input": (False, 7), "expected": 7},
                ],
                chunk_size=1,
                timeout_s=0.25,
            )
            self.assertEqual(report.metrics.timed_out_cases, 1)
            self.assertEqual(report.metrics.worker_restarts, 1)
            self.assertEqual(report.correct_count, 1)
            self.assertEqual(report.error_count, 1)
        finally:
            runner.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
