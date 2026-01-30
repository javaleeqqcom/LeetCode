from typing import List
import numpy as np

class Solution:
    def minimumCost(self, source: str, target: str, original: List[str], changed: List[str], cost: List[int]) -> int:
        inf = float('inf')
        n = len(source)
        
        # 按长度组织字符串
        max_len = max(len(s) for s in original + changed) if original else 0
        str2idx = [dict() for _ in range(max_len + 1)]
        
        # 为每个长度的字符串分配索引
        for x, y in zip(original, changed):
            m = len(x)
            if x not in str2idx[m]:
                str2idx[m][x] = len(str2idx[m])
            if y not in str2idx[m]:
                str2idx[m][y] = len(str2idx[m])
        
        # 为每个长度创建成本矩阵
        dists = []
        for m in range(max_len + 1):
            if str2idx[m]:
                size = len(str2idx[m])
                D = np.full((size, size), inf, dtype=np.float64)
                np.fill_diagonal(D, 0)
                dists.append(D)
            else:
                dists.append(None)
        
        # 设置初始成本
        for x, y, c in zip(original, changed, cost):
            m = len(x)
            idx_x = str2idx[m][x]
            idx_y = str2idx[m][y]
            if c < dists[m][idx_x, idx_y]:
                dists[m][idx_x, idx_y] = c
        
        # Floyd-Warshall 算法（正确实现）
        for m in range(1, max_len + 1):
            if dists[m] is None:
                continue
            size = dists[m].shape[0]
            # 标准的Floyd算法：三层循环，使用临时变量
            for k in range(size):
                for i in range(size):
                    if dists[m][i, k] == inf:
                        continue
                    dists[m][i,:] = np.minimum(dists[m][i,:] , dists[m][i,k] + dists[m][k,:]) # 更新终点
        
        # DP数组：dp[i] = 将source[0:i]转换为target[0:i]的最小成本
        dp = [inf] * (n + 1)
        dp[0] = 0
        
        for i in range(n):  # 当前结束位置
            if dp[i] == inf:
                continue
            
            # 尝试从当前位置i开始的各种长度
            for length in range(1, min(max_len, n - i) + 1):
                j = i + length
                sub_src = source[i:j]
                sub_tar = target[i:j]
                
                # 如果子串相等，可以直接转换，成本为0
                if sub_src == sub_tar:
                    dp[j] = min(dp[j], dp[i])
                else:
                    # 尝试通过转换规则
                    m = length
                    if (dists[m] is not None and 
                        sub_src in str2idx[m] and 
                        sub_tar in str2idx[m]):
                        
                        idx_src = str2idx[m][sub_src]
                        idx_tar = str2idx[m][sub_tar]
                        cost_to_convert = dists[m][idx_src, idx_tar]
                        
                        if cost_to_convert < inf:
                            dp[j] = min(dp[j], dp[i] + cost_to_convert)
        
        return int(dp[n]) if dp[n] < inf else -1