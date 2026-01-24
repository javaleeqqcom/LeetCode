import numpy as np
from typing import List

class Solution:
    def minimumPairRemoval(self, nums: List[int]) -> int:
        nums = np.array(nums, dtype=np.int32)
        ans = 0
        print(f"初始数组: {nums.tolist()}")
        
        # 并非有序
        while np.any(nums[:-1] > nums[1:]):
            # 计算相邻和
            sums = nums[:-1] + nums[1:]
            idx = np.argmin(sums)
            sum_val = sums[idx]
            
            # 打印当前步骤
            print(f"\n步骤 {ans + 1}:")
            print(f"当前数组: {nums.tolist()}")
            print(f"相邻和: {sums.tolist()}")
            print(f"选择索引 {idx} (和 = {sum_val})")
            
            # 合并相邻对
            nums = np.concatenate((nums[:idx], [sum_val], nums[idx+2:]))
            
            # 打印合并后数组
            print(f"合并后数组: {nums.tolist()}")
            
            ans += 1
        
        print(f"\n最终操作次数: {ans}")
        return ans
    
obj = Solution()
arr = [3,6,4,-6,2,-4,5,-7,-3,6,3,-4]
print(obj.minimumPairRemoval(arr))