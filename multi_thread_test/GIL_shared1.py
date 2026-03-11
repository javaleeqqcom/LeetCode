import time
import random
import concurrent.futures
from queue import Queue
from typing import List, Tuple

def generate_mid_changes(duration: int, interval: float) -> List[Tuple[float, int]]:
    """主线程生成mid变化序列"""
    changes = []
    start_time = time.time()
    
    current_value = random.randint(1, 1000)
    changes.append((0.0, current_value))
    
    while time.time() - start_time < duration:
        time.sleep(interval * 2)
        new_value = random.randint(1, 1000)
        while new_value == current_value:
            new_value = random.randint(1, 1000)
        
        current_value = new_value
        changes.append((time.time() - start_time, current_value))
    
    return changes

def monitor_mid_changes(shared_queue: Queue, interval: float, max_duration: float) -> List[Tuple[float, int]]:
    """子线程监控mid变化"""
    changes = []
    start_time = time.time()
    
    while time.time() - start_time < max_duration:
        time.sleep(interval)
        try:
            # 从队列中获取最新值
            time_stamp, value = shared_queue.get_nowait()
            # 记录变化，但不记录相同值
            if not changes or changes[-1][1] != value:
                changes.append((time_stamp, value))
        except:
            # 队列为空，继续等待
            pass
    
    return changes

def test_shared_variable_protocol(n_interpreters: int = 4, duration: int = 10, interval: float = 0.5):
    """测试多GIL线程间共享变量通讯协议，使用InterpreterPoolExecutor和Queue"""
    # 创建队列用于解释器间通信
    shared_queue = Queue()
    
    # 生成主线程的mid变化序列
    main_changes = generate_mid_changes(duration, interval)
    
    # 将主线程的初始值放入队列
    shared_queue.put((0.0, main_changes[0][1]))
    
    # 创建子解释器
    with concurrent.futures.InterpreterPoolExecutor(max_workers=n_interpreters) as executor:
        futures = [executor.submit(monitor_mid_changes, shared_queue, interval, duration) 
                  for _ in range(n_interpreters)]
        
        # 为每个子线程提供数据
        for time_stamp, value in main_changes[1:]:
            shared_queue.put((time_stamp, value))
        
        # 收集子线程的监测结果
        thread_changes = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    # 验证结果一致性
    consistent = True
    for i, thread_change in enumerate(thread_changes):
        # 检查子线程记录的序列是否与主线程一致
        for time_stamp, value in thread_change:
            if not any(t == time_stamp and v == value for t, v in main_changes):
                consistent = False
                print(f"解释器 {i} 有不一致: {time_stamp:.2f}s, {value}")
    
    # 输出结果
    print(f"测试共享变量协议: {n_interpreters}个解释器, {duration}s, 每 {interval}s 间隔")
    print(f"主线程变化次数: {len(main_changes)}")
    print(f"子线程变化次数: {sum(len(changes) for changes in thread_changes)}")
    print(f"结果一致性: {'✓' if consistent else '✗'}")
    
    return consistent, main_changes, thread_changes

if __name__ == "__main__":
    # 测试协议
    test_shared_variable_protocol(n_interpreters=4, duration=10, interval=0.5)