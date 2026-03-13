import math
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
