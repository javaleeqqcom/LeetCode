class Solution:
    def total(self, values: list[int], offset: int) -> int:
        # Deliberately mutate the argument to verify case isolation in the runner.
        values.sort()
        return sum(values) + offset
