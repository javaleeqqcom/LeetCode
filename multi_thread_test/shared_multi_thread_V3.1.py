import math
import random
import time
import concurrent.futures
from concurrent import interpreters
from typing import List, Tuple
from Solution3 import Solution
from itertools import chain

_N_CORE_ = 12
_N_THREAD_ = 100

# 测试用例生成
def generate_test_cases(n: int = 10000) -> List[int]:
    """生成 n 个随机 int32 正整数 (1 到 2^31-1)"""
    return [random.randint(1, 2**31 - 1) for _ in range(n)]

def geometric_decreasing_queue_generator(test_cases: List[int], rate: float = 0.9, n_core: int = _N_CORE_) -> List[List[Tuple[int, int]]]:
    """将测试用例分割为若干个子列表，越往后子列表的大小呈等比递减，以便维持各线程基本同时收工"""
    n = len(test_cases)
    chunks = []
    remaining = n
    
    # 首先，将前 90% 的用例按 n_core 平分
    for _ in range(n_core):
        if remaining <= 0:
            break
        chunk_size = remaining // n_core
        # 为当前块中的每个测试用例分配唯一ID
        chunk = [(i, num) for i, num in enumerate(test_cases[:chunk_size], start=len(chunks))]
        chunks.append(chunk)
        test_cases = test_cases[chunk_size:]
        remaining -= chunk_size
    
    # 然后，将剩余的用例按 rate 递减加入到 chunks 中
    current_size = max(1, int(remaining * rate / n_core))
    while remaining > 0:
        chunk_size = max(1, int(current_size * rate))
        if chunk_size > remaining:
            chunk_size = remaining
        
        # 为当前块中的每个测试用例分配唯一ID
        chunk = [(i, num) for i, num in enumerate(test_cases[:chunk_size], start=len(chunks))]
        chunks.append(chunk)
        test_cases = test_cases[chunk_size:]
        remaining -= chunk_size
        current_size = chunk_size
    
    return chunks

def execute_in_interpreter(test_cases: List[Tuple[int, int]], interpreter_id: int) -> List[Tuple[int, bool]]:
    """在子解释器中执行测试用例"""
    # 每个解释器独立创建Solution实例
    _solution = Solution()
    
    # 执行测试用例
    results = []
    start_time = time.time()
    
    for case_id, num in test_cases:
        results.append((case_id, _solution.is_sqrt_prime(num)))
    
    elapsed = time.time() - start_time
    print(f"解释器 {interpreter_id} 处理 {len(results)} 个用例耗时: {elapsed:.6f} s")
    
    return results

def merge_sorted_lists(lists) -> List[Tuple[int, bool]]:
    """使用归并排序合并多个已排序列表"""
    from heapq import merge
    
    # 确保所有列表都是按case_id排序的
    # 将每个列表转换为生成器
    generators = [iter(lst) for lst in lists]
    
    # 归并排序
    merged = merge(*generators, key=lambda x: x[0])
    
    # 提取结果
    return [(case_id, result) for case_id, result in merged]

def main():
    # 生成测试用例
    test_cases = generate_test_cases(1000000)
    
    # 顺序执行测试（用于基准比较）
    start_time = time.time()
    solution = Solution()
    results_seq = [solution.is_sqrt_prime(num) for num in test_cases]
    seq_time = time.time() - start_time
    print(f"顺序执行耗时: {seq_time:.3f} s")
    
    # 使用等比递减队列生成器分割测试用例
    chunks = geometric_decreasing_queue_generator(test_cases)
    
    # 并行执行测试
    start_time = time.time()
    
    # 创建解释器池
    with concurrent.futures.InterpreterPoolExecutor(max_workers=_N_CORE_) as executor:
        # 启动解释器任务
        futures = [
            executor.submit(execute_in_interpreter, chunk, i)
            for i, chunk in enumerate(chunks)
        ]
        
        # 收集结果
        results_parallel = []
        for future in concurrent.futures.as_completed(futures):
            results_parallel.extend(future.result())
    
    # 使用归并排序合并结果
    results_parallel = merge_sorted_lists(results_parallel)
    
    # 提取结果值
    results_parallel = [res for _, res in results_parallel]
    
    parallel_time = time.time() - start_time
    print(f"\n{_N_CORE_} 解释器并行耗时: {parallel_time:.3f} s")
    
    # 验证结果一致性
    consistent = all(r1 == r2 for r1, r2 in zip(results_seq, results_parallel))
    print(f"结果一致性: {'✓' if consistent else '✗'}")
    
    # 计算加速比
    speedup = seq_time / parallel_time
    print(f"加速比: {speedup:.2f}x (目标: ~{_N_CORE_}x)")

if __name__ == '__main__':
    main()