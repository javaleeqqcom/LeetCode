class 

class Solution:
    def minimumCost(self, nums: List[int], k: int, dist: int) -> int:
        # 暴力算法：
        # nums[0:i]为第一组
        res = float('inf')
        for i in range(1,len(nums)-dist): 
            # sub 中有 k-1 组，其中第 k 组队头在 sub 中
            sub = sorted(nums[i:i+dist+1])
            # print(sub[:k-1])
            res = min(res, sum(sub[:k-1]))
        return nums[0] + res
