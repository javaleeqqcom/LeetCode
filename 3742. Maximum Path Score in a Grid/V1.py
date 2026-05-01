try: from tools.args_parser import *
except:pass

import numpy as np
INF = (1<<31)-1
class Solution:
    def maxPathScore(self, grid: List[List[int]], k: int) -> int:
        m,n = len(grid), len(grid[0])
        dp = -INF * np.ones((m,n,k+1),dtype=np.int32) # 初始得分为 -INF
        dp[0,0,0] = 0 # 起点 （只能设 k=0 时为0）
        for i in range(m):
            for j in range(n):
                # print(i,j)
                if 0 == grid[i][j]: # 无消耗也无得分
                    if i>0:
                        dp[i,j,:] = np.maximum(dp[i,j,:],dp[i-1,j,:])
                    if j>0:
                        dp[i,j,:] = np.maximum(dp[i,j,:],dp[i,j-1,:])
                else: # 消耗+1 得分+grid[i][j]
                    if i>0:
                        dp[i,j,1:] = np.maximum(dp[i,j,1:], grid[i][j] + dp[i-1,j,:-1])
                    if j>0:
                        dp[i,j,1:] = np.maximum(dp[i,j,1:], grid[i][j] + dp[i,j-1,:-1])
                # print(dp)
        res = np.max(dp[m-1,n-1,:])
        return max(-1,int(res))