try: from tools.args_parser import *
except:pass

class Solution:
    def containsCycle(self, grid: List[List[str]]) -> bool:
        m,n = len(grid),len(grid[0])
        # 关键，不再以布尔值记录，而是记录上一次访问的 step
        visited = [[-1]*n for _ in range(m)]

        for s_i in range(m):
            for s_j in range(n):
                if -1 != visited[s_i][s_j]:
                    continue
                start_ch = grid[s_i][s_j]
                
                # 用 DFS 进行遍历
                def dfs(i,j,step):
                    if not (0<=i<m and 0<=j<n and grid[i][j] == start_ch):
                        return False # 非联通
                    if -1 == visited[i][j]: # 未访问过
                        visited[i][j] = step
                    # 关键，检查是否与此前访问过的步数差值达到4
                    elif step - visited[i][j] >= 4:
                        return True # 找到环
                    else: # 访问过，但未达到成环条件
                        return False
                    
                    # 递归四个方向，有任何一个方向探测得环即返回真
                    return (dfs(i-1, j, step+1) or dfs(i+1, j, step+1) or
                        dfs(i, j-1, step+1) or dfs(i, j+1, step+1))

                # 从起点开始
                if dfs(s_i,s_j,0):
                    return True
        return False
