```ps1
(py314) PS C:\Users\john> maturin --version
maturin 1.13.1
(py314) PS C:\Users\john> cargo expand --version
cargo-expand 1.0.121
```

你现在已经进入：

# “Runtime 架构设计”

阶段了。

不是简单的：

* Python 调 multiprocessing
* Rust 调 Python

而是：

# 如何设计一个真正高吞吐的 OJ Runtime

你现在提的几个问题，
其实本质是：

# Rust 与 Python 的边界该怎么划分

这是核心。

我先直接给结论：

---

# 结论（非常重要）

# 你必须采用：

# 方案 A

即：

```text
Rust Worker
    ↓
长期持有 Python Interpreter
    ↓
循环收任务
```

而绝对不能：

# 方案 B

即：

```text
每次 chunk 都重新调用 Python
```

因为：

# Python 启动极贵

尤其 Windows。

---

# 你现在已经发现：

你真正的敌人不是 GIL。

而是：

```text
Python Runtime Bootstrap
```

包括：

* import
* sys.path
* exec
* module build
* class build
* gc init
* allocator
* refcount graph

这些。

---

# 所以：

# 正确架构必须是：

# “Persistent Python Worker”

即：

```text
Rust Runtime
    ↓
启动 N 个 Python Worker
    ↓
每个 Worker:
    - 只初始化一次
    - 只 import 一次
    - 只 exec 一次
    - 只构建一次 Solution()
```

然后：

```text
循环：
    接收 case chunk
    执行
    返回结果
```

这才是工业方案。

---

# 这也是：

# PyTorch

# Ray

# vLLM

# TensorRT-LLM

等等所有高性能 Python Runtime 的核心思想。

---

# 你的未来架构应该是：

# Rust Runtime Core

负责：

```text
- scheduler
- worker pool
- load balancing
- timeout
- sandbox
- memory limit
- logging
- early stop
- merge
```

---

# Python Worker

负责：

```text
- execute Solution
- inspect
- conversion
- ListNode
- TreeNode
```

---

# 所以：

# 你的第4问：

> Rust 如何动态分配 chunk，而 Python 动态接收？

答案：

# Job Queue

这是标准 Worker Pool。

---

# 推荐最终架构

# Rust Master

```text
global queue
```

里面：

```rust
struct Job {
    start: usize,
    end: usize,
}
```

---

# Python Worker

循环：

```python
while True:
    job = recv_job()

    if job == STOP:
        break

    process_cases(job)
```

---

# 这里关键点：

# Python Interpreter 不退出

这才是核心。

---

# 你现在应该避免：

# “每 chunk 一次 Python”

否则：

```text
Rust
    ↓
启动 Python
        ↓
        import
        exec
        init
        process
退出
```

会比你现在 multiprocessing 还慢。

---

# 所以：

# 你实际上已经不再是：

“Rust 调 Python”

而是：

# Rust Hosting Python Runtime

这差别巨大。

---

# 下一问题：

# Rust 怎么持有 Python？

你有三种方案：

---

# 方案1（推荐）

# PyO3 Embedded Python

即：

```rust
Python::with_gil(...)
```

或者：

```rust
prepare_freethreaded_python()
```

这是最推荐的。

---

# 优势

你可以：

```rust
worker thread
    ↓
独立 Python interpreter
```

并且：

* 无需 subprocess
* 无需 pipe
* 无需 pickle
* 无需 spawn
* 无需 JSON IPC

性能极强。

---

# 尤其：

# Python 3.14 Free-threaded

未来会极其适合这个架构。

因为：

```text
Rust Thread
    ↓
Embedded CPython
    ↓
无 GIL
```

会非常猛。

---

# 你现在其实正好踩中未来方向：

# Rust + FreeThreaded Python

这是未来 AI Runtime 的重要方向。

---

# 但：

# 当前 PyO3 对 free-threaded 还在演进

所以：

目前建议：

# “1 Worker = 1 Python Interpreter”

不要共享解释器。

---

# 推荐架构（当前最佳）

# Rust

```text
N worker threads
```

每个：

```text
持有：
- 一个 Python interpreter
- 一个已初始化 Solution()
- 一个 conversion
```

---

# 然后：

# 动态 stealing queue

例如：

```text
crossbeam-deque
```

---

# 然后：

Python worker：

```python
process_cases(cases[start:end])
```

---

# 这样：

# chunk 可以非常小

因为：

不再有：

* spawn
* import
* exec

开销。

---

# 这是你最关键的突破点：

# chunk 粒度终于可以很细

这会极大改善：

```text
负载均衡
```

---

# 你现在的问题：

```text
后期只剩小 chunk
```

是典型：

# Static Chunking 问题

---

# 正确方案：

# Work Stealing

Rust 非常适合。

例如：

```text
worker 空闲
    ↓
偷别人的 chunk
```

---

# 所以：

# 不再需要：

```python
_geom_queue_generator()
```

这种几何切块。

---

# 而是：

# runtime dynamic scheduling

---

# 最终：

# 每个 case 甚至都可以是单独任务

因为：

任务调度已经很轻。

---

# 你现在会进入：

# 两层调度

---

# Rust层

负责：

```text
CPU负载均衡
```

---

# Python层

负责：

```text
算法执行
```

---

# 你后面甚至可以：

# Python Worker 热更新

即：

```text
Rust runtime 不停
只替换：
- student code
- solution object
```

---

# 这会极大提升：

# AI 自动生成→自动验证

循环速度。

---

# 你真正应该避免的

# 千万别：

```text
Rust
    ↓
subprocess python
```

这会退化。

---

# 你真正应该做的是：

# Embed Python

---

# 未来最终形态

你后面会逐渐形成：

# Rust Judge Kernel

类似：

```text
mini-LeetCode runtime
```

---

# 支持：

```text
Python
C
C++
Rust
Go
Java
```

---

# 而：

# Python 只是“插件语言”

---

# 你现在最推荐的路线

# Phase 1

先：

# Rust + PyO3

实现：

```text
persistent python worker
```

---

# Phase 2

实现：

```text
dynamic work stealing
```

---

# Phase 3

实现：

```text
memory pool
zero-copy cases
```

---

# Phase 4

实现：

```text
多语言统一 ABI
```

---

# 最后：

你现在已经完全不需要：

```python
ProcessPoolExecutor
```

了。

因为：

# Rust Runtime 会彻底替代它。
