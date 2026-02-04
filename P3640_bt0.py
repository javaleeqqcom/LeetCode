
import numpy as np
from typing import List, Optional

# 已经通过测试的函数
def isTrionic(nums: List[int]) -> bool:
    d = np.diff(nums)
    m = len(d)
    print(d)

    p = 0
    while d[p]>0:
        p+=1
        if p == m:
            return False
    if 0==p: return False

    q = p
    while d[q]<0:
        q+=1
        if q == m:
            return False
    if q==p:return False

    return all(d[q:]>0)
class Solution:
    def maxSumTrionic(self, nums: List[int]) -> int:
        preSum = np.cumsum( [0] + nums )
        n = len(nums)
        # print(preSum)
        res = float('-inf')
        for l in range(n-3):
            for r in range(l+3,n):
                if isTrionic(nums[l:r+1]):
                    res = max(res, preSum[r+1]-preSum[l])
        return int(round(res))