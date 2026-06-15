from tools.AIConsultation import AIConsultation as AIC

README = AIC(r"README.md")

debug_retriever = AIC(r"rag\debug_retriever.py")
RAG_DEBUG = AIC(r"RAG_DEBUG.txt")
embedding = AIC(r"rag\embedding.py")
retriever=AIC(r"rag\retriever.py")
index_builder = AIC(r"rag\index_builder.py")
RAG_DOC = AIC(r"rag\RAG_DOC.md")

AGENTS_DOC = AIC(r"agents\AGENTS_DOC.md")
agent_io = AIC(r"agents\agent_io.py")
analyze_agent = AIC(r"agents\analyze_agent.py")
build_graph = AIC(r"agents\build_graph.py")
case_generator_agent = AIC("agents\case_generator_agent.py")
graph_state = AIC(r"agents\graph_state.py")

solution_runner = AIC(r"tools\solution_runner.py")
cases_generator = AIC(r"tools\cases_generator.py")


status_list代码 = """```
import multiprocessing
import time
import ctypes

# 定义一个自定义的 C 语言结构体，用来存放数据
class CrashRecord(ctypes.Structure):
    _fields_ = [
        ('cases_index', ctypes.c_uint64), # 64位无符号整型
        ('timestamp', ctypes.c_double)  # 双精度浮点数时间戳
    ]

def worker(shared_value):
    # 子进程崩溃时写入，通过属性名直接赋值，非常直观
    shared_value.cases_index = 146744073709551615
    shared_value.timestamp = time.time()

if __name__ == "__main__":
    process_count = 4
    
    # 1. 为每个进程创建独立的结构体 Value
    # 使用 RawValue 绕过不必要的进程锁，追求极致速度
    slots = [multiprocessing.RawValue(CrashRecord, 0, 0.0) for _ in range(process_count)]
    
    processes = []
    for i in range(process_count):
        # 2. 精准传递单个信号量
        p = multiprocessing.Process(target=worker, args=(slots[i],))
        processes.append(p)
        p.start()
        
    for p in processes:
        p.join()
        
    # 3. 主进程读取
    for i, slot in enumerate(slots):
        if slot.timestamp > 0:
            print(f"进程 {i} 崩溃：cid={_GLOBAL_CASES_READER[slot.cases_index]['cid']}, 时间={slot.timestamp}")
```"""


# {README}
# {AGENTS_DOC}
# {RAG_DOC}
# 参考代码：
# {solution_runner}
# {cases_generator}
template_text = fr"""
{README}
参考代码：
{solution_runner}
{cases_generator}
{AIC(r"tools\solution_runner(modify).py")}
执行：
{AIC(r"V0.7.6版调用程序.py")}
{AIC(r"V0.7.6报错.txt")}
solution_runner 虽然可以刹停TLE程序，但是没有记录到log（无 'TLE_*'）。
GPT5分析原因如下：
- Windows 的 terminate()直接把进程砍掉。不会：signal.signal(SIGTERM,...)
- 即便是 Linux 的，traceback 只代表：当前栈帧不是完整 traceback。
因此修改意见：
- 放弃 signal(SIGTERM ，在主进程捕捉TLE的子进程最后保存信息（cid,时间戳）写 log（调用 _log_result 统一格式）
- 大部分全局变量无意义，因为用传参，应删除避免竞争。
- 建议采用 PyArrow 技术只读共享可序列化，在主进程初始化全局测试样例list的内存指针：
```参考代码
import pyarrow as pa
from multiprocessing import shared_memory

_GLOBAL_CASES_READER = None

def _init_process_worker(shm_name: str, shm_size: int, ...):
    global _GLOBAL_CASES_READER
    
    # 1. 连接共享内存
    shm = shared_memory.SharedMemory(name=shm_name)
    
    # 2. 核心优化：直接用 pyarrow 的 Buffer 指向这块内存，【零拷贝，零反序列化开销】
    # 这步操作耗时接近 0 毫秒！
    buf = pa.pyarrow_wrap_buffer(shm.buf)
    
    # 3. 读入为 pyarrow 的 RecordBatch 或 Tensor（取决于您存的数据类型）
    # 此时 _GLOBAL_CASES_READER 只是一个内存指针映射
    _GLOBAL_CASES_READER = pa.ipc.open_stream(buf).read_all()

# 多个子进程同时执行此切片，在操作系统层面是完全并发、互不干扰、且速度极快的只读流。
```
- 不要用 manager.list ，因为所有子线程都要抢占一个 manager.list 对象：
- 保持原有的TLE视为早停，而早停只杀出错的进程，其余进程等待其该group产出并收集结果。
- 建议删除 group，改为单样例 获取、上报。因为用了 PyArrow 技术，仅需获取单个下标，内容少多进程抢占时间短。
- 每个子进程用两个 multiprocessing.Queue： input_queue 和 output_queue：
  - input_queue：仅输入其在 _GLOBAL_CASES_READER 中的下标
  - output_queue：返回 cases_result 的结果（包含ERROR的情况，但是不含TLE）
- early_stop_event: multiprocessing.Event，不需要全局遍历，通过传参给子进程共用
- 每个子进程用一个 multiprocessing.Value + 结构体 Structure ，来记录开始执行的样例。主进程将其包装为一个 status_list，给子进程代入不同的对象，参考代码：
{status_list代码}
"""


# 可以参考GPT联网搜索下的建议：
# {AIC(r"GPT的改进方案V0.7.6.a.md")}

# 使用示例
line_count = template_text.count('\n')
print(f"待合并文本共 {line_count} 行")

if AIC.copy_to_clipboard(template_text):
  print("✅ 已成功复制到剪贴板。")
else:
  print("❌ 复制失败，请检查系统环境。")


# - 原 safe_iter_kit.pyx 有一个风险点，对于树，其 stack 和 queue 并没有持有原生节点的引用计数
# - 因此需要修改为入 stack（queue） 就增加引用，而 check_safe 仅当为重复（in _seen 为真）时减少引用计数，销毁时按 _seen 减少引用计数