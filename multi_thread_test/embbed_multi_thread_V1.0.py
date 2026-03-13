# embbed_multi_thread_V1.py - 修复版本
# 核心改进：使用 __import__() 替代 import 语句，避免子解释器中的变量绑定问题

import math
import random
import time
import concurrent.futures
from concurrent import interpreters
from typing import List, Tuple, Any
from pathlib import Path
from itertools import chain
from functools import partial

_N_CORE_ = 12
_TIMEOUT_ = 60
_GDQG_RATE_ = 1/_N_CORE_

# ========== 读取学生代码文件内容为字符串 ==========
_CURRENT_DIR = Path(__file__).resolve().parent
_SOLUTION_A_PATH = _CURRENT_DIR / "Solution5_A.py"
_SOLUTION_B_PATH = _CURRENT_DIR / "Solution5_B.py"

with open(_SOLUTION_A_PATH, 'r', encoding='utf-8') as f:
    _SOLUTION_A_CODE = f.read()

with open(_SOLUTION_B_PATH, 'r', encoding='utf-8') as f:
    _SOLUTION_B_CODE = f.read()

def generate_test_cases(n: int = 10000) -> List[int]:
    """生成 n 个随机 int32 正整数 (1 到 2^31-1)"""
    return [random.randint(1, (2**31) - 1) for _ in range(n)]

def execute_in_interpreter(
    interpreter_id: int,
    test_queue_id: int,
    early_stop_queue_id: int,
    solution_a_code: str,
    solution_b_code: str,
) -> List[Tuple[int, Any]]:
    """
    在子解释器中执行测试用例
    所有参数必须是可共享的基本类型（int, str）
    
    ⚠️ 关键：使用 __import__() 替代 import 语句，避免子解释器中的变量绑定问题
    """
    # ========== 关键修复：使用 __import__() 替代 import 语句 ==========
    _time = __import__('time')
    _sys = __import__('sys')
    _types = __import__('types')
    _math = __import__('math')
    _bisect = __import__('bisect')
    _typing = __import__('typing')
    _concurrent = __import__('concurrent')
    _interpreters = _concurrent.interpreters
    
    start_time = _time.time()

    # ========== 通过 ID 重建队列对象 ==========
    test_queue = _interpreters.Queue(test_queue_id)
    early_stop_queue = _interpreters.Queue(early_stop_queue_id)
    print(f"解释器 {interpreter_id}: 队列重建成功")

    # ========== 在子解释器中执行学生代码 ==========
    student_mod = _types.ModuleType('student_solution')
    student_mod.__dict__.update({
        '__builtins__': __builtins__,
        'math': _math,
        'bisect': _bisect,
        'List': _typing.List,
        'Optional': _typing.Optional,
        'Tuple': _typing.Tuple,
    })

    # 先执行 Solution5_A.py（定义 _prime）
    _exec_code = __builtins__['exec']
    _exec_code(solution_a_code, student_mod.__dict__)
    # 再执行 Solution5_B.py（定义 Solution 类，依赖 _prime）
    _exec_code(solution_b_code, student_mod.__dict__)

    # 从模块中获取 Solution 类
    Solution = student_mod.__dict__['Solution']
    _solution = Solution()
    
    print(f"解释器 {interpreter_id}: 成功创建 Solution 实例")

    # 从队列中获取测试用例
    results = []
    
    while early_stop_queue.empty():
        try:
            group_id, cases = test_queue.get_nowait()
        except _interpreters.QueueEmpty:
            if test_queue.empty():
                break
            _time.sleep(0.001)
            continue

        results_buff = []
        try:
            for num in cases:
                results_buff.append(_solution.is_sqrt_prime(num))
        except Exception as e:
            print(f"线程{interpreter_id}执行黑箱任务 gid={group_id} 出错，报错信息如下：\n{e}")
            early_stop_queue.put(group_id)

        results.append((group_id, results_buff))

    end_time = _time.time()
    elapsed = end_time - start_time
    print(f"解释器 {interpreter_id:2d} 处理 {sum([len(cases) for _,cases in results]):8d} 个用例耗时: {elapsed:10.6f} s , 结束时刻: {end_time:20.6f}s")
    
    return results

