class Solution {
public:
    int minOperations(vector<vector<int>>& grid, int x) {
        vector<int> L;
        // 展平
        for (auto& row : grid) {
            for (int v : row) {
                L.push_back(v);
            }
        }
        int n = L.size();
        // 同余检查：所有元素与 L[0] 模 x 同余
        int base_mod = L[0] % x;
        for (int v : L) {
            if (v % x != base_mod) {
                return -1;
            }
        }
        // 排序取中位数
        sort(L.begin(), L.end());
        int mid = L[n / 2];   // 实际上可以取任意最接近中位数的两个数
        // 计算操作次数
        long long ops = 0;
        for (int v : L) {
            ops += abs(v - mid);
        }
        return (int)ops/x; // 最后计算除法节约资源
    }
};