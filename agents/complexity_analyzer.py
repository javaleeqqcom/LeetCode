from tools.solution_struct import SolutionStruct, ComplexityHint
import ast
import textwrap

class ComplexityAnalyzer:
    def analyze(self, struct: SolutionStruct) -> ComplexityHint:
        hint = ComplexityHint()
        # 仅做 Python 示例：统计方法中的 for 嵌套层数
        max_depth = 0
        for method in struct.methods:
            depth = self._count_for_depth(method.source_code)
            max_depth = max(max_depth, depth)
        if max_depth <= 1:
            has_loop = any(
                isinstance(node, (ast.For, ast.AsyncFor, ast.While))
                for node in ast.walk(ast.parse(struct.source_code))
            )
            hint.time_complexity = "O(n)" if has_loop else "O(1)"
            hint.estimated_n_limit = 100_000
        elif max_depth == 2:
            hint.time_complexity = "O(n^2)"
            hint.estimated_n_limit = 2_000
        elif max_depth >= 3:
            hint.time_complexity = "O(n^3) or worse"
            hint.estimated_n_limit = 200
        return hint

    @staticmethod
    def _count_for_depth(code: str) -> int:
        if not code.strip():
            return 0
        try:
            tree = ast.parse(textwrap.dedent(code))
        except SyntaxError:
            return 0

        class LoopDepthVisitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.depth = 0
                self.max_depth = 0

            def _visit_loop(self, node) -> None:
                self.depth += 1
                self.max_depth = max(self.max_depth, self.depth)
                self.generic_visit(node)
                self.depth -= 1

            visit_For = _visit_loop
            visit_AsyncFor = _visit_loop
            visit_While = _visit_loop

        visitor = LoopDepthVisitor()
        visitor.visit(tree)
        return visitor.max_depth
