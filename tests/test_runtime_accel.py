from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runtime.accel import DIGEST_SCHEME, digest_value
from runtime.accel.fallback import digest_value as fallback_digest_value
from runtime.accel.fallback import legacy_digest_value
from runtime.runner import CaseStoreReader, CaseStoreWriter, PersistentPythonRunner
from runtime.runner.case_store import HEADER, INDEX_ENTRY_V1, MAGIC
from runtime.runner.common import can_reuse_expected_digest


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"

try:
    from runtime.accel._result_digest import digest_value as cython_digest_value
except ImportError:
    cython_digest_value = None


class DigestTests(unittest.TestCase):
    def test_expected_digest_requires_exact_json_value_types(self) -> None:
        self.assertTrue(can_reuse_expected_digest([1.0, {"x": 2}], [1.0, {"x": 2}]))
        self.assertFalse(can_reuse_expected_digest(1, 1.0))
        self.assertFalse(can_reuse_expected_digest([1], [1.0]))
        self.assertFalse(can_reuse_expected_digest(-0.0, 0.0))

    def test_python_fast_path_preserves_canonical_digest(self) -> None:
        cases = (
            (0, 0, 7, None),
            (1, -2, -(2**63), None),
            (2, "unicode-编号", [1, 2, {"x": True}], None),
            (3, 3, None, "ValueError: bad input"),
            (4, 4, 10**100, None),
            (5, 5, -0.0, None),
        )
        for case in cases:
            with self.subTest(case=case):
                self.assertEqual(fallback_digest_value(*case), legacy_digest_value(*case))
                self.assertEqual(digest_value(*case), legacy_digest_value(*case))

    @unittest.skipUnless(
        cython_digest_value is not None, "optional Cython accelerator is not built"
    )
    def test_cython_digest_matches_python_fallback(self) -> None:
        for index in range(-1000, 1001, 37):
            case = (index, index * 3, index * index - 17, None)
            self.assertEqual(cython_digest_value(*case), fallback_digest_value(*case))


class PrecomputedDigestTests(unittest.TestCase):
    def test_case_store_v1_remains_readable(self) -> None:
        case = {"cid": "old", "input": [[1, 2], 3], "expected": 6}
        payload = json.dumps(case, separators=(",", ":")).encode("utf-8")
        payload_offset = HEADER.size
        table_offset = payload_offset + len(payload)
        contents = (
            HEADER.pack(MAGIC, 1, 1, table_offset, payload_offset)
            + payload
            + INDEX_ENTRY_V1.pack(payload_offset, len(payload))
        )
        with tempfile.TemporaryDirectory(prefix="digest_store_v1_test_") as directory:
            path = Path(directory) / "cases.ojbin"
            path.write_bytes(contents)
            with CaseStoreReader(path) as reader:
                decoded, expected_digest = reader.read_record(0)
                self.assertEqual(reader.format_version, 1)
                self.assertEqual(decoded["input"], ([1, 2], 3))
                self.assertEqual(decoded["expected"], 6)
                self.assertIsNone(expected_digest)

    def test_case_store_embeds_expected_digest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="digest_store_test_") as directory:
            path = Path(directory) / "cases.ojbin"
            CaseStoreWriter.write(
                path,
                (
                    {"cid": 11, "input": ([1, 2], 3), "expected": 9},
                    {"cid": 12, "input": ([4], 5)},
                ),
            )
            with CaseStoreReader(path) as reader:
                first, first_digest = reader.read_record(0)
                _, second_digest = reader.read_record(1)
                self.assertEqual(
                    first_digest,
                    legacy_digest_value(0, first["cid"], first["expected"], None),
                )
                self.assertIsNone(second_digest)
                self.assertEqual(reader.format_version, 2)

    def test_precomputed_and_full_digest_runs_are_identical(self) -> None:
        cases = [
            {"cid": index, "input": ([index, 1], 2), "expected": index + 3}
            for index in range(200)
        ]
        runner = PersistentPythonRunner(
            FIXTURES / "basic_solution.py",
            main_method="total",
            workers=2,
            capture_stdout=False,
            standard_mode=True,
        )
        try:
            precomputed = runner.run(
                cases,
                collect_results=False,
                use_precomputed_digest=True,
            )
            full = runner.run(
                cases,
                collect_results=False,
                use_precomputed_digest=False,
            )
            self.assertEqual(precomputed.digest, full.digest)
            self.assertEqual(precomputed.digest_scheme, DIGEST_SCHEME)
            self.assertEqual(precomputed.correct_count, len(cases))
            self.assertEqual(full.correct_count, len(cases))
        finally:
            runner.close()

    def test_judge_equal_numeric_types_preserve_actual_output_digest(self) -> None:
        cases = [{"cid": 7, "input": (1,), "expected": 1}]
        runner = PersistentPythonRunner(
            FIXTURES / "float_solution.py",
            main_method="as_float",
            workers=1,
            capture_stdout=False,
            standard_mode=True,
        )
        try:
            precomputed = runner.run(
                cases,
                collect_results=False,
                use_precomputed_digest=True,
            )
            full = runner.run(
                cases,
                collect_results=False,
                use_precomputed_digest=False,
            )
            expected_actual_digest = legacy_digest_value(0, 7, 1.0, None)
            self.assertEqual(precomputed.digest, full.digest)
            self.assertEqual(precomputed.digest, f"{expected_actual_digest:032x}")
        finally:
            runner.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
