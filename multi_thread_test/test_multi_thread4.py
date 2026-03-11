import math
import random
import time
import concurrent.futures
from typing import List
from Solution import Solution

# 生成素数表（只在主解释器中执行一次）
def generate_primes(limit: int = 65536) -> List[int]:
    """使用埃拉托斯特尼筛法生成素数表"""
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(math.sqrt(limit)) + 1):
        if sieve[i]:
            sieve[i*i : limit+1 : i] = [False] * len(sieve[i*i : limit+1 : i])
    return [i for i, is_prime in enumerate(sieve) if is_prime]

# 预先生成素数表（只生成一次）
_prime_table = generate_primes(65536)

def init_prime():
    """在每个工作解释器中设置 _prime"""
    import Solution
    Solution.self.prime = _prime_table

def generate_test_cases(n: int = 10000) -> List[int]:
    """生成 n 个随机 int32 正整数 (1 到 2^31-1)"""
    return [random.randint(1, 2**31 - 1) for _ in range(n)]

def main():
    # 生成测试用例
    test_cases = generate_test_cases(100000)
    
    # 顺序执行测试
    start_time = time.time()
    solution = Solution()
    results_seq = [solution.is_sqrt_prime(num) for num in test_cases]
    seq_time = time.time() - start_time
    print(f"顺序执行耗时: {seq_time:.3f} s")
    
    # 正确的并行执行测试 (12 解释器)
    start_time = time.time()
    # 在主解释器中创建 Solution 对象 (只创建一次)
    solution = Solution()
    
    with concurrent.futures.InterpreterPoolExecutor(
        max_workers=12,
        initializer=init_prime  # 关键：在每个工作解释器中设置 _prime
    ) as executor:
        # 提交任务，使用同一个 solution 对象
        futures = [executor.submit(solution.is_sqrt_prime, num) for num in test_cases]
        # 收集结果 (按顺序，与 test_cases 顺序一致)
        results_parallel = [f.result() for f in futures]
    
    parallel_time = time.time() - start_time
    print(f"12 解释器并行耗时: {parallel_time:.3f} s")
    
    # 验证结果一致性
    consistent = all(r1 == r2 for r1, r2 in zip(results_seq, results_parallel))
    print(f"结果一致性: {'✓' if consistent else '✗'}")
    
    # 计算加速比
    speedup = seq_time / parallel_time
    print(f"加速比: {speedup:.2f}x (目标: ~12x)")

if __name__ == '__main__':
    main()