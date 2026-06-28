if __name__ == "__main__":
    DRY_RUN = True   # 调试阶段设为 True，避免浪费 token

    import os, sys, time
    from pathlib import Path
    from tools.solution_runner import SolutionRunner
    from tools.solution_struct import SolutionStruct, ComplexityHint
    from tools.cases_generator import build_test_cases, sample_lognormal_scales, quantize_scales

    # Agent 层组件
    from agents.complexity_analyzer import ComplexityAnalyzer
    from agents.case_generator_agent import CaseGeneratorAgent
    from schemas.problem_context import ProblemContext

    # ================= 题目目录 =================
    problem_dir = Path(r"Question\Q1. Maximum Total Sum of K Selected Elements©leetcode")
    sys.path.insert(1, str(problem_dir))

    # ================= 1. 暴力解法结构提取 =================
    brute_runner = SolutionRunner(problem_dir / "bt.py")
    brute_struct = brute_runner.build_solution_struct()

    # ================= 2. 静态复杂度分析 =================
    analyzer = ComplexityAnalyzer()
    brute_struct.complexity_hint = analyzer.analyze(brute_struct)

    # ================= 3. 构建 ProblemContext =================
    with open(problem_dir / "题目.txt", "r", encoding="utf-8") as f:
        description = f.read()

    context = ProblemContext(
        title="Count of Sub-Multisets With Bounded Sum",
        description=description,
        examples=[],
        constraints="...",
        tags=["dp","math"],
        solution_struct=brute_struct,

        problem_dir=problem_dir,
    )

    # ================= 4. Agent 自动生成测试用例生成器 =================
    case_gen_agent = CaseGeneratorAgent()
    if DRY_RUN:
        # 仅生成 Prompt 并复制，不调用 LLM
        case_gen_agent.run(context, dry_run=True)
        print("已生成 Prompt 并复制到剪贴板/日志。请手动提问后将代码放入 auto/ 目录，然后重新运行本脚本（设置 DRY_RUN=False）。")
        exit(0)
    else:
        generated_code = case_gen_agent.run(context)
        # ... 后续执行 generated_code ...

    # 动态执行生成的代码，获取 case_generator 函数
    local_ns = {}
    try:
        exec(generated_code, {"__builtins__": __builtins__}, local_ns)
        case_generator = local_ns["case_generator"]
    except Exception as e:
        # 失败时保存代码供人工调试
        fallback_path = problem_dir / "generated_case_generator.py"
        with open(fallback_path, "w", encoding="utf-8") as f:
            f.write(generated_code)
        print(f"⚠️ Agent 生成的代码执行失败：{e}\n已保存至 {fallback_path}，请检查后手动运行。")
        exit(1)

    # ================= 5. 生成测试用例 =================
    size_list = sample_lognormal_scales(1000, mean_scale=10) + 1
    scales = quantize_scales(size_list, min_scale=1, max_scale=10**5)
    cases = build_test_cases(case_generator, scales)
    print(f"✅ 自动生成 {len(cases)} 个测试用例")

    # 保存用例（覆盖旧文件）
    cases_path = brute_runner.auto_path_cases()
    brute_runner.save_test_cases(cases, cases_path)

    # ================= 6. 运行暴力算法生成 expected =================
    print("🚀 运行暴力算法获取预期输出...")
    raw_results = brute_runner.run(cases, thread=1)
    expected_cases = brute_runner.get_expected_cases(raw_results)
    brute_runner.save_test_cases(expected_cases, cases_path)
    print(f"✅ 最终有效用例数：{len(expected_cases)}")

    # ================= 7. 运行优化算法 =================
    improved_runner = SolutionRunner(problem_dir / "V2.12.sim.py")
    print("=== 测试改进算法 ===")
    begin = time.time()
    results = improved_runner.run(
        expected_cases,
        thread=1,
        timeout_s=60,
        summary=True,
        early_stop=10
    )
    end = time.time()
    print(f"⏱️ 总耗时：{end - begin:.6f}s")