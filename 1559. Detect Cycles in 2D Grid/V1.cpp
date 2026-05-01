class Solution {
public:
    bool containsCycle(vector<vector<char>>& grid) {
        int m = grid.size();
        int n = grid[0].size();
        // 记录步数戳
        vector<vector<int>> visited(m, vector<int>(n, -1));
        for (int si = 0; si < m; ++si) {
            for (int sj = 0; sj < n; ++sj) {
                if(-1 != visited[si][sj]){
                    continue; // 跳过已访问
                }
                char start_ch = grid[si][sj];
                
                // DFS 闭包，使用 std::function 实现递归
                function<bool(int, int, int)> dfs = [&](int i, int j, int step) -> bool {
                    // 越界或字符不同
                    if (i < 0 || i >= m || j < 0 || j >= n || grid[i][j] != start_ch)
                        return false;
                    if(-1 == visited[i][j]){ // 未访问过
                        visited[i][j] = step;
                    }else if(step - visited[i][j] >= 4){
                        return true; // 步数 ≥4 且回到起点 → 找到环
                    }else{ // 已访问过
                        return false;
                    }
                    // 递归四个方向，有任何一个方向探测得环即返回真
                    return (dfs(i - 1, j, step + 1) || dfs(i + 1, j, step + 1) || 
                        dfs(i, j - 1, step + 1) || dfs(i, j + 1, step + 1) );
                };
                
                if (dfs(si, sj, 0))  return true;
            }
        }
        return false;
    }
};