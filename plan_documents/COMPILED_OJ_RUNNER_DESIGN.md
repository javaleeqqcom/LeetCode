# C/C++ OJ 编译与多进程执行设计

## 目标与依据

第一阶段覆盖 LeetCode 最常见的无状态算法接口。测试 fixture 对齐了官方题目中的
[Two Sum](https://leetcode.com/problems/two-sum/)、
[Binary Search](https://leetcode.com/problems/binary-search/)、
[Sort an Array](https://leetcode.com/problems/sort-an-array/) 和
[Longest Common Subsequence](https://leetcode.com/problems/longest-common-subsequence/)
输入输出形态，并补充筛法、向量校验和与矩阵运算作为性能负载。

核心原则：学生源码只编译一次；每个 Worker 是独立原生进程，在一个循环中执行
多个样例；1～16 个 Worker 共享只读内存映射，不复制整套 JSON 数据。

```text
solution.c/.cpp
      │  解析受限接口 + 生成 adapter
      ▼
MSVC/GCC/Clang ── cache key ──► oj_cpp_worker.exe
                                      │
oj_native_manager.exe ─ Job Object ───┼── Worker 0: [start, stop)
                                      ├── Worker 1: [start, stop)
.ojbin v1/v2 read-only mmap ──────────┴── Worker N: [start, stop)
```

## C++ 支持范围

- 恰好一个 `class Solution`；通过 `main_method` 选择一个公有成员方法。
- 参数和返回值：`int`/长整数/无符号整数、`float`/`double`、`bool`、
  `string`、`vector<T>` 和嵌套 `vector`。
- 同时接受 JSON 数组位置参数与按 C++ 参数名匹配的 JSON 对象。
- Harness 注入 LeetCode 常用 STL 头文件，因此 standard 源码不接受预处理指令，
  也不允许自定义 `main()`。
- 多个辅助/公有方法可以存在，但第一阶段一次只选择和调用一个目标方法；需要
  构造器与操作序列的设计题暂缓。

## C 支持范围

第一阶段支持一个全局纯标量函数，使用与 C++ 相同的 JSON 标量参数和返回值。
C 数组并不与 JSON 数组一一对应：LeetCode C ABI 会额外加入 `numsSize`、
`returnSize`、二维 `columnSizes`，并涉及返回内存由谁释放。因此指针数组、字符串、
二维数组和动态返回值必须在后续引入显式 ABI schema 后实现，当前不会猜测长度或
静默泄漏内存。

## 编译与缓存

Windows 默认优先发现 MSVC x64 工具链，也允许显式传入 GCC/Clang。缓存键覆盖：

- 学生源码与所选方法 ABI；
- 生成 Harness 版本；
- `.ojbin`/JSON Worker Runtime 与 nlohmann/json 头文件；
- 编译器绝对路径、版本和优化参数。

编译输出位于忽略的 `build/cpp_runner/cache/<sha256>/`。编译失败、超时或 ABI
不受支持会抛出明确异常，不会执行旧制品。墙钟性能报告不混入编译时间，但单独
记录首次编译耗时和缓存命中状态。

## 数据与结果协议

- C/C++ 与 Python 使用相同 `CaseStoreWriter` 和 `.ojbin`；无需生成语言专属用例。
- v2 正确结果直接 XOR 索引中的预计算摘要。
- 错误、异常或没有 `expected` 时，Worker 回传最小 fallback 记录，由 Python
  使用 `canonical-json-blake2b-128-v1` 计算兼容摘要。
- Worker 汇总正确/错误/异常数、解码/计算时间和 RSS；父进程验证完成数量。

## 调度与性能结论

当前管理器采用静态等数量连续分片。它适合同规模独立样例，且没有 Python Queue
和解释器开销；对强烈不均匀的样例，后续可加入共享原子 chunk 计数器。

短批次不应盲目增加进程：10k 微任务通常 1 个原生进程最佳，多开进程的启动成本
高于计算。8192 个 `400×400` LCS 重负载中，1/4/8/16 进程中位数为
`1.158/0.378/0.252/0.234s`，加速比为 `1.00/3.06/4.60/4.94×`。因此调用方应按
预计单批计算量选择 Worker，而不是固定开满 16。

## 安全边界

已实现 Job Object 活动进程数、单进程提交内存、整批超时和管理器关闭时终止全部
Worker。源码格式检查用于保证 ABI，不是安全边界；编译器和原生代码仍可能读取
主机文件或访问网络。完成受限令牌/AppContainer、仅题目目录可写 ACL、禁网和
编译制品审计之前，不能把本实现称为完整不可信代码沙箱。
