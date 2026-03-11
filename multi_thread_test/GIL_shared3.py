import time
import random
from concurrent import interpreters

def run_subinterpreter(id, t0, mailbox, result_queue, stop_event):
    """子解释器执行逻辑"""
    last_mid = None
    recorded_mids = []
    
    while not stop_event.empty() == False: # 模拟停止信号
        try:
            # 轮询最新的 mid (不移除，只读取最新)
            # 注意：标准 Queue.get() 会移除元素，这里我们假设 mailbox 只存最新的 mid
            current_mid = mailbox.peek() 
            if current_mid != last_mid:
                recorded_mids.append(current_mid)
                last_mid = current_mid
        except Exception:
            pass
        
        time.sleep(t0)
    
    # 任务结束，将记录推入结果队列
    result_queue.put(recorded_mids)

def main():
    t0 = 0.1
    num_subs = 3
    change_count = 5
    
    # 1. 基础设施：信箱(存mid)、结果队列、停止信号
    mailbox = interpreters.Queue(maxsize=1) # 覆盖式信箱
    result_queues = [interpreters.Queue() for _ in range(num_subs)]
    stop_signal = interpreters.Queue()
    
    # 2. 启动子解释器
    interps = []
    for i in range(num_subs):
        interp = interpreters.create()
        # 注入共享对象
        interp.prepare_main({
            "mailbox": mailbox,
            "res_q": result_queues[i],
            "stop_sig": stop_signal,
            "t0": t0
        })
        # 执行轮询脚本
        interp.exec("""
import time
last_mid = None
history = []
while stop_sig.empty():
    try:
        # 获取当前 mid (此处逻辑：主线程put，子线程get后马上put回去以模拟peek)
        mid = mailbox.get()
        mailbox.put(mid) 
        if mid != last_mid:
            history.append(mid)
            last_mid = mid
    except: pass
    time.sleep(t0)
res_q.put(history)
        """)
        interps.append(interp)

    # 3. 主线程控制 mid 变化
    main_history = []
    current_mid = -1
    
    print("开始生产 mid...")
    for _ in range(change_count):
        # 确保 mid 不与上次相等
        new_mid = random.randint(1, 100)
        while new_mid == current_mid:
            new_mid = random.randint(1, 100)
        
        current_mid = new_mid
        main_history.append(current_mid)
        
        # 更新信箱 (先清空旧的，放入新的)
        if not mailbox.empty(): mailbox.get()
        mailbox.put(current_mid)
        
        time.sleep(2 * t0)

    # 4. 停止并收集
    stop_signal.put(True)
    print(f"主线程序列: {main_history}")
    
    for i, q in enumerate(result_queues):
        sub_history = q.get()
        print(f"子解释器 {i} 序列: {sub_history}")
        assert sub_history == main_history, f"子解释器 {i} 数据不一致！"

    print("✅ 所有序列校验成功！")

if __name__ == "__main__":
    main()
