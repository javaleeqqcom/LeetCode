# Runtime 热点优化与 Cython 采纳报告

## 结论

v0.9.0 采纳纯 Python Phase A 和 `.ojbin` v2 作为默认路径；学生 OJ 源码仍由
长驻 CPython 解释执行，不会自动编译。可选 Cython 摘要扩展已能构建为 `.pyd`
并通过差分测试，但端到端收益随进程数波动，未达到默认采纳门槛，因此仅通过
`OJ_RUNTIME_ACCEL=cython` 显式启用。

本轮没有继续开发 `_chunk_kernel.pyx`。当前剩余主要成本是学生 Python 方法调用、
JSON 对象构造和 Windows 多进程调度；把更大的调度循环搬入 Cython 会扩大 ABI 与
维护成本，却无法释放任意 `Solution` 调用期间的 GIL。

## 实现范围

- `.ojbin` v2 在索引中预存正确结果摘要，仍可读取 v1。
- 只在实际输出与 `expected` 的规范 JSON 类型和值完全一致时复用摘要。
- 汇总模式跳过逐样例计时、结果对象、父进程重复 hash 和无用 stdout Writer。
- 未配置 TLE 时不再为每个样例写跨进程共享状态。
- native worker 每个进程只做一次 stdout 空设备重定向。
- 摘要协议固定为 `canonical-json-blake2b-128-v1`，报告中显式记录版本。
- Python fallback 和 Cython `.pyd` 使用相同测试向量；扩展导入失败自动回退。

## 默认路径最终性能

环境为 CPython 3.14、24 个逻辑处理器；测试最多使用 16 个工作进程。表中为热池
墙钟时间中位数，括号内是同一新后端相对 1 进程的加速比。

| 场景 | 1 进程 | 4 进程 | 8 进程 | 16 进程 |
|---|---:|---:|---:|---:|
| tiny 10k | 0.0474s (1.00×) | 0.0174s (2.73×) | 0.0161s (2.95×) | 0.0182s (2.61×) |
| tiny 100k | 0.4800s (1.00×) | 0.1558s (3.08×) | 0.1042s (4.61×) | 0.1027s (4.67×) |
| vector 10k | 0.1122s (1.00×) | 0.0394s (2.84×) | 0.0289s (3.88×) | 0.0319s (3.51×) |
| LCS 128 | 2.0351s (1.00×) | 0.6453s (3.15×) | 0.3678s (5.53×) | 0.3131s (6.50×) |
| tiny 1m | 4.8498s (1.00×) | 1.4427s (3.36×) | 0.9394s (5.16×) | 0.6700s (7.24×) |

相对之前保存的 v0.8.0 结果，tiny 100k 在 1/4/8/16 进程分别提升
`1.68× / 1.50× / 1.72× / 1.26×`；tiny 1m 分别提升
`1.57× / 1.62× / 1.60× / 1.85×`。

## 重负载同会话回归检查

历史文件跨时段比较会受到 Windows 后台负载、温度和频率影响，因此又从 Git
`HEAD` 导出 v0.8.0 临时副本，在同一会话用相同 LCS 输入各跑 5 次。正百分比表示
v0.9.0 更快。

| 进程 | v0.8.0 | v0.9.0 | v0.9.0 变化 |
|---:|---:|---:|---:|
| 1 | 2.0562s | 2.0382s | +0.9% |
| 4 | 0.5831s | 0.5997s | -2.8% |
| 8 | 0.3599s | 0.3685s | -2.3% |
| 16 | 0.2853s | 0.2598s | +9.8% |

核心 1/4/8/16 矩阵没有超过 3% 的重负载回退。额外的 4 进程、21 组同池交替
A/B 稳定性测试中，Phase A 为 `0.61044s`，完整摘要和逐例计时模式为
`0.61898s`，Phase A 中位数快 `1.40%`。

## Cython `.pyd` 决策

在最终代码上用 tiny 100k 各跑 5 次，比较默认 Python fallback 与显式 Cython：

| 进程 | Python | Cython | Cython 变化 |
|---:|---:|---:|---:|
| 1 | 0.4689s | 0.4663s | +0.6% |
| 4 | 0.1369s | 0.1497s | -8.5% |
| 8 | 0.0955s | 0.0957s | -0.3% |
| 16 | 0.0894s | 0.0804s | +11.1% |

函数级摘要更快，但端到端结果不稳定且 4 进程超过回退门槛，所以 `.pyd` 不作为
默认依赖。它保留为可复现实验，也为以后真正占比足够高的框架热点提供构建骨架。

## 验证与原始数据

- `python runtime/accel/setup.py build_ext --inplace`：成功生成 CPython 3.14
  `win_amd64` `.pyd`。
- `python -m compileall -q runtime tests tools agents rag schemas`：通过。
- `python -m unittest discover -s tests -p "test_*.py" -v`：38 项通过。
- `OJ_RUNTIME_ACCEL=cython` 下 Runtime、persistent 和 native 关键套件：14 项通过。

原始结果：

- [`runner_backend_comparison_runtime_accel_final.json`](runner_backend_comparison_runtime_accel_final.json)
- [`runner_backend_comparison_runtime_accel_million_final.json`](runner_backend_comparison_runtime_accel_million_final.json)
- [`runner_backend_comparison_same_session_v080.json`](runner_backend_comparison_same_session_v080.json)
- [`runner_backend_comparison_same_session_runtime_accel.json`](runner_backend_comparison_same_session_runtime_accel.json)
- [`runner_backend_comparison_digest_python_final.json`](runner_backend_comparison_digest_python_final.json)
- [`runner_backend_comparison_digest_cython_final.json`](runner_backend_comparison_digest_cython_final.json)
- [`runtime_accel_paired_lcs_4w_stability.json`](runtime_accel_paired_lcs_4w_stability.json)
