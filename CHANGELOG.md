# Changelog

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
