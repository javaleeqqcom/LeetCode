try: from tools.args_parser import *
except:pass

INF = (1<<31)-1

class Solution:
    def containsCycle(self, grid: List[List[str]]) -> bool:
        m,n = len(grid),len(grid[0])
        # 关键，不再以布尔值记录，而是记录上一次访问的 step
        visited = [[INF]*n for _ in range(m)]
        # for row in grid:
        #     print(row)

        for s_i in range(m):
            for s_j in range(n):
                if visited[s_i][s_j] < INF:
                    continue
                start_ch = grid[s_i][s_j]

                # print("start:",s_i,s_j,start_ch)

                # 用 DFS 进行遍历
                def dfs(i,j,step):
                    if not (0<=i<m and 0<=j<n and grid[i][j] == start_ch):
                        return False # 非联通
                    # 关键，检查是否与此前访问过的步数差值达到4
                    if step - visited[i][j] >= 4:
                        return True # 找到环
                    if step < visited[i][j]: # 未访问过，或者有更短的路径
                        visited[i][j] = step
                    else: # 访问过，且步数更长，但未达到成环条件
                        return False
                    
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
