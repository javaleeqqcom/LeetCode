import math
from functools import lru_cache
MODULE = 10**9 + 7
class Solution:
    def numberOfStableArrays(self, zero: int, one: int, limit: int) -> int:
        @lru_cache(maxsize=None) # 记忆化递归
        def f(bit: int, zero: int, k: int)->int:
            # 以 1 开头，有 zero 个 0 的 bit 位二进制数中，排除任意连续 k 位相同（全为 0 或全为 1）的个数模 MODULE
            if not (0 <= zero < bit):
                return 0
            if 0 == zero:
                return int(k > bit)
            
            sub = (
                + f(bit - 1,zero,k) ,
                + f(bit - 1,bit - 1 -zero,k) ,
                - f(bit - k + 1,zero,k) if zero >= k else 0
            )

            print(bit,zero,k,f"sum{sub}={sum(sub)}")
            return sum(sub) % MODULE

        return (f(zero + one,zero,limit+1) + f(zero+one,one,limit+1)) % MODULE
