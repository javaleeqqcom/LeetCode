class Solution {
public:
    bool containsCycle(vector<vector<char>>& grid) {
        int m = grid.size();
        int n = grid[0].size();
        for (int si = 0; si < m; ++si) {
            for (int sj = 0; sj < n; ++sj) {
                // 记录当前起点是否被访问过
                vector<vector<bool>> visited(m, vector<bool>(n, false));
                char start_ch = grid[si][sj];
                
                // DFS 闭包，使用 std::function 实现递归
                function<bool(int, int, int)> dfs = [&](int i, int j, int step) -> bool {
                    // 越界或字符不同
                    if (i < 0 || i >= m || j < 0 || j >= n || grid[i][j] != start_ch)
                        return false;
                    // 步数 ≥4 且回到起点 → 找到环
                    if (step >= 4 && i == si && j == sj)
                        return true;
                    // 已访问过
                    if (visited[i][j])
                        return false;
                    visited[i][j] = true;
                    // 四个方向探索
                    if (dfs(i - 1, j, step + 1)) return true;
                    if (dfs(i + 1, j, step + 1)) return true;
                    if (dfs(i, j - 1, step + 1)) return true;
                    if (dfs(i, j + 1, step + 1)) return true;
                    return false;
                };
                
                if (dfs(si, sj, 0))
                    return true;
            }
        }
        return false;
    }
};