from typing import List
import numpy as np
class Solution:
    def rotateElements(self, nums: List[int], k: int) -> List[int]:
        nums = np.array(nums)
        n = len(nums)
        not_ng = nums >= 0 

        # print(nums)

        not_ng_sub = nums[not_ng]
        m = len(not_ng_sub)
        if m>0:

            # print(not_ng_sub)

            not_ng_sub = np.roll(not_ng_sub, (m-k) % m)

            # print(not_ng_sub)

            nums[not_ng] = not_ng_sub

        return nums.tolist()
    

obj = Solution()
nums =[5,4,-9,6]
k=2
# print(obj.rotateElements(nums, k))