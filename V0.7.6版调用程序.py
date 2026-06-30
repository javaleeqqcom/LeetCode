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


    cases_path = brute_runner.auto_path_cases()
    if cases_path.exists():
        print(f"从文件中读取测试用例：{cases_path}")
        cases = brute_runner.read_test_case(cases_path)
    else:
        # ================= 3. 构建 ProblemContext =================
        with open(problem_dir / "题目.txt", "r", encoding="utf-8") as f:
            description = f.read()

        context = ProblemContext(
            title="Count of Sub-Multisets With Bounded Sum",
            description=description,
            examples=[],
            constraints="...",
            tags=["dp", "math"],
            solution_struct=brute_struct,
            problem_dir=problem_dir,
        )

        # ================= 4. Agent 生成测试用例生成器 =================
        case_gen_agent = CaseGeneratorAgent(context)            # 修改：构造时传入 context
        generated_code = case_gen_agent.run(dry_run=DRY_RUN)    # 修改：不再需要传入 context，统一返回代码

        if generated_code is None:
            print("❌ 未能获得 case_generator 代码，程序退出。")
            sys.exit(1)

        # 动态执行生成的代码，获取 case_generator 函数
        exec_globals = {"__builtins__": __builtins__}
        try:
            exec(generated_code, exec_globals)
            case_generator = exec_globals["case_generator"]
        except Exception as e:
            fallback_path = problem_dir / "generated_case_generator.py"
            with open(fallback_path, "w", encoding="utf-8") as f:
                f.write(generated_code)
            print(f"⚠️ Agent 生成的代码执行失败：{e}\n已保存至 {fallback_path}，请检查后手动运行。")
            sys.exit(1)

        # ================= 5. 生成测试用例 =================
        size_list = sample_lognormal_scales(100000, mean_scale=100) + 1
        scales = quantize_scales(size_list, min_scale=1, max_scale=1500)

        cases = build_test_cases(case_generator, scales)
        print(f"✅ 自动生成 {len(cases)} 个测试用例")

        # 先保存不含 expected 的结果
        brute_runner.save_test_cases(cases, cases_path)

    # ================= 6. 运行暴力算法生成 expected =================
    if all('expected' in case for case in cases):
        expected_cases = cases
        print(f"✅ 读取到有效用例数：{len(expected_cases)}")
    else:
        print("🚀 运行暴力算法获取预期输出...")
        raw_results = brute_runner.run(cases, thread=12)
        expected_cases = brute_runner.get_expected_cases(raw_results)
        brute_runner.save_test_cases(expected_cases, cases_path)
        print(f"✅ 最终有效用例数：{len(expected_cases)}")
        
    # ================= 7. 运行优化算法 =================
    improved_runner = SolutionRunner(problem_dir / "V2.2.py")
    print("=== 测试改进算法 ===")
    begin = time.time()
    results = improved_runner.run(
        expected_cases,
        thread=12,
        timeout_s=2,
        summary=True,
        early_stop=10
    )
    end = time.time()
    print(f"⏱️ 总耗时：{end - begin:.6f}s")