import math
import random
import time
from concurrent import interpreters, futures
from typing import List
from Solution import Solution
from itertools import chain
from functools import partial

_N_CORE_ = 12

# 测试用例生成
def generate_test_cases(n: int = 10000) -> List[int]:
    """生成 n 个随机 int32 正整数 (1 到 2^31-1)"""
    return [random.randint(1, 2**31 - 1) for _ in range(n)]

def execute_in_interpreter(test_cases: List[int]) -> List[bool]:
    """用 interpreters 创建子 GIL执行求解程序"""
    begin = time.time()
    interpreter = interpreters.create()
    _solution = interpreter.call(Solution)
    # 使用全局 Solution 对象（无需在每个解释器中创建）
    res = [_solution.is_sqrt_prime(num) for num in test_cases]
    interpreter.close()
    end = time.time()
    print(f"{len(test_cases)} test cost: {end-begin:.6f} s")
    return res

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
    split_idx = [(len(test_cases)*i)//_N_CORE_ for i in range(_N_CORE_+1)]
    
    with futures.InterpreterPoolExecutor(max_workers=_N_CORE_) as executor:
        results_parallel = list(chain.from_iterable(
            executor.map(
                execute_in_interpreter,
                [test_cases[split_idx[thread_id]:split_idx[thread_id+1]] for thread_id in range(_N_CORE_)]
            )
        ))
    
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