import numpy as np
class Solution:
    def minimumCost(self, source: str, target: str, original: List[str], changed: List[str], cost: List[int]) -> int:
        # dp[i] = minimumCost(source[:i], target[:i],changed,cost).replace(-1,inf)
        inf = 10**18 # 确保 inf*2 不会溢出
        n = len(source) # 也 == len(target)
        
        # 按长度组织字符串
        max_len = max(len(s) for s in original + changed) if original else 0

        # 由于只能替换相同长度的字符串，故以长度划分
        str2idx = [dict() for _ in range(max_len + 1)]
        for x,y in zip(original,changed):
            m = len(x)
            if x not in str2idx[m]: str2idx[m][x] = len(str2idx[m])
            if y not in str2idx[m]: str2idx[m][y] = len(str2idx[m])

        # 按不同长度的字符串构造转换成本矩阵
        Ds = [None]*(max_len+1)
        for m in range(1,max_len+1):
            if not str2idx[m]: continue
            count = len(str2idx[m])
            Ds[m] = np.full((count,count) , inf, dtype=np.int64)
            np.fill_diagonal(Ds[m] , 0)
        
        # 设置转换成本矩阵的初始值
        for x,y,c in zip(original,changed,cost):
            m = len(x)
            Ds[m][str2idx[m][x],str2idx[m][y]] = min(Ds[m][str2idx[m][x],str2idx[m][y]] ,c )

        # 用 floyd 算法计算所有在str2idx中任意两个长度相同的字符串之间的转换成本
        for m in range(1,max_len+1):
            count = len(str2idx[m])
            if 0==count: continue
            for k in range(count): # 中继节点
                for i in range(count): # 起点
                    if Ds[m][i,k]==inf: continue
                    Ds[m][i,:] = np.minimum(Ds[m][i,:] , Ds[m][i,k] + Ds[m][k,:]) # 更新终点

        # DP数组：dp[i] = 将source[0:i]转换为target[0:i]的最小成本
        dp = [inf] * (n + 1)
        dp[0] = 0
        
        for i in range(n):  # 当前结束位置
            if dp[i] == inf:
                continue
            
            # 尝试从当前位置i开始的各种长度
            for m in range(1, min(max_len, n - i) + 1):
                j = i + m
                sub_src = source[i:j]
                sub_tar = target[i:j]
                
                # 如果子串相等，可以直接转换，成本为0
                if sub_src == sub_tar:
                    dp[j] = min(dp[j], dp[i])
                # 尝试通过转换矩阵进行转换，找到最小成本
                elif ( sub_src in str2idx[m] and sub_tar in str2idx[m]):
                    assert Ds[m] is not None # 只要 sub_src,sub_tar 能在 str2idx[m] 找到，则 Ds[m] 一定存在
                    cost_to_convert = Ds[m][str2idx[m][sub_src], str2idx[m][sub_tar]]
                    
                    if cost_to_convert < inf:
                        dp[j] = min(dp[j], dp[i] + cost_to_convert)
        
        return int(dp[n]) if dp[n] < inf else -1
