import time
import random
import concurrent.futures

def generate_mid_changes(duration: int, interval: float) -> list:
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

def monitor_mid_changes(interval: float, max_duration: float, future: concurrent.futures.Future) -> list:
    """子线程监控mid变化"""
    changes = []
    start_time = time.time()
    
    # 从Future获取初始值
    time_stamp, value = future.result()
    changes.append((time_stamp, value))
    
    while time.time() - start_time < max_duration:
        time.sleep(interval)
        if future.done():
            time_stamp, value = future.result()
            # 记录变化，但不记录相同值
            if not changes or changes[-1][1] != value:
                changes.append((time_stamp, value))
    
    return changes

def test_shared_variable_protocol(n_interpreters: int = 4, duration: int = 10, interval: float = 0.5):
    """测试多GIL线程间共享变量通讯协议，使用Future进行跨解释器通信"""
    # 创建一个Future用于存储当前值
    current_value_future = concurrent.futures.Future()
    
    # 生成主线程的mid变化序列
    main_changes = generate_mid_changes(duration, interval)
    
    # 设置初始值
    current_value_future.set_result((0.0, main_changes[0][1]))
    
    # 创建子解释器
    with concurrent.futures.InterpreterPoolExecutor(max_workers=n_interpreters) as executor:
        # 为每个子线程提交任务，传入同一个Future
        futures = [
            executor.submit(monitor_mid_changes, interval, duration, current_value_future)
            for _ in range(n_interpreters)
        ]
        
        # 为每个子线程提供数据（更新Future）
        for time_stamp, value in main_changes[1:]:
            # 更新同一个Future，所有子线程都能看到
            current_value_future.set_result((time_stamp, value))
            
            # 等待一段时间，确保子线程有时间处理
            time.sleep(interval * 0.5)
        
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