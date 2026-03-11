import random
import time
import concurrent.futures
from typing import List
from Solution import Solution

# 测试用例生成
def generate_test_cases(n: int = 10000) -> List[int]:
    """生成 n 个随机 int32 正整数 (1 到 2^31-1)"""
    return [random.randint(1, 2**31 - 1) for _ in range(n)]

def create_solution_and_check(num):
    """在工作解释器中创建 Solution 对象并检查"""
    solution = Solution()
    return solution.is_sqrt_prime(num)

def main():
    # 生成测试用例
    test_cases = generate_test_cases(100000)
    
    
    # 顺序执行测试
    start_time = time.time()
    solution = Solution()
    results_seq = [solution.is_sqrt_prime(num) for num in test_cases]
    seq_time = time.time() - start_time
    print(f"顺序执行耗时: {seq_time:.3f} s")
    
    # 正确的并行执行测试
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        # 提交任务，传递 num 和 prime
        futures = [executor.submit(create_solution_and_check, num) for num in test_cases]
        # 收集结果
        results_parallel = [f.result() for f in concurrent.futures.as_completed(futures)]
    
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