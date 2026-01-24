import numpy as np
class Solution:
    def minimumPairRemoval(self, nums: List[int]) -> int:
        nums = np.array(nums,dtype=np.int32)
        ans = 0
        # 并非有序
        while np.any(nums[:-1]>nums[1:]):
            # Select the adjacent pair with the minimum sum in nums. 
            idx = np.argmin(nums[:-1]+nums[1:])
            # Replace the pair with their sum.
            nums = np.concatenate((nums[:idx],[nums[idx:idx+2].sum()],nums[idx+2:]))
            ans += 1
        return ans

