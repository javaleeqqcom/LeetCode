MODULE = 10**9 + 7

class Solution:
    def numberOfStableArrays(self, zero: int, one: int, limit: int) -> int:
        k = limit + 1  # 不允许连续 k 个相同
        
        # dp1[z][o]: 以 1 开头，z 个 0，o 个 1 的合法序列数
        # dp0[z][o]: 以 0 开头，z 个 0，o 个 1 的合法序列数
        dp1 = [[0] * (one + 1) for _ in range(zero + 1)]
        dp0 = [[0] * (one + 1) for _ in range(zero + 1)]
        
        # 边界条件：zero = 0 时（只有 1）
        for o in range(1, one + 1):
            dp1[0][o] = 1 if o < k else 0
        
        # 边界条件：one = 0 时（只有 0）
        for z in range(1, zero + 1):
            dp0[z][0] = 1 if z < k else 0
        
        # DP 填表：按 zero + one 递增的顺序
        for total in range(2, zero + one + 1):
            for z in range(max(0, total - one), min(zero, total) + 1):
                o = total - z
                if o < 1:
                    continue
                
                # dp1[z][o]: 以 1 开头
                # 下一个放 1: dp1[z][o-1]
                # 下一个放 0: dp0[z][o-1] (角色交换)
                # 减去连续 k 个 1 的情况: dp0[z][o-k]
                dp1[z][o] = dp1[z][o - 1]
                if z >= 1:
                    dp1[z][o] = (dp1[z][o] + dp0[z][o - 1]) % MODULE
                if o >= k and z >= 1:
                    dp1[z][o] = (dp1[z][o] - dp0[z][o - k] + MODULE) % MODULE
                
                # dp0[z][o]: 以 0 开头
                # 下一个放 0: dp0[z-1][o]
                # 下一个放 1: dp1[z-1][o] (角色交换)
                # 减去连续 k 个 0 的情况: dp1[z-k][o]
                if z >= 1:
                    dp0[z][o] = dp0[z - 1][o]
                    if o >= 1:
                        dp0[z][o] = (dp0[z][o] + dp1[z - 1][o]) % MODULE
                    if z >= k and o >= 1:
                        dp0[z][o] = (dp0[z][o] - dp1[z - k][o] + MODULE) % MODULE
        
        # 答案：以 1 开头 + 以 0 开头
        return (dp1[zero][one] + dp0[zero][one]) % MODULE