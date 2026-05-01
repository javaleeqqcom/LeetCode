try: from tools.args_parser import *
except:pass

# 超出时间限制

class Solution:
    def containsCycle(self, grid: List[List[str]]) -> bool:
        m,n = len(grid),len(grid[0])

        # for row in grid:
        #     print(row)

        for s_i in range(m):
            for s_j in range(n):
                # 暴力算法，每个起点都重新遍历
                visited = [[False]*n for _ in range(m)]
                start_ch = grid[s_i][s_j]
                # print("start:",s_i,s_j,start_ch)

                # 用 DFS 进行遍历
                def dfs(i,j,step):
                    if not (0<=i<m and 0<=j<n and grid[i][j] == start_ch):
                        return False # 非联通
                    # 关键，达到4步后检查是否回到起点
                    if step >= 4 and i==s_i and j==s_j:
                        return True # 找到环
                    # 检查是否访问过
                    if visited[i][j]: 
                        return False
                    visited[i][j] = True
                    # print("dfs: ",i,j,step)
                    # 检查后继（DFS）
                    if dfs(i-1,j,step+1):
                        return True
                    if dfs(i+1,j,step+1):
                        return True
                    if dfs(i,j-1,step+1):
                        return True
                    if dfs(i,j+1,step+1):
                        return True
                    return False
                # 从起点开始
                if dfs(s_i,s_j,0):
                    return True
        return False
