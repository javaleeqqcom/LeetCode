try: from tools.args_parser import *
except:pass

import numpy as np
INF = 99 #(1<<31)-1

def maxPathScore_dp( grid: List[List[int]], k: int):
    m,n = len(grid), len(grid[0])
    dp = -INF * np.ones((m,n,k+1),dtype=np.int32) # 初始得分为 -INF
    dp[0,0,0] = 0 # 起点 （只能设 k=0 时为0）
    for i in range(m):
        for j in range(n):
            # print(i,j)
            if 0 == grid[i][j]: # 无消耗也无得分
                if i>0:
                    dp[i,j,:] = dp[i-1,j,:]
                if j>0:
                    dp[i,j,:] = np.maximum(dp[i,j,:],dp[i,j-1,:])
            else: # 消耗+1 得分+grid[i][j]
                if i>0:
                    dp[i,j,1:] = grid[i][j] + dp[i-1,j,:-1]
                if j>0:
                    dp[i,j,1:] = np.maximum(dp[i,j,1:], grid[i][j] + dp[i,j-1,:-1])
            # print(dp)
    return dp

class Solution:
    def maxPathScore(self, grid: List[List[int]], k: int) -> int:
        m,n = len(grid), len(grid[0])

        s_dp = maxPathScore_dp(grid,k)

        dp = -INF * np.ones((2,n,k+1),dtype=np.int32) # 初始得分为 -INF
        # dp[i%2,j,c] 表示 grid[i,j] 处在总花费为 c 时的最大得分
        dp[0,0,0] = 0 # 起点（只能设 c=0 时为0，注意 dp[,0,] 中的下标 0 作为哨兵用于自动处理边界）
        for i in range(m):
            if i>0:
                if 0 == grid[i][0]: # 无消耗也无得分
                    dp[i%2,0,:] = dp[1-(i%2),0,:]
                else:
                    dp[i%2,0,0] = -INF
                    dp[i%2,0,1:] = grid[i][0] + dp[1-(i%2),0,:-1]
                    
                print(f"i={i}, j={0}")
                for c in range(1+k):
                    print(f"c={c}")
                    print(dp[:,:,c])
            for j in range(1,n):
                if 0 == grid[i][j]: # 无消耗也无得分
                    dp[i%2,j,:] = np.maximum(dp[1-(i%2),j,:], dp[i%2,j-1,:])
                else: # 消耗+1 得分+grid[i][j]
                    dp[i%2,j,0] = -INF
                    dp[i%2,j,1:] = grid[i][j] + np.maximum(dp[1-(i%2),j,:-1] , dp[i%2,j-1,:-1])

                print(f"i={i}, j={j}")
                for c in range(1+k):
                    print(f"c={c}")
                    print(dp[:,:,c])
        res = np.max(dp[(m-1)%2,n-1,:])
        return max(-1,int(res))