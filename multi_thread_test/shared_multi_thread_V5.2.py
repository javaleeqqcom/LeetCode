# V5 基于 V3.4 改进，使得能够适应早停机制
"""
(py314) PS D:\Users\java_lee\Documents\GitHub\LeetCode> & C:\Users\john\anaconda3\envs\py314\python.exe d:/Users/java_lee/Documents/GitHub/LeetCode/multi_thread_test/shared_multi_thread_V5.2.py
顺序执行黑箱任务出错，报错信息如下：
num 必须是 int32 非负整数
顺序执行耗时: 0.050 s
geom_rate / first_rate = 0.4 / 0.8, case group num = 250
线程3执行黑箱任务出错，报错信息如下：
num 必须是 int32 非负整数

解释器 3 处理 0 个用例耗时: 0.019452 s
线程0执行黑箱任务出错，报错信息如下：
num 必须是 int32 非负整数

解释器 0 处理 0 个用例耗时: 0.074820 s
解释器 6 处理 6666 个用例耗时: 0.072891 s
解释器 8 处理 6666 个用例耗时: 0.075288 s
解释器 10 处理 6666 个用例耗时: 0.069845 s
线程1执行黑箱任务出错，报错信息如下：
num 必须是 int32 非负整数

解释器 1 处理 0 个用例耗时: 0.078277 s
解释器 2 处理 6666 个用例耗时: 0.079004 s
解释器 9 处理 6666 个用例耗时: 0.081178 s
解释器 7 处理 6666 个用例耗时: 0.085646 s
解释器 4 处理 6666 个用例耗时: 0.086661 s
解释器 11 处理 6666 个用例耗时: 0.087191 s
解释器 5 处理 6666 个用例耗时: 0.091758 s

12 解释器并行耗时: 0.182 s
结果一致性: ✗
加速比: 0.27x (目标: ~12x)
"""
import math
import random
import time
import concurrent.futures
from concurrent import interpreters
from typing import List, Tuple, Any
from Solution4 import Solution
from itertools import chain
from functools import partial  # 固定 test_queue 参数之用于多线程调用

_N_CORE_ = 12
_N_THREAD_ = 100

# 测试用例生成
def generate_test_cases(n: int = 10000) -> List[int]:
    """生成 n 个随机 int32 正整数 (1 到 2^31-1)"""
    return [random.randint(1, (2**31) + (2**15)) for _ in range(n)]

def execute_in_interpreter(interpreter_id : int , test_queue :interpreters.Queue , early_stop_queue : interpreters.Queue)->List[Tuple[int,Any]]:
    """在子解释器中执行测试用例"""
    start_time = time.time()

    # 每个解释器独立创建Solution实例
    _solution = Solution()
    
    # 从队列中获取测试用例
    results = []
    
    while early_stop_queue.empty():
        try:
            # 阻塞等待获取测试用例
            group_id, cases = test_queue.get_nowait()
        except:
            # 队列为空，结束处理
            break
        try:
            results.append((
                group_id, 
                [_solution.is_sqrt_prime(num) for num in cases] # 第 group_id 组样例分块连续处理
                ))
        except Exception as e:
            early_stop_queue.put(interpreter_id) # 暂时用 id 表示早停
            print(f"线程{interpreter_id}执行黑箱任务出错，报错信息如下：\n{e}\n")
            break

    elapsed = time.time() - start_time
    print(f"解释器 {interpreter_id} 处理 {sum([len(cases) for _,cases in results])} 个用例耗时: {elapsed:.6f} s")
    
    return results

def merge_sorted_lists(lists)->List[Any]:
    """使用归并排序合并多个已排序列表"""
    from heapq import merge
    
    # 归并排序
    merged = merge(*lists, key=lambda x: x[0])
    
    # 提取结果
    return [result for case_id, result in merged]

def geometric_decreasing_queue_generator(test_cases: List[int],queue:interpreters.Queue , rate: float = 0.5, first_rate = 0.9 , n_core: int = _N_CORE_) -> bool:
    """将测试用例分割为若干个子列表，越往后子列表的大小呈等比递减，以便维持各线程基本同时收工"""
    assert 0 < rate < 1 and 0 < first_rate <1, "rate,first_rate 必须在 0 和 1 之间"
    assert n_core >= 1, "n_core 必须大于等于 1"

    n_core = min(n_core,len(test_cases)) # 若 test_cases 不够 ncore 分，则减少 ncore。
    group_id,case_id = 0,0
    # 首先，将前 first_rate 的用例按 n_core 平分
    chunk_size = max(1,int(len(test_cases) * first_rate / n_core) )
    if chunk_size > 0:
        # 为当前块中的每个测试用例分配唯一ID
        for group_id in range(n_core):
            queue.put((group_id, test_cases[case_id:case_id+chunk_size]))
            case_id += chunk_size

        group_id = n_core
    
    # 然后，将剩余的用例按 rate/n_core 递减加入到 queue 中，至少要有 1 个用例
    while case_id < len(test_cases):
        chunk_size = max(1, int((len(test_cases)-case_id) * rate/ n_core))
        queue.put((group_id, test_cases[case_id:case_id+chunk_size]))
        case_id += chunk_size
        group_id += 1
    
    # 检查队列数量和 group_id 计数是否一致
    return queue.qsize() == group_id

def main():
    # 生成测试用例
    test_cases = generate_test_cases(100000)
    
    # 顺序执行测试（用于基准比较）
    start_time = time.time()
    solution = Solution()
    results_seq = []
    for num in test_cases:
        try:
            results_seq.append(solution.is_sqrt_prime(num))
        except Exception as e:
            print(f"顺序执行黑箱任务出错，报错信息如下：\n{e}")
            break
    seq_time = time.time() - start_time
    print(f"顺序执行耗时: {seq_time:.3f} s")
    
    # 并行执行测试
    start_time = time.time()
    
    # 创建跨解释器队列
    test_queue = interpreters.create_queue()

    # 早停广播队列
    early_stop_queue = interpreters.create_queue()

    # 用“等比递减分割器”分割测试用例，一个组合并用一个 group_id 标记即可
    rate,first_rate = 0.4,0.8
    assert geometric_decreasing_queue_generator(test_cases,test_queue,rate=rate,first_rate=first_rate) == True, "分割器生成失败"
    print(f"geom_rate / first_rate = {rate} / {first_rate}, case group num = {test_queue.qsize()}")
    
    # 创建解释器池
    with concurrent.futures.InterpreterPoolExecutor(max_workers=_N_CORE_) as executor:
        # 使用 partial 固定 test_queue 参数
        func = partial(execute_in_interpreter, test_queue=test_queue,early_stop_queue=early_stop_queue)
        # 收集结果（现在只需传入 interpreter_id 列表）
        results_parallel = executor.map(func, range(_N_CORE_))
    
    # 使用归并排序合并结果
    results_parallel = chain.from_iterable(merge_sorted_lists(results_parallel))
    
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