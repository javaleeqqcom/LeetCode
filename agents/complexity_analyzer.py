from tools.solution_struct import SolutionStruct, ComplexityHint

class ComplexityAnalyzer:
    def analyze(self, struct: SolutionStruct) -> ComplexityHint:
        hint = ComplexityHint()
        # 仅做 Python 示例：统计方法中的 for 嵌套层数
        max_depth = 0
        for method in struct.methods:
            depth = self._count_for_depth(method.source_code)
            max_depth = max(max_depth, depth)
        if max_depth <= 1:
            hint.time_complexity = "O(n)" if "for" in struct.source_code else "O(1)"
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
        depth = 0
        max_depth = 0
        for line in code.split('\n'):
            stripped = line.strip()
            if stripped.startswith("for ") or stripped.startswith("while "):
                depth += 1
                max_depth = max(max_depth, depth)
            # 简化：假设缩进减少一层即结束一个循环（不精确但够用）
            elif not stripped and depth > 0:
                pass   # 实际实现应基于缩进，这里仅示意
        return max_depth