def merge_sorted_lists(lists, max_id=-1) -> List[Any]:
    """使用归并排序合并多个已排序列表"""
    from heapq import merge
    
    merged = merge(*lists, key=lambda x: x[0])
    
    if -1 == max_id:
        return [result for case_id, result in merged]
    else:
        return [result for case_id, result in merged if case_id <= max_id]

def geometric_decreasing_queue_generator(test_cases: List[int], queue: interpreters.Queue, rate: float = 0.1, min_chunk=1):
    """将测试用例分割为若干个子列表，越往后子列表的大小呈等比递减"""
    group_id, case_id = 0, 0
    while case_id < len(test_cases):
        chunk_size = max(1, int((len(test_cases)-case_id) * rate))
        queue.put((group_id, test_cases[case_id:case_id+chunk_size]))
        case_id += chunk_size
        group_id += 1
    
def main():
    # 生成测试用例
    test_cases = generate_test_cases(1000000)
    
    # 顺序执行测试（用于基准比较）
    start_time = time.time()
    
    import types
    import math
    import bisect
    from typing import List, Optional, Tuple
    
    student_mod = types.ModuleType('student_solution')
    student_mod.__dict__.update({
        '__builtins__': __builtins__,
        'math': math,
        'bisect': bisect,
        'List': List,
        'Optional': Optional,
        'Tuple': Tuple,
    })
    exec(_SOLUTION_A_CODE, student_mod.__dict__)
    exec(_SOLUTION_B_CODE, student_mod.__dict__)
    Solution = student_mod.__dict__['Solution']
    
    solution = Solution()
    results_seq = []
    try:
        for num in test_cases:
            results_seq.append(solution.is_sqrt_prime(num))
    except Exception as e:
        print(f"顺序执行黑箱任务出错，报错信息如下：\n{e}")
    seq_time = time.time() - start_time
    print(f"顺序执行耗时: {seq_time:.3f} s, 返回结果数量：{len(results_seq)}")
    
    # 并行执行测试
    start_time = time.time()
    
    # 创建跨解释器队列
    test_queue = interpreters.create_queue()
    early_stop_queue = interpreters.create_queue()

    # 用"等比递减分割器"分割测试用例
    geometric_decreasing_queue_generator(test_cases, test_queue, rate=_GDQG_RATE_)
    print(f"geom_rate = {_GDQG_RATE_}, case group num = {test_queue.qsize()}")
    
    # 创建解释器池
    with concurrent.futures.InterpreterPoolExecutor(max_workers=_N_CORE_) as executor:
        func = partial(
            execute_in_interpreter,
            test_queue_id=test_queue.id,
            early_stop_queue_id=early_stop_queue.id,
            solution_a_code=_SOLUTION_A_CODE,
            solution_b_code=_SOLUTION_B_CODE,
        )
        
        results_parallel = list(executor.map(func, range(_N_CORE_), timeout=_TIMEOUT_))
        
        early_stop_gid = []
        while not early_stop_queue.empty():
            value = early_stop_queue.get(timeout=_TIMEOUT_)
            if isinstance(value, int):
                early_stop_gid.append(value)

    print(f"early_stop_gid={early_stop_gid}")

    results_parallel = list(
        chain.from_iterable(merge_sorted_lists(
            results_parallel,
            max_id=min(early_stop_gid) if early_stop_gid else -1
        ))
    )
    
    parallel_time = time.time() - start_time
    print(f"\n{_N_CORE_} 解释器并行耗时: {parallel_time:.3f} s")
    
    print(f"num-seq = {len(results_seq)} , num-para = {len(results_parallel)}")
    consistent = all(r1 == r2 for r1, r2 in zip(results_seq, results_parallel))
    print(f"结果一致性: {'✓' if consistent else '✗'}")
    
    speedup = seq_time / parallel_time
    print(f"加速比: {speedup:.2f}x (目标: ~{_N_CORE_}x)")

if __name__ == '__main__':
    main()