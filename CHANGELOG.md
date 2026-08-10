# Changelog

## 0.11.0 - 2026-08-10

- 为长驻 CPython 与编译型 C/C++ 执行器增加 `workers="auto"`。
- 综合 CPU、可用内存、样例数量/体积、程序静态特征与单进程代表样例探针选择 1～16 个进程。
- 增加本机校准器，生成带机器指纹的启动开销与并行效率档案。
- TLE 探针固定降级到单进程；Python 记录超时结果，C++ 由 Job Object 终止失控批次。
- 补充 Visual Studio Preview 的 MSVC/vcvars 自动发现。

## 0.8.0 - 2026-08-09

- 修复随机样例生成、结果比较、输入隔离、多进程结果收集和 TLE Worker 替换。
- 修复 Agent/RAG 配置、检索与生成器验证流程，并增加本地 Ollama/RAG 探测脚本。
- 新增 mmap `.ojbin` 样例存储和长驻 CPython/PyPy Worker 后端。
- 新增 Windows C++ Job Object 进程管理器，支持进程数、内存和批次超时限制。
- 完成 1/2/4/6/8/12/16 进程经典算法、后端和 100 万样例基准。
- 重新组织 `runtime/`、`native_runner/`、`tests/`、`benchmark_results/` 和设计文档。

## 0.7.7

- 合并 RAG 数据库路径并修复 CaseGeneratorAgent 检索。
- 改进旧 SolutionRunner 多进程和 TLE 处理。
