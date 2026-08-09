from __future__ import annotations

import tempfile
import time
import unittest
import warnings
import json
import os
from pathlib import Path

from tools.args_parser import (
    List2ListNode,
    List2TreeNode,
    ListNode2List,
    TreeNode2List,
    parse_output_to_standard,
)
from tools.cases_generator import (
    build_test_cases,
    quantize_scales,
    quantize_size_2D,
    sample_lognormal_scales,
)
from tools.examples_parser import _parse_labeled_cases, _parse_tuple_style_case
from tools.solution_runner import SolutionRunner
from agents.agent_io import AgentIO
from agents.analyze_agent import AnalyzeAgent
from agents.complexity_analyzer import ComplexityAnalyzer
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from schemas.problem_context import ProblemContext


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"


class ConversionTests(unittest.TestCase):
    def test_list_node_round_trip_and_empty_input(self) -> None:
        self.assertIsNone(List2ListNode([]))
        head = List2ListNode([1, 2, 3])
        self.assertEqual(ListNode2List(head), [1, 2, 3])
        self.assertEqual(parse_output_to_standard(head), [1, 2, 3])

    def test_link_cycle_is_rejected(self) -> None:
        head = List2ListNode([1, 2, 3])
        assert head is not None and head.next is not None and head.next.next is not None
        head.next.next.next = head.next
        with self.assertRaisesRegex(ValueError, "存在环"):
            ListNode2List(head)

    def test_tree_round_trip_and_invalid_graph(self) -> None:
        root = List2TreeNode([1, 2, 3, None, 4])
        self.assertEqual(TreeNode2List(root), [1, 2, 3, None, 4])
        assert root is not None and root.left is not None
        root.right = root.left
        with self.assertRaisesRegex(ValueError, "环或共享子节点"):
            TreeNode2List(root)

    def test_container_cycle_is_rejected(self) -> None:
        value: list[object] = []
        value.append(value)
        with self.assertRaisesRegex(ValueError, "循环引用"):
            parse_output_to_standard(value)


