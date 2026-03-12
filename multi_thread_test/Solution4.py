import math
import bisect
from typing import List,Optional,Tuple

# 生成所有 ≤ 65536 的素数（不再依赖全局状态）
def generate_primes(limit: int = 65536) -> List:
    """使用埃拉托斯特尼筛法生成素数表"""
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(math.sqrt(limit)) + 1):
        if sieve[i]:
            sieve[i*i : limit+1 : i] = [False] * len(sieve[i*i : limit+1 : i])
    return list(i for i, is_prime in enumerate(sieve) if is_prime)

_prime = generate_primes(65536)  # 包含所有 ≤ 65536 的素数

# 解答类
class Solution:
    def is_sqrt_prime(self, num: int) -> bool:
        """
        判断是否为开方素数
        1. num 是素数
        2. ceil(sqrt(num)) 也是开方素数
        """
        
        def is_prime(num: int ,hi:Optional[int] = None) -> int:
            assert 0<= num <2**31, "num 必须是 int32 非负整数"
            """高效判断素数 (使用预计算的素数表)"""
            if num < 2:
                return False
            
            # 情况 1: num ≤ 65536，直接查表
            if num <= _prime[-1]:
                # 使用 bisect 进行二分查找
                pos = bisect.bisect_left( _prime , num , hi=hi)
                if pos < len(_prime) and _prime[pos] == num:
                    return pos
                else:
                    return -1 
            
            # 情况 2: num > 65536，使用素数表进行试除
            # 由于 num ≤ 2^32，sqrt(num) ≤ 65536，所以素数表已覆盖所有需要的因子
            sqrt_num = math.isqrt(num)
            for p in _prime:
                if p > sqrt_num:
                    break
                if num % p == 0:
                    return -1
            return len(_prime)

        # 递归判断，直到 num ≤ 2
        pos = None
        while num > 2:
            pos = is_prime(num,pos)
            if -1 == pos:
                return False
            num = math.ceil(math.sqrt(num))
        return num == 2
