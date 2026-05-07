try: from tools.args_parser import *; DEBUG=True
except: DEBUG = False

if __name__ == "__main__":
    import os,sys
    print(f"当前工作目录：{os.getcwd()}")
        
    # ------------ 三选一进行调用来测试 -------------------
    from tools.solution_runner import SolutionRunner
    from typing import List, Union, Tuple, Dict, Any
    # 导入 Path 库
    from pathlib import Path
    import numpy as np

    问题目录 = Path(r"Question\3660. Jump Game IX")
    sys.path.insert(1, str(问题目录))
    from bt import Solution


    # 初始化暴力解法运行器
    暴力算法 = SolutionRunner(问题目录 / "bt.py")

    attached_attentions = [
        "请先修复暴力算法并给出样例生成器"
    ]

    测试样例提问_file = 暴力算法.relPath/"测试样例提问.txt"
    if not 测试样例提问_file.exists():
        prompt_str = 暴力算法.get_cases_generator("题目.txt",attached_attentions = attached_attentions) # 会自动加相对路径
        with open(测试样例提问_file,"w",encoding="utf-8") as fp:
            fp.write(prompt_str)
        print("等待测试样例提问完成！")
        exit(0)


    cases_path = 暴力算法.auto_path_cases()
    if cases_path.exists():
        print(f"从文件中读取测试用例：{cases_path}")
        cases = 暴力算法.read_test_case(cases_path)
    else:
        from test_cases_generator import test_cases_generator
        
        cases = test_cases_generator(1000, max_n = 100)
        # print(cases[0])
        # print(cases[10])

        # 多线程测试
        import time
        bg = time.time()
        cases12 = 暴力算法.run(cases,thread=12)
        end = time.time()
        t12 = end -bg
        print(f"多线程测试时间：{t12:.3f}s")
        
        bg = time.time()
        cases1 = 暴力算法.run(cases,thread=1)
        end = time.time()
        t1 = end -bg
        print(f"单线程测试时间：{t1:.3f}s")
        print(f"加速比：{t1/t12:.3f}")

        exit(0)

        print("cases num:",len(cases))

        if len(cases) == 0:
            raise ValueError("没有生成测试用例！")
        if isinstance(cases[0],dict):
            cases = 暴力算法.run(cases,thread=12)
            cases = 暴力算法.get_expected_cases(cases)
            print(cases)
            暴力算法.save_test_cases(cases , cases_path)

    # print("expected_results[0]=", cases[0])
    print(f"暴力算法 是否有 custom_caller ：{暴力算法.has_custom_caller}")

    改进算法 = SolutionRunner(问题目录 / "V4.1.py")

    # 多线程
    print("=== 多线程 ===")
    print(f"改进算法 是否有 custom_caller ：{改进算法.has_custom_caller}")
    results_multi = 改进算法.run(cases, thread=1, timeout_s=60,summary=True)
