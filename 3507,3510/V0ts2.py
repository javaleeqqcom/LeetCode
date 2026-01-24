import numpy as np
from typing import List

def print_arr_with_idx(arr,idx):
    # out.append("{}{}".format("^"if idx==i else "",link[idx].val))
    print("[{}]".format(",".join(
        "{}{}".format("^"if idx==i else "",arr[i]) for i in range(len(arr))
    )))

class Solution:
    def minimumPairRemoval(self, nums: List[int]) -> int:
        nums = np.array(nums, dtype=np.int32)
        ans = 0
        
        # 并非有序
        while np.any(nums[:-1] > nums[1:]):
            # 计算相邻和
            sums = nums[:-1] + nums[1:]
            idx = np.argmin(sums)
            sum_val = sums[idx]
            
            # 打印当前步骤
            print(f"步骤 {ans + 1}: sum_adj={sum_val}")
            print_arr_with_idx(nums.tolist(),idx)
            
            # 合并相邻对
            nums = np.concatenate((nums[:idx], [sum_val], nums[idx+2:]))
            
            ans += 1
        
        # 打最终数组
        print_arr_with_idx(nums.tolist(), -1)

        return ans
    
obj = Solution()
arr = [3,4,1,1,-3,2,4,3]
print(obj.minimumPairRemoval(arr))