class ExampleParserTests(unittest.TestCase):
    def test_official_english_format(self) -> None:
        cases = _parse_labeled_cases(
            "Input: nums = [2,7,11,15], target = 9\nOutput: [0,1]",
            params_num=2,
        )
        self.assertEqual(
            cases,
            [{"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1]}],
        )

    def test_chinese_full_width_colon_and_json_keywords(self) -> None:
        cases = _parse_labeled_cases(
            '输入：head = [true, null, "false"]\n输出：[true, null, "false"]',
            params_num=1,
        )
        self.assertEqual(
            cases,
            [{"input": {"head": [True, None, "false"]}, "expected": [True, None, "false"]}],
        )

    def test_plain_tuple_stream(self) -> None:
        self.assertEqual(
            _parse_tuple_style_case(["1", "2", "3", "4"], 2),
            [{"input": (1, 2)}, {"input": (3, 4)}],
        )


class RandomCaseTests(unittest.TestCase):
    def test_random_scale_pipeline(self) -> None:
        scales = sample_lognormal_scales(
            2_000, mean_scale=100, second_moment=100_000, seed=7
        )
        sizes = quantize_scales(scales, min_scale=1, max_scale=10_000)
        pairs = quantize_size_2D(
            scales[:100],
            bound=((1, 1_000), (1, 1_000)),
            beta=(1, 1),
            seed=7,
        )
        self.assertEqual(scales.shape, (2_000,))
        self.assertTrue(((1 <= sizes) & (sizes <= 10_000)).all())
        self.assertEqual(pairs.shape, (100, 2))

    def test_build_cases_and_validation(self) -> None:
        cases = build_test_cases(lambda size: {"input": ([size],)}, [1, 2])
        self.assertEqual(cases, [{"input": ([1],), "cid": 0}, {"input": ([2],), "cid": 1}])
        with self.assertRaises(ValueError):
            sample_lognormal_scales(1, mean_scale=1, second_moment=0.5)


class RunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.log_dir = tempfile.TemporaryDirectory(prefix="leetcode_runner_")

    def tearDown(self) -> None:
        self.log_dir.cleanup()

    def test_direct_execution_comparison_and_input_isolation(self) -> None:
        runner = SolutionRunner(FIXTURES / "basic_solution.py")
        cases = [
            {"cid": "a", "input": ([3, 1], 2), "expected": 6},
            {"cid": "b", "input": ([5, 2], -1), "expected": 6},
        ]
        original = [case["input"][0][:] for case in cases]
        results = runner.run(cases, log_folder=self.log_dir.name)
        self.assertEqual([item["output"] for item in results], [6, 6])
        self.assertEqual([case["input"][0] for case in cases], original)
        self.assertEqual(runner.summary_results(results, verbose=False), (2, 2))

    def test_multiprocess_does_not_drop_queued_results(self) -> None:
        runner = SolutionRunner(FIXTURES / "basic_solution.py")
        cases = [
            {"cid": index, "input": ([index, 1], 0), "expected": index + 1}
            for index in range(24)
        ]
        results = runner.run(cases, log_folder=self.log_dir.name, thread=2)
        self.assertEqual(len(results), len(cases))
        self.assertEqual(runner.summary_results(results, verbose=False), (24, 24))

    def test_custom_caller_supports_multiple_solution_methods(self) -> None:
        runner = SolutionRunner(FIXTURES / "multi" / "multi_solution.py")
        cases = [
            {"cid": "add", "input": ("add", 2, 3), "expected": 5},
            {"cid": "multiply", "input": ("multiply", 4, 5), "expected": 20},
        ]
        direct = runner.run(cases, log_folder=self.log_dir.name)
        parallel = runner.run(cases, log_folder=self.log_dir.name, thread=2)
        self.assertEqual([item["output"] for item in direct], [5, 20])
        self.assertEqual([item["output"] for item in parallel], [5, 20])

    def test_worker_count_is_not_hard_capped(self) -> None:
        runner = SolutionRunner(FIXTURES / "basic_solution.py")
        requested_workers = (os.cpu_count() or 1) + 1
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            results = runner.run(
                [{"cid": 0, "input": ([1], 0), "expected": 1}],
                log_folder=self.log_dir.name,
                thread=requested_workers,
            )
        self.assertEqual(results[0]["output"], 1)
        self.assertTrue(any("超过逻辑处理器数" in str(item.message) for item in caught))

    def test_timeout_worker_is_replaced(self) -> None:
        runner = SolutionRunner(FIXTURES / "slow_solution.py")
        started = time.perf_counter()
        results = runner.run(
            [
                {"cid": "hang", "input": (True, 0), "expected": 0},
                {"cid": "next", "input": (False, 42), "expected": 42},
            ],
            log_folder=self.log_dir.name,
            thread=1,
            timeout_s=0.35,
            skip_error=True,
        )
        elapsed = time.perf_counter() - started
        self.assertEqual([item["cid"] for item in results], ["hang", "next"])
        self.assertIn("TLE", results[0]["error"])
        self.assertEqual(results[1]["output"], 42)
        self.assertLess(elapsed, 5.0)


class AgentValidationTests(unittest.TestCase):
    def test_complexity_analyzer_distinguishes_sequential_and_nested_loops(self) -> None:
        sequential = """
def f(values):
    for value in values:
        pass
    for value in values:
        pass
"""
        nested = """
def f(values):
    for left in values:
        for right in values:
            pass
"""
        self.assertEqual(ComplexityAnalyzer._count_for_depth(sequential), 1)
        self.assertEqual(ComplexityAnalyzer._count_for_depth(nested), 2)

    def test_solution_struct_retains_dynamic_method_source(self) -> None:
        runner = SolutionRunner(FIXTURES / "basic_solution.py")
        struct = runner.build_solution_struct()
        self.assertIn("def total", struct.methods[0].source_code)

    def test_generator_is_validated_in_isolated_process(self) -> None:
        code = """
import random
def case_generator(scale):
    n = max(1, int(scale))
    return {"input": ([random.randint(0, 10) for _ in range(n)],)}
"""
        self.assertEqual(AgentIO.validate_case_generator(code), (True, ""))

    def test_chinese_source_crosses_isolated_process_boundary(self) -> None:
        code = '''
def case_generator(scale):
    """中文注释不应受 Windows 控制台代码页影响。"""
    return {"input": (int(scale),)}
'''
        self.assertEqual(AgentIO.validate_case_generator(code), (True, ""))

    def test_unsafe_import_is_rejected(self) -> None:
        code = 'import os\ndef case_generator(scale):\n    return {"input": ()}'
        valid, reason = AgentIO.validate_case_generator(code)
        self.assertFalse(valid)
        self.assertIn("不允许导入", reason)

    def test_unbounded_rejection_sampling_is_rejected(self) -> None:
        code = 'def case_generator(scale):\n    while True:\n        return {"input": ()}'
        valid, reason = AgentIO.validate_case_generator(code)
        self.assertFalse(valid)
        self.assertIn("while True", reason)

    def test_reserved_output_key_is_rejected(self) -> None:
        code = 'def case_generator(scale):\n    return {"input": (), "output": 1}'
        valid, reason = AgentIO.validate_case_generator(code)
        self.assertFalse(valid)
        self.assertIn("reserved keys", reason)

    def test_analyze_prompt_matches_runtime_variables(self) -> None:
        payload = {
            "language": "python",
            "main_function": "total",
            "function_type": "unique_call",
            "input_style": "args",
            "need_conversion": False,
            "custom_types": [],
            "complexity": {
                "time_complexity": "O(n)",
                "space_complexity": "O(1)",
                "bottleneck": "scan",
            },
            "scale_config": {
                "num": 100,
                "mean_scale": 10,
                "second_moment": 1000,
                "distribution": "lognormal",
            },
            "test_strategy": ["random"],
            "edge_cases": ["empty"],
            "stress_patterns": ["large"],
            "algorithm_type": "array",
            "difficulty": "easy",
            "knowledge_requirements": ["array generator"],
        }
        fake_llm = RunnableLambda(lambda _: AIMessage(content=json.dumps(payload)))
        runner = SolutionRunner(FIXTURES / "basic_solution.py")
        problem = ProblemContext(
            title="sum",
            description="sum values",
            examples=[],
            constraints="",
            tags=["array"],
            solution_struct=runner.build_solution_struct(),
            problem_dir=Path(self.id()),
        )
        analysis = AnalyzeAgent(llm=fake_llm).run(problem)
        self.assertEqual(analysis.main_function, "total")
        self.assertEqual(analysis.complexity.time_complexity, "O(n)")

    def test_generator_timeout_is_detected(self) -> None:
        code = 'def case_generator(scale):\n    while scale >= 0:\n        pass'
        started = time.perf_counter()
        valid, reason = AgentIO.validate_case_generator(code)
        self.assertFalse(valid)
        self.assertIn("超过 5 秒", reason)
        self.assertLess(time.perf_counter() - started, 7.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
