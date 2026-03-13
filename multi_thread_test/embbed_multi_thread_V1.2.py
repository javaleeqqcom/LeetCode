# embbed_multi_thread_V1.2.py
# 修复：__builtins__ 访问问题

import math
import random
import time
import concurrent.futures
from concurrent import interpreters
from typing import List, Tuple, Any, Callable
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


# ========== 全局单线程函数生成器 ==========
def create_black_box_executor(
    solution_a_code: str,
    solution_b_code: str,
    method_name: str,
) -> Callable:
    """
    创建黑箱执行器（使用 __import__ 确保可 shareable）
    
    参数:
        solution_a_code: Solution5_A.py 代码字符串
        solution_b_code: Solution5_B.py 代码字符串
        method_name: 要调用的方法名（如 "is_sqrt_prime"）
    
    返回:
        callable 对象，支持 black_box(*args, **kwargs) 调用
    """
    # ========== 使用 __import__ 导入模块（可 shareable） ==========
    _types = __import__('types')
    _math = __import__('math')
    _bisect = __import__('bisect')
    _typing = __import__('typing')
    
    # 创建学生代码模块
    student_mod = _types.ModuleType('student_solution')
    student_mod.__dict__.update({
        '__builtins__': __builtins__,
        'math': _math,
        'bisect': _bisect,
        'List': _typing.List,
        'Optional': _typing.Optional,
        'Tuple': _typing.Tuple,
    })
    
    # ========== 修复：直接使用 exec，不通过 __builtins__ 访问 ==========
    exec(solution_a_code, student_mod.__dict__)
    exec(solution_b_code, student_mod.__dict__)
    
    # 获取 Solution 类和方法
    Solution = student_mod.__dict__['Solution']
    _solution = Solution()
    _method = getattr(_solution, method_name)
    
    # 返回 callable
    def black_box(*args, **kwargs):
        return _method(*args, **kwargs)
    
    return black_box


def generate_test_cases(n: int = 10000) -> List[int]:
    """生成 n 个随机 int32 正整数 (1 到 2^31-1)"""
    return [random.randint(1, (2**31) - 1) for _ in range(n)]


def execute_in_interpreter(
    interpreter_id: int,
    test_queue_id: int,
    early_stop_queue_id: int,
    solution_a_code: str,
    solution_b_code: str,
    method_name: str,
) -> List[Tuple[int, Any]]:
    """
    在子解释器中执行测试用例
    所有参数必须是可共享的基本类型（int, str）
    """
    # ========== 使用 __import__ 导入模块（可 shareable） ==========
    _time = __import__('time')
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

    # ========== 调用全局单线程函数生成器的逻辑 ==========
    student_mod = _types.ModuleType('student_solution')
    student_mod.__dict__.update({
        '__builtins__': __builtins__,
        'math': _math,
        'bisect': _bisect,
        'List': _typing.List,
        'Optional': _typing.Optional,
        'Tuple': _typing.Tuple,
    })
    
    # ========== 修复：直接使用 exec ==========
    exec(solution_a_code, student_mod.__dict__)
    exec(solution_b_code, student_mod.__dict__)
    
    Solution = student_mod.__dict__['Solution']
    _solution = Solution()
    _method = getattr(_solution, method_name)
    
    print(f"解释器 {interpreter_id}: 成功创建 Solution 实例和方法 '{method_name}'")

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
                # ========== 统一调用方式：_method(*args, **kwargs) ==========
                results_buff.append(_method(num))
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


def run_single_thread(
    test_cases: List[int],
    solution_a_code: str,
    solution_b_code: str,
    method_name: str,
) -> List[Any]:
    """
    单线程执行（使用全局单线程函数生成器）
    """
    # ========== 调用全局单线程函数生成器 ==========
    black_box = create_black_box_executor(
        solution_a_code=solution_a_code,
        solution_b_code=solution_b_code,
        method_name=method_name,
    )
    
    results = []
    try:
        for case in test_cases:
            results.append(black_box(case))
    except Exception as e:
        print(f"顺序执行黑箱任务出错，报错信息如下：\n{e}")
    
    return results


def run_multi_thread(
    test_cases: List[int],
    solution_a_code: str,
    solution_b_code: str,
    method_name: str,
    n_core: int = 12,
    timeout_s: int = 60,
    gdqg_rate: float = None,
) -> List[Any]:
    """
    多线程执行（使用全局单线程函数生成器的逻辑）
    """
    if gdqg_rate is None:
        gdqg_rate = 1 / n_core
    
    # 创建跨解释器队列
    test_queue = interpreters.create_queue()
    early_stop_queue = interpreters.create_queue()

    # 用"等比递减分割器"分割测试用例
    geometric_decreasing_queue_generator(test_cases, test_queue, rate=gdqg_rate)
    print(f"geom_rate = {gdqg_rate}, case group num = {test_queue.qsize()}")
    
    # 创建解释器池
    with concurrent.futures.InterpreterPoolExecutor(max_workers=n_core) as executor:
        func = partial(
            execute_in_interpreter,
            test_queue_id=test_queue.id,
            early_stop_queue_id=early_stop_queue.id,
            solution_a_code=solution_a_code,
            solution_b_code=solution_b_code,
            method_name=method_name,
        )
        
        results_parallel = list(executor.map(func, range(n_core), timeout=timeout_s))
        
        early_stop_gid = []
        while not early_stop_queue.empty():
            value = early_stop_queue.get(timeout=timeout_s)
            if isinstance(value, int):
                early_stop_gid.append(value)

    print(f"early_stop_gid={early_stop_gid}")

    results_parallel = list(
        chain.from_iterable(merge_sorted_lists(
            results_parallel,
            max_id=min(early_stop_gid) if early_stop_gid else -1
        ))
    )
    
    return results_parallel


def main():
    # 生成测试用例
    test_cases = generate_test_cases(1000000)
    
    # ========== 方法名作为参数传入 ==========
    METHOD_NAME = "is_sqrt_prime"
    
    # ========== 单线程执行（使用全局单线程函数生成器） ==========
    start_time = time.time()
    results_seq = run_single_thread(
        test_cases=test_cases,
        solution_a_code=_SOLUTION_A_CODE,
        solution_b_code=_SOLUTION_B_CODE,
        method_name=METHOD_NAME,
    )
    seq_time = time.time() - start_time
    print(f"顺序执行耗时: {seq_time:.3f} s, 返回结果数量：{len(results_seq)}")
    
    # ========== 多线程执行（使用全局单线程函数生成器的逻辑） ==========
    start_time = time.time()
    results_parallel = run_multi_thread(
        test_cases=test_cases,
        solution_a_code=_SOLUTION_A_CODE,
        solution_b_code=_SOLUTION_B_CODE,
        method_name=METHOD_NAME,
        n_core=_N_CORE_,
        timeout_s=_TIMEOUT_,
        gdqg_rate=_GDQG_RATE_,
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