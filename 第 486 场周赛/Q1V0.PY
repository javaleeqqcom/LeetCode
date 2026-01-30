import numpy as np
class Solution:
    def minimumPrefixLength(self, nums: List[int]) -> int:
        diff = np.diff(nums)
        for i in range(len(diff)-1,-1,-1):
            if diff[i] <= 0:
                return i + 1 
        return 0