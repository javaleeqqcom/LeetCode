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

def execute_in_interpreter(test_queue, results_queue, interpreter_id):
    """在子解释器中执行测试用例"""
    # 每个解释器独立创建Solution实例
    _solution = Solution()
    
    # 从队列中获取测试用例
    results = []
    start_time = time.time()
    
    while True:
        try:
            # 阻塞等待获取测试用例，设置合理超时时间 (小于间隔)
            case_id, num = test_queue.get(timeout=0.0005)
            # 检查是否是结束标记
            if case_id is None:
                break
            
            # 模拟耗时操作，随机时间，以打乱线程的资源获取与输出结果的顺序
            # time.sleep(random.random()*0.01)
            
            results.append((case_id, _solution.is_sqrt_prime(num)))
        except:
            # 队列为空，结束处理
            break
    
    elapsed = time.time() - start_time
    print(f"解释器 {interpreter_id} 处理 {len(results)} 个用例耗时: {elapsed:.6f} s")
    
    # 将结果放入结果队列
    results_queue.put(results)
    return results

def merge_sorted_lists(lists):
    """使用归并排序合并多个已排序列表"""
    from heapq import merge
    
    # 归并排序
    merged = merge(*lists, key=lambda x: x[0])
    
    # 提取结果
    return [(case_id, result) for case_id, result in merged]

def main():
    # 生成测试用例
    test_cases = generate_test_cases(100000)
    
    # 顺序执行测试（用于基准比较）
    start_time = time.time()
    solution = Solution()
    results_seq = [solution.is_sqrt_prime(num) for num in test_cases]
    seq_time = time.time() - start_time
    print(f"顺序执行耗时: {seq_time:.3f} s")
    
    # 创建跨解释器队列
    test_queue = interpreters.create_queue()
    results_queue = interpreters.create_queue()
    
    # 将测试用例放入队列（包含case_id）
    for case_id, num in enumerate(test_cases):
        test_queue.put((case_id, num))
    
    # 放入结束标记（每个解释器一个）
    for _ in range(_N_CORE_):
        test_queue.put((None, None))
    
    # 并行执行测试
    start_time = time.time()
    
    # 创建解释器池
    with concurrent.futures.InterpreterPoolExecutor(max_workers=_N_CORE_) as executor:
        # 启动解释器任务
        futures = [
            executor.submit(execute_in_interpreter, test_queue, results_queue, i)
            for i in range(_N_CORE_)
        ]
        
        # 收集结果
        results_parallel = []
        for _ in range(_N_CORE_):
            results_parallel.append(results_queue.get())
    
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