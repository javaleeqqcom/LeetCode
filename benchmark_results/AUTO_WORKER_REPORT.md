# Auto Worker 校准与验收报告

测试日期：2026-08-10

环境：Windows AMD64，12 物理核 / 24 逻辑处理器，约 47.1 GiB 物理内存

限制：最多 16 个工作进程，Auto 内存预算 8 GiB，校准重复 3 次

## 1. 校准结果

以下为中位数。Persistent Python 的 `wall` 不含一次性进程池启动，因此同时列出首次运行总时间；C++ 的 `wall` 已包含管理器和 Worker 启动。

| Worker | Python wall (s) | Python 启动 (s) | Python 首次总计 (s) | 首次加速比 | C++ wall (s) | C++ 加速比 |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1.6729 | 0.1164 | 1.7893 | 1.00× | 0.5980 | 1.00× |
| 2 | 0.8404 | 0.1479 | 0.9883 | 1.81× | 0.3436 | 1.74× |
| 4 | 0.4775 | 0.2234 | 0.7009 | 2.55× | 0.3686 | 1.62× |
| 6 | 0.3674 | 0.3088 | **0.6762** | **2.65×** | 0.1803 | 3.32× |
| 8 | 0.3265 | 0.3679 | 0.6944 | 2.58× | 0.2953 | 2.03× |
| 12 | 0.2775 | 0.5644 | 0.8419 | 2.13× | **0.1573** | **3.80×** |
| 16 | 0.2544 | 0.6728 | 0.9272 | 1.93× | 0.1761 | 3.40× |

Auto 在复验中为首次运行的 Persistent Python 选择 6 个进程，为编译型 C++ 选择 12 个进程，与各自实测最佳点一致。Python 若长期复用已启动的进程池，12～16 Worker 的稳态吞吐仍可能更高，可通过增大 `expected_runs` 让模型摊薄启动成本。

峰值 Worker RSS：Python 约 29.1 MiB（1）至 461.5 MiB（16）；C++ 约 5.3 MiB（1）至 69.1 MiB（16），均显著低于 8 GiB 预算。

## 2. 极端情况

使用无限循环程序各测试 1 个样例：

- Python：单进程探针 TLE，Auto 固定为 1 Worker；正式执行记录 1 个 `timed_out_case` 并替换受影响 Worker。
- C++：单进程探针超时，Auto 固定为 1 Worker；Job Object 能终止失控批次，探针加正式执行总计约 0.44 秒。
- 断言理由均包含 `probe_timed_out` 与 `single_worker_limits_resource_blast_radius`。

## 3. 结论

Auto 不是简单取逻辑核心数。本机上 Python 首次运行在 6 Worker 后已被进程启动成本抵消；C++ 在 12 Worker 最快，16 Worker 因调度和内存层次竞争回退。加入实测档案后，两类后端都能选中本轮最佳档位，小样例会保持单进程，TLE 会限制为单进程。

原始数据：[`auto_tune_calibration_final.json`](auto_tune_calibration_final.json)。设计说明：[`../plan_documents/AUTO_WORKER_DESIGN.md`](../plan_documents/AUTO_WORKER_DESIGN.md)。
