# 长驻 OJ 执行器与原生管理器设计

## 目标与边界

本子系统处理大量互相独立、程序相同而输入不同的 OJ 测试样例。正式基准使用 `1/2/4/6/8/12/16` 个工作进程；12 是物理核心边界，16 为 Windows 桌面环境中的最高调试档位。24 个逻辑处理器不作为日常结论依据。

旧 `tools/solution_runner.py` 保留为兼容基线。新代码放入 `runtime/runner/`，原生代码放入 `native_runner/`，不会用未经验证的新实现覆盖旧接口。

## 目录映射

| 旧职责 | 新位置 | 状态 |
|---|---|---|
| 通用兼容执行 | `tools/solution_runner.py` | 保留，不移动 |
| 大规模用例数据 | `runtime/runner/case_store.py` | 新增，版本化 `.ojbin` |
| 长驻 CPython/PyPy Worker | `runtime/runner/persistent_python.py` | 新增 |
| 标准 OJ 格式约束 | `runtime/runner/standard.py` | 新增 |
| Windows 原生管理门面 | `runtime/runner/native_process.py` | 新增 |
| C++ Job Object 管理器 | `native_runner/` | 新增、已编译测试 |
| 统一三方基准 | `tests/benchmark_runner_backends.py` | 新增 |

题目目录和原有 `tools.*` 导入暂不批量移动。迁移应通过兼容门面逐项完成，避免一次性改名破坏已有题目脚本。

## 数据与执行协议

`.ojbin` 文件结构为：

```text
Header(magic, version, count, table_offset)
Case payload 0
Case payload 1
...
Offset/length table
```

Writer 接受任意迭代器，索引暂存于磁盘，因此生成 100 万样例时不需要在主进程建立 100 万个 Python 字典。Reader 通过只读 mmap 和偏移表按需解析单个样例。

长驻 Worker 生命周期：

1. 启动 Python 解释器。
2. 加载学生源码、转换器与依赖。
3. 等待主进程分配一个连续样例范围。
4. 循环解码、创建 `Solution()`、执行和比较。
5. 分块回传结果或摘要。
6. 接受下一批测试，不重新加载程序。

默认每个样例创建新的 `Solution()`，防止学生代码在 `self` 中保存的状态污染下一个样例；可信无状态程序可显式选择复用实例。

## 调度策略

Python 长驻后端采用动态分块和每 Worker 独立控制队列。默认总任务数约为 `4 × workers`。实测从 16 波减少到 4 波后，10 万微型样例在 16 Worker 下由约 0.221 秒降至约 0.112 秒，同时 LCS 高并发仍有改善。继续减少到 2 波只对部分微型场景有小幅收益，却使 LCS 12/16 Worker 回退约 5%～7%，因此最终采用 4 波。

C++ 原型当前使用静态等数量分片。它适合相同规模用例和沙箱批次，但对高度不均匀的输入不如 Python 动态后端。只有以后增加低开销控制通道后，才考虑在 C++ 层实现动态领取任务。

## 标准 OJ 模式

标准模式要求：

- 恰好一个 `Solution` 类和显式主方法；
- 参数及返回值为 JSON 基础类型；
- 仅使用常见算法标准库；
- 禁止 `open/eval/exec/compile/input`、系统模块导入和 dunder 属性访问。

它可以显著减少启动依赖并使 PyPy 3.9 Worker 可运行，但 AST 检查不是安全边界。恶意或 AI 生成代码仍必须在 OS 沙箱内执行。

## C++/Windows 安全状态

已实现并测试：

- C++ 创建挂起的 Python 进程；
- 加入 Windows Job Object 后才恢复执行；
- 限制活动进程数（API 上限 16）；
- 限制每个进程提交内存；
- 管理器关闭时杀死全部 Worker；
- 整批超时时终止 Job；
- 指定工作目录和独立结果目录。

尚未实现：

- 受限令牌或 AppContainer；
- 仅工作目录可写的 ACL；
- 禁止网络；
- 系统调用白名单；
- 每个样例的原生动态重分配。

在以上项目完成前，只能称为“资源隔离/沙箱原型”，不能称为完整安全沙箱。

## PyPy 结论

PyPy 3.9 已通过标准模式正确性验证。C++ 静态启动模式中，LCS 有明显 JIT 收益，但多进程启动开销较高；PyPy 自带的 Windows multiprocessing Queue 在本机扩展表现较差。当前策略是：

- 默认：长驻 CPython 标准后端；
- 可选：计算特别重的单进程/少进程 PyPy；
- 不采用：PyPy 多进程作为统一默认后端。

## 采纳规则

- 长驻 Python 后端相对旧执行器有数量级明显的吞吐收益，予以保留。
- C++ 管理器相对已启动的长驻 Python 在百万微型样例中只快约 5.6%，没有达到预设的 20% 热池性能替换门槛，因此不作为重复批次的默认后端；它在一次性冷任务中避免了 Python 建池开销，仍作为独立批处理、资源隔离和未来沙箱宿主保留。
- PyPy 未在多类负载上稳定超过长驻 CPython，不作为默认后端。
- 任何新优化必须使用相同 `.ojbin`、随机种子、源码和输出摘要，且不得牺牲超时恢复、输入隔离或内存上限。

最终数据和热池/冷启动口径说明见 `benchmark_results/FINAL_RUNNER_REPORT.md`。
