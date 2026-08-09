# Cython 热点加速更新方案

## 结论与术语

`PersistentPythonRunner` 当前默认启动 CPython 进程。它的优化来自进程长驻、源码和依赖只加载一次、mmap 按记录读取、动态分块以及结果摘要回传；它没有把 Python 解答转换为机器码，也不依赖 Python 类型注解。

C++ 管理器只负责创建、限制和等待 Python 进程。被调用的 `Solution` 方法仍由 CPython 解释执行，因此会增加一次管理器启动和命令行/结果文件协议开销；只有减少 Python 建池、通信或隔离成本时，端到端才可能更快。现有基准正好反映了这一点：C++ 冷启动批处理有价值，但在可复用的热池吞吐量上没有稳定超过长驻 CPython。

Cython 可以将 `.pyx` 或受支持的 `.py` 编译为 C/C++，再由系统编译器生成 Windows `.pyd`。不过，把动态 Python 原样编译通常只得到有限收益；明显加速需要让热点循环使用 C 数值类型、typed memoryview、`cdef/cpdef`、早绑定，并尽量避免在循环中创建 Python 对象或调用 Python 方法。

## 已有基础

- 环境已安装 Cython 3.2.4。
- `tools/safe_iter_kit.pyx` 已使用 `cdef class`、C/C++ 容器和强类型局部变量。
- 本机已能构建 `safe_iter_kit.cp314-win_amd64.pyd`。
- 旧 `tools/setup.py` 仍是单模块、MSVC 参数硬编码的实验构建入口，后续不能直接扩展为整个工程的正式构建系统。

## 不应整体编译的部分

- 任意学生/AI 生成的 `Solution`：类型和语义不稳定，编译耗时可能高于执行收益。
- Agent、RAG、Ollama 和文件编排：主要等待模型、磁盘或数据库，机器码化收益很低。
- `multiprocessing.Queue` 和 Windows 进程控制：瓶颈在内核 IPC，改写 Python 表面循环帮助有限。
- JSON 解码本身：标准库解码器已经是 C 实现，Cython 包装不会自动消除 Python 对象创建。

特别注意：加载 `.pyd` 等于在进程中运行本地机器码，能够绕过 Python AST、导入和内建函数限制。未经信任的 AI 代码不能在完成 AppContainer、构建隔离和制品校验前自动编译并加载。

## 第一阶段：只编译框架稳定热点（建议 0.8.1 实验）

新增独立目录，保留纯 Python 回退：

```text
runtime/accel/
├── __init__.py          # HAS_ACCEL 与回退选择
├── _runner_accel.pyx    # 稳定 Cython API
├── fallback.py          # 语义完全一致的 Python 实现
└── README.md
```

首批候选函数必须先用现有计时字段和 profiler 证明占比：

1. `.ojbin` 偏移表的批量边界读取与连续区间迭代；
2. 结果计数、摘要 XOR 合并和固定格式数值比较；
3. C++/Python 动态 Worker 共用的原子分块计数器；
4. 数值数组的标准化与比较，可使用 typed memoryview；
5. stdout 限长写入等每样例重复执行的稳定小循环。

边界要求：

- Python 与 Cython 实现使用同一测试向量并逐项验证输出、异常和溢出语义；
- 扩展导入失败时自动回退，不影响 PyPy 和无编译器环境；
- 不把 Python 任意精度整数静默替换为会溢出的 C `int`；
- 每个候选优化必须报告热点微基准和端到端基准，不能只报告函数级速度。

## 第二阶段：可选的受信任 Solution 编译

只对用户明确选择、来源可信、调用次数足够多的标准 OJ 程序开放：

1. 读取方法签名和样例统计，建立明确的标量/数组输入 schema；
2. 优先使用 Cython pure-Python mode，使源码仍可由 CPython 直接运行；
3. 仅给热点局部变量和循环加 `cython.int`、`cython.longlong`、`cython.double`、memoryview 等真实 C 类型；
4. 以“源码哈希 + schema + CPython ABI + Cython 版本 + 编译器参数”作为缓存键；
5. 在独立构建目录编译，构建超时或失败立即回退 CPython；
6. 编译后先跑差分测试，再允许进入性能批次。

普通的 `list[int]`、`dict[str, int]` 注解主要描述 Python 对象，并不自动把列表元素变成连续 C 数组。若要明显加速，需要在边界上把输入转换为 typed memoryview/C 数组；只有当单次转换成本能被大量循环计算摊薄时才值得采用。

## 第三阶段：与沙箱集成（0.9 之前的前置条件）

- 编译器在单独的低权限构建进程中运行；
- 构建目录与题目目录分离，并限制输入/输出 ACL；
- 对生成的 C/C++、编译命令和 `.pyd` 记录哈希及审计日志；
- 原生扩展只在 AppContainer/受限令牌 Worker 中加载；
- 默认禁网、禁止子进程，并限制 Job CPU、内存和墙钟时间；
- 不缓存来源不可信且未通过差分验证的制品。

## 性能采纳门槛

采用与现有后端相同的输入、随机种子、结果摘要和 `1/2/4/6/8/12/16` Worker 矩阵：

- 框架扩展：至少两类负载端到端提升 15%，且没有场景回退超过 5%；
- Solution 热点编译：必须包含编译时间、首次执行和缓存命中三种口径；
- 缓存命中后累计节省时间必须大于编译时间的 3 倍；
- 内存、TLE 恢复、输入隔离和错误栈可诊断性不得退化；
- 未达到门槛的 `.pyx` 仅保留实验分支，不进入默认路径。

## 推荐实施顺序

1. 用 `py-spy/cProfile` 和现有 `worker_compute_seconds/worker_decode_seconds` 定位真实热点；
2. 整理统一 Cython 构建配置，先重建并回归现有 `safe_iter_kit`；
3. 实现 `_runner_accel.pyx` 与 Python fallback 的最小功能对；
4. 做单进程微基准，再做 1～16 Worker 端到端对照；
5. 只有框架热点达到门槛后，再做受信任 Solution 的 opt-in 编译原型；
6. AppContainer 和制品隔离完成前，不对 AI 生成代码启用原生编译。
