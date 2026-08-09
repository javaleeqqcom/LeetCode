# C/C++ OJ 执行与并行性能报告

## 验收结论

v0.10.0 已实现 C++ `class Solution` 基础 JSON 子集和 C 全局标量函数。源码编译为
独立 Worker 后，由现有 Windows C++ Job Object 管理器启动 1/4/8/16 个进程；
每个进程循环执行多个 `.ojbin` 样例。所有正式场景均与 Python expected 和摘要一致。

测试环境：24 个逻辑处理器，桌面环境最多使用 16 个 Worker；MSVC x64
`19.51.36241`，`/O2 /std:c++17`。各 C++ 方法首次编译约 `2.24～2.43s`，缓存
命中为 `0s`。下表执行墙钟不包含编译，但包含 C++ 管理器和 Worker 冷启动。

## C++ 与长驻 CPython

正式矩阵每格 3 次取中位数。`Python 1` 是长驻 CPython 单进程；`C++ 1` 包含
一次原生批次进程启动；`C++ best` 在 1/4/8/16 中选择墙钟最短者。

| 算法与规模 | Python 1 | C++ 1 | C++/Python | C++ best |
|---|---:|---:|---:|---:|
| integer mix 10k | 0.0476s | 0.0421s | 1.13× | 1 / 0.0421s |
| integer mix 100k | 0.4676s | 0.1697s | 2.76× | 4 / 0.0750s |
| vector checksum 10k × 64 | 0.1290s | 0.0855s | 1.51× | 4 / 0.0631s |
| binary search 10k × 256 | 0.1499s | 0.2037s | 0.74× | 4 / 0.0907s |
| sort checksum 2k × 512 | 0.0649s | 0.0982s | 0.66× | 4 / 0.0717s |
| sieve 512 × ~5k | 0.1608s | 0.0331s | 4.85× | 1 / 0.0331s |
| LCS 128 × 400² | 2.0262s | 0.0560s | 36.17× | 4 / 0.0454s |
| matrix 64 × 32³ | 0.1675s | 0.0347s | 4.83× | 1 / 0.0347s |

二分和排序场景中，C++ 算法本身很短，JSON 解码与原生批次启动使其暂时慢于已经
启动的 Python 热池；这类负载不应为了“使用 C++”强制走多进程。LCS、筛法、矩阵
和 100k 微任务足以摊薄启动成本，C++ 优势明显。

## C 与 C++ 标量路径

相同 integer mix 100k 用例中：C 单进程 `0.1737s`、C++ 单进程 `0.1697s`、
Python 单进程 `0.4676s`。C 和 C++ 使用同一个管理器、JSON Runtime 与摘要协议，
差异在噪声范围内；C 数组 ABI 尚未加入本轮对比。

## C++ 重负载扩展性

为避免 Python expected 生成本身成为基准瓶颈，使用 8192 对相同字符串；expected
可直接确定为 400，但学生 LCS 仍完整执行 `O(400²)` DP。每格 5 次中位数：

| Worker | 墙钟 | 加速比 | Worker 总 RSS |
|---:|---:|---:|---:|
| 1 | 1.1576s | 1.00× | 11.2 MiB |
| 4 | 0.3782s | 3.06× | 24.1 MiB |
| 8 | 0.2518s | 4.60× | 41.0 MiB |
| 16 | 0.2343s | 4.94× | 74.6 MiB |

16 进程仍最短，但从 8 到 16 仅改善约 7%；桌面日常运行优先 8，只有单批计算量
足够大且系统空闲时才使用 16。

## 正确性与故障恢复

- 45 项全量单元测试通过，覆盖原 Python 随机样例、persistent/native 后端和
  Agent/RAG 管线。
- C++ Two Sum 同时通过位置参数与按参数名组织的 JSON 对象输入。
- 错误答案和 C++ 异常通过 fallback 记录生成与 Python 完全相同的摘要。
- 无限 C++ 循环在 `0.4s` 批次超时后由 Job Object 终止，整个测试在 4 秒内返回。
- C 标量 fixture 与 C++/Python 共享同一 `.ojbin` 并通过 200 例差分验证。
- 全部 Worker RSS 远低于 8 GiB；8192 例重负载在 16 Worker 时总 RSS 约
  `74.6 MiB`。

## 原始数据与复现

- [`compiled_language_scaling_final.json`](compiled_language_scaling_final.json)：
  C/C++/Python 经典算法正式矩阵。
- [`compiled_language_scaling_cpp_heavy_final_v2.json`](compiled_language_scaling_cpp_heavy_final_v2.json)：
  C++ 重负载 5 次矩阵。

```powershell
python -m tests.benchmark_compiled_languages --repeats 3 `
  --workers 1 --workers 4 --workers 8 --workers 16 `
  --force-rebuild --output-suffix final
```
