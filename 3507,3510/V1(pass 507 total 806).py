"""
解答错误
507 / 806 个通过的测试用例
提交于 2026.01.22 17:45

官方题解
输入
nums =
[2,2,-1,3,-2,2,1,1,1,0,-1]

添加到测试用例
输出
10
预期结果
9
"""
import numpy as np
class Solution:
    def minimumPairRemoval(self, nums: List[int]) -> int:
        nums = np.array(nums,dtype=np.int32)
        ans = 0
        inf = int(1e9)
        # 并非有序
        while np.any(nums[:-1]>nums[1:]):
            # 构造查询表，按相邻从小到大，同大按序号小者优先
            adj_sum = sorted(list(zip(nums[:-1]+nums[1:] ,range(len(nums)-1) )) )
            adjusted_min_sum = inf

            # 用外部排序的思想，每次取最小的两个数进行合并，但是需要确保求和不得大于 adjusted_min_sum
            for a,j in adj_sum:
                if a < adjusted_min_sum:
                    nums[j] = a
                    nums[j+1] = inf # 用 inf 表示待删除的元素
                    # 重点！更新 adjusted_min_sum，确保后续的合并操作不会破坏有序性：新插入的 a 与其相邻元素的和不会小于后续 adj_sum 的元素，否则会破坏有序性。
                    adjusted_min_sum = min(adjusted_min_sum, a + nums[j-1] if j>=1 else inf , a + nums[j+2] if j+2<len(nums) else inf)
                    ans += 1
                else: # 下一个最小相邻元素和是未更新再 adj_sum 中的元素，需要刷新 nums
                    nums = nums[np.where(nums != inf)]
                    break # 跳出本轮 adj_sum 的循环，开始下一轮的合并操作。

        return ans

