from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from runtime.runner import (
    AutoTuneConfig,
    CaseStoreWriter,
    CompiledCppRunner,
    PersistentPythonRunner,
)
from runtime.runner.auto_tune import (
    AutoTuneProbe,
    ProgramFeatures,
    StoreFeatures,
    SystemFeatures,
    select_workers,
)
from runtime.runner.cpp_process import _toolchain
from runtime.runner.native_process import DEFAULT_MANAGER


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
CPP_FIXTURES = FIXTURES / "cpp"
GIB = 1024**3


def _system(*, available_memory: int = 32 * GIB) -> SystemFeatures:
    return SystemFeatures(24, 12, 64 * GIB, available_memory, 5.0, "test-host")


def _store(count: int) -> StoreFeatures:
    return StoreFeatures(count, count * 128, min(32, count), 96.0, 128.0, 160, 1.0)


def _program() -> ProgramFeatures:
    return ProgramFeatures("python", 500, 2, 2, 3, False, 8.0)


class AutoTunePolicyTests(unittest.TestCase):
    def test_tiny_workload_stays_single_process(self) -> None:
        decision = select_workers(
            backend_family="persistent_python",
            system=_system(),
            store=_store(2),
            program=_program(),
            config=AutoTuneConfig(enable_probe=False, profile_path=None),
        )
        self.assertEqual(decision.workers, 1)
        self.assertEqual(decision.candidate_workers, (1,))

    def test_measured_cpu_heavy_workload_uses_parallel_workers(self) -> None:
        decision = select_workers(
            backend_family="persistent_python",
            system=_system(),
            store=_store(10_000),
            program=_program(),
            config=AutoTuneConfig(profile_path=None),
            probe=AutoTuneProbe("persistent_python", 8, 0.85, 0.80, 0.01, 64 * 1024**2),
        )
        self.assertGreater(decision.workers, 1)
        self.assertLessEqual(decision.workers, 16)

    def test_memory_pressure_caps_parallelism(self) -> None:
        decision = select_workers(
            backend_family="persistent_python",
            system=_system(available_memory=128 * 1024**2),
            store=_store(10_000),
            program=_program(),
            config=AutoTuneConfig(profile_path=None),
            probe=AutoTuneProbe("persistent_python", 8, 0.85, 0.80, 0.01, 80 * 1024**2),
        )
        self.assertEqual(decision.memory_limited_workers, 1)
        self.assertEqual(decision.workers, 1)

    def test_few_expensive_cases_can_use_one_worker_each(self) -> None:
        decision = select_workers(
            backend_family="compiled",
            system=_system(),
            store=_store(8),
            program=_program(),
            config=AutoTuneConfig(profile_path=None),
            probe=AutoTuneProbe("compiled", 2, 0.25, 0.20, 0.01, 16 * 1024**2),
        )
        self.assertEqual(max(decision.candidate_workers), 8)
        self.assertGreater(decision.workers, 1)

    def test_tle_probe_forces_single_process(self) -> None:
        decision = select_workers(
            backend_family="compiled",
            system=_system(),
            store=_store(1_000_000),
            program=_program(),
            config=AutoTuneConfig(profile_path=None),
            probe=AutoTuneProbe("compiled", 1, 0.2, 0.0, 0.0, 0, timed_out=True),
        )
        self.assertEqual(decision.workers, 1)
        self.assertIn("probe_timed_out", decision.reasons)


class AutoPersistentIntegrationTests(unittest.TestCase):
    def test_auto_executes_python_store_and_reports_decision(self) -> None:
        config = AutoTuneConfig(sample_cases=2, probe_timeout_s=0.2, profile_path=None)
        with PersistentPythonRunner(
            FIXTURES / "basic_solution.py",
            main_method="total",
            workers="auto",
            standard_mode=True,
            auto_tune_config=config,
        ) as runner:
            report = runner.run(
                [
                    {"cid": index, "input": ([index, 1], 2), "expected": index + 3}
                    for index in range(20)
                ],
                collect_results=False,
            )
            self.assertEqual(report.correct_count, 20)
            self.assertIsNotNone(report.auto_tune)
            self.assertEqual(report.metrics.workers, report.auto_tune["workers"])
            self.assertLessEqual(report.metrics.workers, 16)

    def test_auto_detects_python_tle_without_parallel_amplification(self) -> None:
        config = AutoTuneConfig(sample_cases=1, probe_timeout_s=0.12, profile_path=None)
        started = time.perf_counter()
        with PersistentPythonRunner(
            FIXTURES / "tle_solution.py",
            main_method="work",
            workers="auto",
            standard_mode=True,
            auto_tune_config=config,
        ) as runner:
            report = runner.run(
                [{"cid": "hang", "input": (True, 0), "expected": 0}],
                timeout_s=0.12,
            )
            self.assertEqual(report.metrics.workers, 1)
            self.assertEqual(report.metrics.timed_out_cases, 1)
            self.assertIn("probe_timed_out", report.auto_tune["reasons"])
        self.assertLess(time.perf_counter() - started, 8.0)


def _cpp_available() -> bool:
    try:
        _toolchain(None)
    except (FileNotFoundError, RuntimeError):
        return False
    return DEFAULT_MANAGER.is_file()


@unittest.skipUnless(_cpp_available(), "C++ manager/compiler is unavailable")
class AutoCompiledIntegrationTests(unittest.TestCase):
    def test_auto_executes_cpp_store(self) -> None:
        cases = [
            {"cid": index, "input": ([index, 1], 2), "expected": index + 3}
            for index in range(20)
        ]
        with tempfile.TemporaryDirectory(prefix="cpp_auto_test_", dir=ROOT) as directory:
            store = Path(directory) / "cases.ojbin"
            CaseStoreWriter.write(store, cases)
            runner = CompiledCppRunner(
                CPP_FIXTURES / "wrong_solution.cpp",
                "total",
                workers="auto",
                workspace=ROOT,
                auto_tune_config=AutoTuneConfig(
                    sample_cases=2, probe_timeout_s=0.2, profile_path=None
                ),
            )
            report = runner.run_store(store)
            self.assertEqual(report.wrong_count, 20)
            self.assertIsNotNone(report.auto_tune)
            self.assertEqual(report.metrics.workers, report.auto_tune["workers"])

    def test_auto_cpp_tle_probe_stays_single_process(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cpp_auto_tle_", dir=ROOT) as directory:
            store = Path(directory) / "cases.ojbin"
            CaseStoreWriter.write(
                store, [{"cid": "hang", "input": (True, 7), "expected": 7}]
            )
            runner = CompiledCppRunner(
                CPP_FIXTURES / "hang_solution.cpp",
                "work",
                workers="auto",
                workspace=ROOT,
                auto_tune_config=AutoTuneConfig(
                    sample_cases=1, probe_timeout_s=0.15, profile_path=None
                ),
            )
            with self.assertRaisesRegex(RuntimeError, r"native C\+\+ manager failed"):
                runner.run_store(store, batch_timeout_s=0.2)
            self.assertIsNotNone(runner.last_auto_tune)
            self.assertEqual(runner.last_auto_tune.workers, 1)
            self.assertIn("probe_timed_out", runner.last_auto_tune.reasons)


if __name__ == "__main__":
    unittest.main(verbosity=2)
