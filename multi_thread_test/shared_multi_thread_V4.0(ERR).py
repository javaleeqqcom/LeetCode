# V4 基于 V3.2 改进，使得能够适应早停机制
import math
import random
import time
import concurrent.futures
from concurrent import interpreters
from typing import List, Tuple, Any
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
    
    # 从队列中获取测试用例
    start_time = time.time()
    
    # 每个解释器独立创建Solution实例
    _solution = Solution()
    process_case_num = 0

    while True:
        try:
            # 阻塞等待获取测试用例，设置合理超时时间 (小于间隔)
            group_id, cases = test_queue.get(timeout=0.0005)
        except:
            # 队列为空，结束处理
            break

        try:
            results_queue.put((
                group_id, 
                [_solution.is_sqrt_prime(num) for num in cases] # 第 group_id 组样例分块连续处理
                ))
            process_case_num+=len(cases)
        except:
            results_queue.put((None,None)) # 执行黑箱任务出错，插入 None 以表示任务出错
            print(f"线程{interpreter_id}执行黑箱任务出错，提前跳出。")
            break
    
    elapsed = time.time() - start_time
    print(f"解释器 {interpreter_id} 处理 {process_case_num} 个用例耗时: {elapsed:.6f} s")
    
def geometric_decreasing_queue_generator(test_cases: List[int],queue:interpreters.Queue , rate: float = 0.5, n_core: int = _N_CORE_) -> bool:
    """将测试用例分割为若干个子列表，越往后子列表的大小呈等比递减，以便维持各线程基本同时收工"""
    n_core = min(n_core,len(test_cases)) # 若 test_cases 不够 ncore 分，则减少 ncore。
    group_id,case_id = 0,0
    # 首先，将前 90% 的用例按 n_core 平分
    chunk_size = max(1,int(len(test_cases) * rate / n_core) )
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
    test_cases = generate_test_cases(100)
    
    # 顺序执行测试（用于基准比较）
    start_time = time.time()
    solution = Solution()
    results_seq = [solution.is_sqrt_prime(num) for num in test_cases]
    seq_time = time.time() - start_time
    print(f"顺序执行耗时: {seq_time:.3f} s")
    
    # 并行执行测试
    start_time = time.time()
    
    # 创建跨解释器队列
    test_queue = interpreters.create_queue()
    results_queue = interpreters.create_queue()
    
    # 创建解释器池
    with concurrent.futures.InterpreterPoolExecutor(max_workers=_N_CORE_) as executor:
        # 启动解释器任务
        for i in range(_N_CORE_):
            executor.submit(execute_in_interpreter, test_queue, results_queue, i)
        
        # 用“等比递减分割器”分割测试用例，一个组合并用一个 group_id 标记即可
        gdqg_rate = 0.5
        assert geometric_decreasing_queue_generator(test_cases,test_queue,rate=gdqg_rate) == True, "分割器生成失败"
        print(f"geom_rate = {gdqg_rate}, case group num = {test_queue.qsize()}")
        
        # 放入结束标记（每个解释器一个）
        for _ in range(_N_CORE_):
            test_queue.put((None, None))
        
        # 收集结果
        results_parallel = []
        while not results_queue.empty():
            cur = results_queue.get()
            if cur[0] is not None:
                results_parallel.append(cur)

        for _ in range(_N_CORE_):
            results_parallel.append(results_queue.get())
    
    print(results_parallel)

    # 使用排序确保结果有序
    results_parallel = chain.from_iterable(sorted(results_parallel,key=lambda id_var:id_var[0]))
    
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