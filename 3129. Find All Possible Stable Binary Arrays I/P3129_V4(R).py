import math
from functools import lru_cache
MODULE = 10**9 + 7
class Solution:
    def numberOfStableArrays(self, zero: int, one: int, limit: int) -> int:
        @lru_cache(maxsize=None) # 记忆化递归
        def dfs(zero: int, one: int,  k: int)->int:
            # 以 1 开头，有 zero 个 0 、one 个 1 的二进制数中，排除任意连续 k 位相同（全为 0 或全为 1）的个数模 MODULE
            if zero < 0 or one <= 0:
                return 0
            if 0 == zero:
                return int(k > one)
            
            sub = (
                + dfs(zero,one - 1,k) ,
                + dfs(one - 1,zero,k) ,
                - dfs(one - k,zero,k) 
            )

            # print(one,zero,k,f"sum{sub}={sum(sub)}")
            return sum(sub) % MODULE

        return (dfs(one,zero,limit+1) + dfs(zero,one,limit+1)) % MODULE
