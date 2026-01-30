import numpy as np
class Solution:
    def minimumCost(self, source: str, target: str, original: List[str], changed: List[str], cost: List[int]) -> int:
        # dp[e][b] = minimumCost(source[b:e], target[b:e],changed,cost).replace(-1,inf)
        inf = float('inf')
        n = len(source) # 也 == len(target)
        dp = [[inf]*e + [0] for e in range(n+1)]
        
        # 由于只能替换相同长度的字符串，故以长度划分
        str2idx = [dict() for _ in range(n+1)]
        for x,y in zip(original,changed):
            m = len(x)
            if x not in str2idx[m]: str2idx[m][x] = len(str2idx[m])
            if y not in str2idx[m]: str2idx[m][y] = len(str2idx[m])

        # 按不同长度的字符串构造转换成本矩阵
        Ds = [np.zeros((0,))]*(n+1)
        for m in range(1,n+1):
            if not str2idx[m]: continue
            count = len(str2idx[m])
            D = np.full((count,count) , inf, dtype=np.float64)
            np.fill_diagonal(D, 0)
            Ds[m] = D # pyright: ignore[reportCallIssue]
        
        # 设置转换成本矩阵的初始值
        for x,y,c in zip(original,changed,cost):
            m = len(x)
            Ds[m][str2idx[m][x],str2idx[m][y]] = c

        # 用 floyd 算法计算所有在str2idx中任意两个长度相同的字符串之间的转换成本
        for m in range(1,n+1):
            count = len(str2idx[m])
            if 0==count: continue
            for k in range(count): # 中继节点
                for i in range(count): # 起点
                    Ds[m][i,:] = np.minimum(Ds[m][i,:] , Ds[m][i,k] + Ds[m][k,:]) # 更新终点

        # 遍历 dp
        for e in range(1,n+1):
            for b in range(e-1,-1,-1): # 注意长度由小到大遍历
                m = e-b
                x = source[b:e]
                y = target[b:e]
                # 该子串可直接转化
                if x in str2idx[m] and y in str2idx[m]:
                    dp[e][b] = Ds[m][str2idx[m][x],str2idx[m][y]].item()
                # 同时要尝试分开转化
                dp[e][b] = min(dp[i][b]+dp[e][i] for i in range(b,e))

        for dpi in dp:
            print(",".join("{:>4s}".format(
                "inf" if x == inf else str(int(x))
            ) for x in dpi))
        
        if dp[n][0] == inf:
            return -1
        else:
            return int(dp[n][0])
