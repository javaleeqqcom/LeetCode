import numpy as np

class PrimeSieve:
    def __init__(self, max_n: int):
        """
        初始化质数筛选器，预计算 [0, max_n] 范围内的所有质数
        """
        self.max_n = max_n
        
        # 1. 创建布尔标记桶（默认全为 True）
        self._is_prime_bucket = np.ones(max_n + 1, dtype=bool)
        self._is_prime_bucket[0] = self._is_prime_bucket[1] = False # 0 和 1 不是质数
        
        # 2. 完美的 NumPy 切片筛法（埃氏筛）
        # 只需要筛选到 sqrt(max_n) 即可
        limit = int(np.sqrt(max_n)) + 1
        for i in range(2, limit):
            if self._is_prime_bucket[i]:
                # 从 i*i 开始，以 i 为步长，全部标记为非质数（False）
                # 这里完美的利用了 NumPy 的底层切片赋值，完全没有 Python 内部循环
                self._is_prime_bucket[i*i :: i] = False
                
        # 3. 提取出所有真正的质数列表（一维数组）
        self.primes = np.nonzero(self._is_prime_bucket)[0]

    def is_prime(self, n: int) -> bool:
        """判断一个数是否为质数（O(1) 复杂度）"""
        if 0 <= n <= self.max_n:
            return bool(self._is_prime_bucket[n])
        raise ValueError(f"数值超出预计算范围 [0, {self.max_n}]")

    def count_primes_up_to(self, n: int) -> int:
        """计算小于等于 n 的质数个数（利用二分查找查找位置，对数复杂度）"""
        if n > self.max_n:
            raise ValueError(f"数值超出预计算范围 [0, {self.max_n}]")
        return int(np.searchsorted(self.primes, n, side='right'))

    def get_prime_factors(self, n: int) -> list:
        """获取 n 的所有质因数（常规因数分解）"""
        if n > self.max_n:
            raise ValueError(f"数值超出预计算范围 [0, {self.max_n}]")
        
        factors = []
        temp = n
        # 只需要遍历可能整除 temp 的质数
        limit = int(np.sqrt(temp)) + 1
        active_primes = self.primes[self.primes <= limit]
        
        for p in active_primes:
            if p * p > temp:
                break
            if temp % p == 0:
                factors.append(int(p))
                while temp % p == 0:
                    temp //= p
        if temp > 1:
            factors.append(int(temp))
        return factors

def test():
    import time

    # 初始化一个一千万大小的质数筛
    start = time.time()
    sieve = PrimeSieve(10_000_000)
    end = time.time()

    print(f"✨ 成功筛选 10,000,000 以内的质数！")
    print(f"⏱️ 耗时: {end - start:.4f} 秒") # 通常只需 0.05 秒左右！
    print(f"📊 质数总个数: {len(sieve.primes)} 个")
    print(f"🔍 前 10 个质数是: {sieve.primes[:10]}")
    print(f"❓ 999983 是质数吗？ {sieve.is_prime(999983)}")

if __name__ == "__main__":
    test()