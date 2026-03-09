from functools import lru_cache
MODULE = 10**9 + 7
class Solution:
    def numberOfStableArrays(self, zero: int, one: int, limit: int) -> int:
        k = limit + 1  # 不允许有连续 k 位相同，连续相同位数小于 k 方为合法情况

        @lru_cache(maxsize=None) # 记忆化递归
        def dfs(c0: int, c1: int)->int:
            # 以 1 开头，有 c0 个 0 和 c1 个 1 的二进制数中的合法情况数模 MODULE
            nonlocal k
            if c0 < 0 or c1 <= 0:
                return 0
            if 0 == c0:
                return int(k > c1)
            
            sub = (
                # 1. 以 11 开头的情况，注意递归只是去掉最高位的1个1（因此不是 c1-2），注意其中包含第3点的非法情况数；
                + dfs(c0, c1 - 1) , 
                # 2. 以 10 开头的情况，相当于递归高位为 0，c1-1 个1（去掉最高位1），c0 个0，代入 dfs 互换参数即可；
                + dfs(c1 - 1, c0) , 
                # 3. 第1点需要剔除 11...110x...xx （高位连续 k 位为 1 时，然后接着0）的情况，相当于递归高位为 0，仅剩 c1-k 个1 的情况。
                - dfs(c1 - k, c0)   
            )

            # print(c0,c1,f"sum{sub}={sum(sub)}")
            return sum(sub) % MODULE # 递归正确时 sum(sub) 不可能为负值
        
        return (dfs(one,zero) + dfs(zero,one)) % MODULE
