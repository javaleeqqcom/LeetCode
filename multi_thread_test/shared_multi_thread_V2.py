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

def execute_in_interpreter(test_queue:interpreters.Queue, thread_id):
    """在子解释器中执行测试用例"""
    # 每个解释器独立创建Solution实例
    _solution = Solution()
    
    # 从队列中获取测试用例
    results = []
    start_time = time.time()
    
    while test_queue.empty() == False:
        try:
            # 阻塞等待获取测试用例，设置合理超时时间 (小于间隔)
            var = test_queue.get(timeout=0.0005)
            assert isinstance(var, tuple)
            case_id,num = var
            results.append((case_id,_solution.is_sqrt_prime(num)))
        except:
            # 队列为空，结束处理
            break
    
    elapsed = time.time() - start_time
    print(f"线程号：{thread_id} 执行{len(results)} 个用例耗时: {elapsed:.6f} s")
    
    return results

def main():
    # 生成测试用例
    test_cases = generate_test_cases(100)
    
    # 顺序执行测试（用于基准比较）
    start_time = time.time()
    solution = Solution()
    results_seq = [solution.is_sqrt_prime(num) for num in test_cases]
    seq_time = time.time() - start_time
    print(f"顺序执行耗时: {seq_time:.3f} s")
    
    # 创建跨解释器队列
    test_queue = interpreters.create_queue()

    # print(f"max_queue_size = {test_queue.maxsize}")
    
    # 并行执行测试
    start_time = time.time()

    # 将测试用例放入队列
    for case_id,num in enumerate(test_cases):
        test_queue.put((case_id,num))
    
    push_time = time.time() - start_time
    print(f"放入队列执行耗时: {push_time:.3f} s")

    print(f"test.qsize = {test_queue.qsize()}")
    
    # 创建解释器池
    with concurrent.futures.InterpreterPoolExecutor(max_workers=_N_CORE_) as executor:
        # 启动解释器子线程的并合并计算结果
        thread_buff = list(chain.from_iterable(
            executor.map(
                代入部分参数器(execute_in_interpreter , test_queue),
                range(_N_CORE_)
            )
        )) 
        # 后面需要以 cid 进行排序，确保结果顺序正确。如果可以的话，使用 python 自带的多队列归并排序（每个队列内部有序）可能效率更高

    print(f"thread_buff :\n{thread_buff}")

    # 以 cid 进行排序，确保结果顺序正确。
    thread_buff.sort(key = lambda id_res: id_res[0])

    results_parallel = [ res for _, res in thread_buff ]

    
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