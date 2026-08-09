from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from runtime.runner import CaseStoreWriter, NativeProcessRunner
from runtime.runner.native_process import DEFAULT_MANAGER


ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(DEFAULT_MANAGER.is_file(), "native manager has not been built")
class NativeRunnerTests(unittest.TestCase):
    def test_job_managed_workers_execute_disjoint_ranges(self) -> None:
        with tempfile.TemporaryDirectory(prefix="native_runner_test_") as directory:
            store_path = Path(directory) / "cases.ojbin"
            CaseStoreWriter.write(
                store_path,
                (
                    {"cid": index, "input": ([index, 1], 2), "expected": index + 3}
                    for index in range(101)
                ),
            )
            report = NativeProcessRunner(
                ROOT / "tests" / "fixtures" / "basic_solution.py",
                "total",
                workers=6,
                workspace=ROOT,
                standard_mode=True,
            ).run_store(store_path)
            self.assertEqual(report.correct_count, 101)
            self.assertEqual(report.wrong_count, 0)
            self.assertEqual(report.error_count, 0)
            self.assertEqual(report.metrics.workers, 6)
            self.assertEqual(
                report.metrics.backend, "native_process_manager_standard_cpython"
            )
            self.assertLess(report.metrics.peak_worker_rss_bytes, 8 * 1024**3)

    def test_job_batch_timeout_terminates_hung_workers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="native_runner_timeout_") as directory:
            store_path = Path(directory) / "cases.ojbin"
            CaseStoreWriter.write(
                store_path,
                ({"cid": 0, "input": (True, 7), "expected": 7},),
            )
            runner = NativeProcessRunner(
                ROOT / "tests" / "fixtures" / "slow_solution.py",
                "work",
                workers=1,
                workspace=ROOT,
            )
            started = time.perf_counter()
            with self.assertRaisesRegex(RuntimeError, "native manager failed"):
                runner.run_store(store_path, batch_timeout_s=0.5)
            self.assertLess(time.perf_counter() - started, 4.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
