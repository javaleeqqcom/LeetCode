# Auto Worker 自动并行度设计（v0.11.0）

## 1. 目标与边界

`workers="auto"` 面向同一份学生程序反复执行大量相互独立的 OJ 样例。它要在不超过 16 个工作进程、默认不超过 8 GiB 运行预算的前提下，自动平衡进程启动、JSON 解码、计算、尾部负载与桌面系统资源竞争。

Auto 不是新的学生代码编译器，也不会把 Python 解答自动转为 Cython。`PersistentPythonRunner` 仍使用长驻 CPython 进程；`CompiledCppRunner` 仍先编译 C/C++ 解答，再由原生 Job Object 管理器启动独立 Worker。

## 2. 决策输入

一次决策综合三组信息：

1. 主机状态：逻辑/物理核心数、当前 CPU 负载、总内存和可用内存。
2. 工作负载：样例数、`.ojbin` 文件大小、均值/P95/最大输入 JSON 大小、预期答案覆盖率。
3. 程序特征：语言、源码大小、循环数量和最大嵌套深度、分支数、直接递归，以及单进程代表样例的实测计算/解码/RSS。

样例探针从数据集首尾和中间均匀抽取，避免只测试最小输入。默认抽取 8 个样例。Python 使用每样例超时；C++ 管理器当前只有批次超时，因此按“每样例限时 × 抽样数”换算。

## 3. 选择过程

```text
候选进程数
  = {1, 2, 4, 6, 8, 12, 16}
  ∩ CPU 上限
  ∩ 内存上限
  ∩ 样例并行度上限
```

- CPU：默认保留 1～4 个逻辑处理器给 Windows 和其他桌面进程，同时不超过“物理核心 + 1/3 物理核心”；当前负载达到 80% 时进一步收缩。
- 内存：取 `min(8 GiB, 75% 可用内存)`，除以探针测得的单 Worker RSS；没有 `psutil` 时使用保守默认值。
- 样例数：微小样例默认每 Worker 至少 4 个；若探针表明单样例较重，则自动放宽为每 Worker 1～2 个。
- 时间模型：`startup / expected_runs + compute / (workers × efficiency) + decode / effective_workers`。
- 收益门槛：预测收益不足 5% 时保持单进程，避免为小任务支付启动成本。

若代表样例 TLE 或原生探针异常退出，Auto 选择 1 个进程。这样并不能让错误算法变快，但能避免同时启动 8～16 个死循环并扩大资源占用。

## 4. 本机校准档案

默认内置一份保守模型。执行以下自测会覆盖为当前机器实测模型：

```powershell
C:\Users\john\anaconda3\envs\py314\python.exe tests\calibrate_auto_workers.py
```

校准器测试 1/2/4/6/8/12/16 进程，分别测量长驻 CPython 的进程池启动时间、C++ 原生 Worker 启动时间和 CPU 密集 LCS 的并行效率。结果写入：

- `build/auto_tune/host_profile.json`：运行时读取，包含机器指纹，属于本机构建产物。
- `benchmark_results/auto_tune_calibration_final.json`：可审计的原始测量、Auto 复验与 TLE 结果。

CPU/内存或操作系统指纹不匹配时不会套用旧档案，而会回退到内置模型。`expected_runs` 可声明同一进程池预计复用次数，让启动成本按次数摊销。

## 5. API 与生命周期

```python
from runtime.runner import AutoTuneConfig, PersistentPythonRunner

config = AutoTuneConfig(
    max_workers=16,
    memory_budget_bytes=8 * 1024**3,
    expected_runs=1,
)

with PersistentPythonRunner(
    "solution.py",
    main_method="solve",
    workers="auto",
    standard_mode=True,
    auto_tune_config=config,
) as runner:
    report = runner.run_store("cases.ojbin", collect_results=False)
    print(report.metrics.workers, report.auto_tune)
```

Python Auto 会延迟创建正式进程池：先由一个临时 Worker 探测，再一次性创建最终数量的长驻 Worker。一个 Runner 首次运行后保持该数量，以免为后续相同工作负载反复销毁进程；若数据规模发生数量级变化，应新建 Runner。C/C++ 探针复用已缓存的编译产物。

`RunReport.auto_tune` 保存候选数、各候选预测时间、CPU/内存上限、探针指标、理由和档案来源，便于复现而不是把 Auto 做成黑盒。

## 6. 已知限制

- Auto 优化吞吐量，不改变单样例时间复杂度，也不替代 OJ 的正式时间限制。
- CPU 当前负载是瞬时信号；高波动桌面环境下应在相对空闲时运行校准器。
- Job Object 已能限制进程、内存和超时，但文件 ACL、受限令牌/AppContainer 与网络隔离仍是后续沙箱阶段。
- 链表、树和复杂多方法 C/C++ ABI 仍不在当前编译执行器支持范围内。
