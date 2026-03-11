import time
import random
import concurrent.futures
import concurrent.interpreters
from typing import List, Tuple

def monitor_mid_changes(shared_queue, interval, duration):
    """子线程监控mid变化（实时捕获变化）"""
    changes = []
    start_time = time.time()
    last_value = None
    
    while time.time() - start_time < duration:
        time.sleep(interval)
        try:
            # 从跨解释器队列中获取最新值
            time_stamp, value = shared_queue.get_nowait()
            # 记录变化（避免记录重复值）
            if value != last_value:
                changes.append((time_stamp, value))
                last_value = value
        except:
            # 队列为空，继续等待
            pass
    
    return changes

def test_shared_variable_protocol(n_interpreters: int = 4, duration: int = 10, interval: float = 0.5):
    """测试多GIL线程间共享变量通讯协议，使用InterpreterPoolExecutor和跨解释器队列"""
    # 创建跨解释器队列
    shared_queue = concurrent.interpreters.create_queue()
    
    # 主线程：实时生成mid变化并放入队列
    def generate_mid_changes():
        # 初始值
        initial_value = random.randint(1, 1000)
        shared_queue.put((0.0, initial_value))
        main_changes = [(0.0, initial_value)]
        
        current_value = initial_value
        start_time = time.time()
        
        while time.time() - start_time < duration:
            time.sleep(interval * 2)  # 确保变化间隔大于轮询间隔
            new_value = random.randint(1, 1000)
            while new_value == current_value:
                new_value = random.randint(1, 1000)
            
            current_value = new_value
            elapsed = time.time() - start_time
            shared_queue.put((elapsed, new_value))
            main_changes.append((elapsed, new_value))
        
        return main_changes
    
    # 启动子线程
    with concurrent.futures.InterpreterPoolExecutor(max_workers=n_interpreters) as executor:
        # 启动子线程
        futures = [executor.submit(monitor_mid_changes, shared_queue, interval, duration) 
                  for _ in range(n_interpreters)]
        
        # 主线程实时生成变化
        main_changes = generate_mid_changes()
        
        # 收集子线程的监测结果
        thread_changes = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    # 验证结果一致性：按时间戳归并后比较
    def merge_and_verify(changed_list):
        """按时间戳合并所有子线程的记录并验证"""
        # 合并所有记录
        all_changes = []
        for changes in changed_list:
            all_changes.extend(changes)
        
        # 按时间戳排序
        all_changes.sort(key=lambda x: x[0])
        
        # 从排序后的列表中提取值序列（去除重复值，因为时间戳递增，值变化才记录）
        merged_values = [v for t, v in all_changes]
        
        # 从主线程序列提取值序列（主线程序列也是按时间戳排序的）
        main_values = [v for t, v in main_changes]
        
        # 比较两个序列
        return merged_values == main_values
    
    consistent = merge_and_verify(thread_changes)
    
    # 输出结果
    print(f"测试共享变量协议: {n_interpreters}个解释器, {duration}s, 每 {interval}s 间隔")
    print(f"主线程变化次数: {len(main_changes)}")
    print(f"子线程变化次数: {sum(len(changes) for changes in thread_changes)}")
    print(f"结果一致性: {'✓' if consistent else '✗'}")
    
    return consistent, main_changes, thread_changes

if __name__ == "__main__":
    test_shared_variable_protocol(n_interpreters=4, duration=10, interval=0.5)