MOD = 10**9+7
def f(ori,cur):
    # if ori*cur < 0 :return -1
    return (ori * cur)

class Solution:
    def maxProductPath(self, grid: List[List[int]]) -> int:
        m,n = len(grid),len(grid[0])
        dp_pos = [[-1]*(n+1) for i in range(m+1)]
        dp_neg = [[-1]*(n+1) for i in range(m+1)]
        if grid[0][0] >= 0:
            dp_pos[1][1] = grid[0][0]
        if grid[0][0] <= 0:
            dp_neg[1][1] = -grid[0][0]
        
        for i in range(m):
            for j in range(n):
                if i==0 and j==0:continue
                if grid[i][j] < 0:
                    dp_pos[i+1][j+1] = f(max(dp_neg[i][j+1] , dp_neg[i+1][j]) , - grid[i][j])
                    dp_neg[i+1][j+1] = f(max(dp_pos[i][j+1] , dp_pos[i+1][j]) , - grid[i][j])
                else:
                    dp_pos[i+1][j+1] = f(max(dp_pos[i][j+1] , dp_pos[i+1][j]) , grid[i][j])
                    dp_neg[i+1][j+1] = f(max(dp_neg[i][j+1] , dp_neg[i+1][j]) , grid[i][j])

        # for i in range(m):
        #     print(",".join(f"{p}|{n}" for p,n in zip(dp_pos[i+1][1:],dp_neg[i+1][1:])))

        return (dp_pos[m][n] % MOD) if dp_pos[m][n] >= 0 else -1
