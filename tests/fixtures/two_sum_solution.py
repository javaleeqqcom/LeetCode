class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        positions = {}
        for index, value in enumerate(nums):
            complement = target - value
            if complement in positions:
                return [positions[complement], index]
            positions[value] = index
        return []
