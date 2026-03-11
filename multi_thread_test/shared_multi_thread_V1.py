import math
import random
import time
import concurrent.futures
from concurrent import interpreters
from typing import List
from Solution3 import Solution
from itertools import chain

_N_CORE_ = 12
_N_THREAD_ = 100

# 测试用例生成
def generate_test_cases(n: int = 10000) -> List[int]:
    """生成 n 个随机 int32 正整数 (1 到 2^31-1)"""
    return [random.randint(1, 2**31 - 1) for _ in range(n)]

_solution = Solution()
def consumers(shared_queue ,test_cases: List[int]) -> List[bool]:
    """用 interpreters 创建子 GIL执行求解程序"""
    ... 待改造为阻塞式消费
    # 使用全局 Solution 对象（无需在每个解释器中创建）
    res = [_solution.is_sqrt_prime(num) for num in test_cases]
    return res

def main():
    # 生成测试用例
    test_cases = generate_test_cases(1000000)
    
    # 顺序执行测试
    start_time = time.time()
    solution = Solution()
    results_seq = [solution.is_sqrt_prime(num) for num in test_cases]
    seq_time = time.time() - start_time
    print(f"顺序执行耗时: {seq_time:.3f} s")
    

    # 正确的并行执行测试 (12 解释器)
    start_time = time.time()
    # 创建跨解释器队列
    shared_queue = interpreters.create_queue()
    
    split_idx = [(len(test_cases)*i)//_N_THREAD_ for i in range(_N_THREAD_+1)]
    with concurrent.futures.InterpreterPoolExecutor(max_workers= _N_CORE_) as executor:
        # 启动子线程
        futures = [executor.submit(consumers, shared_queue, ?) 
                  for _ in range(_N_CORE_)]
        
        for thread_id in range(_N_THREAD_):
            # 阻塞式生产，等待子线程消费
            shared_queue.put(
                (
                    thread_id,
                    test_cases[split_idx[thread_id]:split_idx[thread_id+1]]
                )
            )
        
        # 合并 futures 的结果，按 thread_id 顺序进行 chain
        results_parallel = ...

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