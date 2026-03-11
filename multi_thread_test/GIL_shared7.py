import time
import random
import concurrent.futures
import concurrent.interpreters
from typing import List, Tuple

def consumers(shared_queue : concurrent.interpreters.Queue, interval, duration):
    """子线程监控mid变化（实时捕获变化）"""
    buff = []
    start_time = time.time()
    
    while time.time() - start_time < duration:
        if not shared_queue.empty():
            try: # 多线程安全，即便判断不为空，也可能获取失败
                # 从跨解释器队列中获取最新值
                value = shared_queue.get(timeout=interval*2)
                now_time = time.time()

                buff.append((now_time, value))
            except:
                pass
    
    return buff

def test_shared_variable_protocol(n_interpreters: int = 4, duration: int = 10, interval: float = 0.5):
    """测试多GIL线程间共享变量通讯协议，使用InterpreterPoolExecutor和跨解释器队列"""
    # 创建跨解释器队列
    shared_queue = concurrent.interpreters.create_queue()
    
    # 主线程：实时生成mid变化并放入队列
    def producers():
        buff = []
        start_time = time.time()
        while time.time() - start_time < duration:
            time.sleep(interval)  # 确保生产间隔大于轮询间隔

            # 生产随机数
            new_value = random.randint(1, 1000)

            # 不采用时间戳，直接放入队列
            shared_queue.put(new_value)

            now_time = time.time()

            # 作为正确答案进行记录（时间戳仅用于调试分析是否为真并发）
            buff.append((now_time,new_value))
        
        return buff
    
    # 启动子线程
    with concurrent.futures.InterpreterPoolExecutor(max_workers=n_interpreters) as executor:
        # 启动子线程
        futures = [executor.submit(consumers, shared_queue, interval, duration) 
                  for _ in range(n_interpreters)]
        
        # 主线程实时生产
        main_buff = producers()
        
        # 收集子线程的监测结果
        thread_buff = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    # 验证结果一致性：按时间戳归并后比较
    def merge(buff_list):
        """按时间戳合并所有子线程的记录并验证"""
        # 合并所有记录
        all_changes = []
        for changes in buff_list:
            all_changes.extend(changes)
        
        # 按时间戳排序
        all_changes.sort(key=lambda x: x[0])
        
        # 从排序后的列表中提取值序列（去除重复值，因为时间戳递增，值变化才记录）
        merged_values = [v for t, v in all_changes]
        
        return merged_values
    
    main_list = merge([main_buff])
    thread_list = merge(thread_buff)

    consistent = len(main_list) == len(thread_list) and all(v0==v1 for v0,v1 in zip(main_list,thread_list))
    
    # 输出结果
    print(f"测试共享变量协议: {n_interpreters}个解释器, {duration}s, 每 {interval}s 间隔")
    print(f"主线程变化次数: {len(main_list)}")
    print(f"子线程变化次数: {len(thread_list)}")
    print(f"结果一致性: {'✓' if consistent else '✗'}")
    
    return consistent, main_buff, thread_buff

if __name__ == "__main__":
    test_shared_variable_protocol(n_interpreters=4, duration=10, interval=0.001)