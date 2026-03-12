# V5 基于 V3.4 改进，使得能够适应早停机制
# 改进方法，早停队列存入错误的 cid，最后比较的时候截取最小 cid来搞。以确保结果一致性。

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
_TIMEOUT_ = 60 # 最大超时时间
# 用“等比递减分割器”分割测试用例，一个组合并用一个 group_id 标记即可
_GDQG_RATE_ = 1/_N_CORE_

# 测试用例生成
def generate_test_cases(n: int = 10000) -> List[int]:
    """生成 n 个随机 int32 正整数 (1 到 2^31-1)"""
    return [random.randint(1, (2**31) 
                           + (2**15)
                           ) for _ in range(n)]

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

        results_buff = []
        try:
            for num in cases:
                results_buff.append(_solution.is_sqrt_prime(num))
        except Exception as e:
            print(f"线程{interpreter_id}执行黑箱任务 gid={group_id} 出错，报错信息如下：\n{e}")
            early_stop_queue.put(group_id) # 将早停对应的 gid 存入共享队列

        results.append(( group_id,  results_buff ))

    end_time = time.time()
    elapsed = end_time - start_time
    print(f"解释器 {interpreter_id:2d} 处理 {sum([len(cases) for _,cases in results]):8d} 个用例耗时: {elapsed:10.6f} s , 结束时刻: {end_time:20.6f}s")
    
    return results

def merge_sorted_lists(lists,max_id = -1)->List[Any]:
    """使用归并排序合并多个已排序列表"""
    from heapq import merge
    
    # 归并排序
    merged = merge(*lists, key=lambda x: x[0])
    
    # 提取结果
    if -1 == max_id:
        return [result for case_id, result in merged]
    else:
        return [result for case_id, result in merged if case_id <= max_id]

def geometric_decreasing_queue_generator(test_cases: List[int],queue:interpreters.Queue , rate: float = 0.1):
    """将测试用例分割为若干个子列表，越往后子列表的大小呈等比递减，以便维持各线程基本同时收工"""
    group_id,case_id = 0,0
    # 将剩余的用例按 rate 递减加入到 queue 中，至少要有 1 个用例
    while case_id < len(test_cases):
        chunk_size = max(1, int((len(test_cases)-case_id) * rate))
        queue.put((group_id, test_cases[case_id:case_id+chunk_size]))
        case_id += chunk_size
        group_id += 1
    
def main():
    # 生成测试用例
    test_cases = generate_test_cases(100000)
    
    # 顺序执行测试（用于基准比较）
    start_time = time.time()
    solution = Solution()
    results_seq = []
    try:
        for num in test_cases:
            results_seq.append(solution.is_sqrt_prime(num))
    except Exception as e:
        print(f"顺序执行黑箱任务出错，报错信息如下：\n{e}")
    seq_time = time.time() - start_time
    print(f"顺序执行耗时: {seq_time:.3f} s")
    
    # 并行执行测试
    start_time = time.time()
    
    # 创建解释器池
    with concurrent.futures.InterpreterPoolExecutor(max_workers=_N_CORE_) as executor:
        # 早停广播队列
        early_stop_queue = interpreters.create_queue()
        
        # 创建跨解释器队列
        test_queue = interpreters.create_queue()

        # 使用 partial 固定 test_queue 参数
        func = partial(execute_in_interpreter, test_queue=test_queue,early_stop_queue=early_stop_queue)
        # 收集结果（现在只需传入 interpreter_id 列表）
        results_parallel = executor.map(func, range(_N_CORE_),timeout=_TIMEOUT_)
        
        geometric_decreasing_queue_generator(test_cases,test_queue,rate=_GDQG_RATE_)
        print(f"geom_rate = {_GDQG_RATE_}, case group num = {test_queue.qsize()}")

        # 先确保收集全部结果，再处理 early_stop_queue
        results_parallel = list(results_parallel)
        
        # 阻塞等待 early_stop_queue 的所有线程的停止信号
        early_stop_gid = []
        while not early_stop_queue.empty():
            value = early_stop_queue.get(timeout=_TIMEOUT_)
            if isinstance(value,int):
                early_stop_gid.append(value)

    print(f"early_stop_gid={early_stop_gid}")

    # 使用归并排序合并结果
    results_parallel = list(
        chain.from_iterable(merge_sorted_lists(
        results_parallel,
        max_id= min(early_stop_gid) if early_stop_gid else -1
        ))
    )
    
    parallel_time = time.time() - start_time
    print(f"\n{_N_CORE_} 解释器并行耗时: {parallel_time:.3f} s")
    
    # 验证结果一致性
    print(f"num-seq = {len(results_seq)} , num-para = {len(results_parallel)}")
    consistent = all(r1 == r2 for r1, r2 in zip(results_seq, results_parallel))
    print(f"结果一致性: {'✓' if consistent else '✗'}")
    
    # 计算加速比
    speedup = seq_time / parallel_time
    print(f"加速比: {speedup:.2f}x (目标: ~{_N_CORE_}x)")

if __name__ == '__main__':
    main()