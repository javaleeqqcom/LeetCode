
import math
from functools import lru_cache
MODULE = 10**9 + 7
class Solution:
    @lru_cache(maxsize=None) # 记忆化递归
    def numberOfStableArrays(self, zero: int, one: int, limit: int) -> int:
        def f(a,b,l)->Tuple:
            if l > a+b:
                l= a+b
            if a>b:
                a,b = b,a
            if a<0:
                return (-1,-1,-1)
            return (a,b,l)
        bit = zero + one
        if zero < 0 or one < 0:
            return 0
        elif limit >= bit:
            return math.comb(bit,one) % MODULE
        else:
            sub = (
                + self.numberOfStableArrays(*f(zero-1,one,limit)),
                + self.numberOfStableArrays(*f(zero,one-1,limit)),
                - self.numberOfStableArrays(*f(zero-limit-1,max(0,one-1),limit)),
                - self.numberOfStableArrays(*f(max(0,zero-1),one-limit-1,limit)),
            )
            print(zero,one,limit,f"sum{sub}={sum(sub)}")
            return sum(sub) % MODULE
