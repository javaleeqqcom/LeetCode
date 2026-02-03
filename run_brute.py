from tools.solution_runner import SolutionRunner
brute = SolutionRunner("brute.py")
ask_file = None
brute.get_ask_for_cases(ask_file) # 执行后自动生成用于生成适用于 brute 的测试用例的 token，输出到 ask_file 中，若 ask_file 为空则取与 solution_file 同名的 txt 文件中。重名自动覆盖。考虑到暴力算法消耗大，可以尽量采用 Cython 进行优化。

# 此处插入 cases_generation 函数代码，出于方便，一般不另存为 python 文件，直接写在这里
def cases_generation(...) -> List[Union[Tuple,Dict]]: # 告诉 AI-agent 优先生成 List[Tuple] 格式，除非参数名容易互相混淆，或者有其他特殊需求。
    ……

# 保存测试样例为 {与brute的py同名的}.json
brute.save_cases(cases_generation,...) # 其中 ... 是 cases_generation 函数的参数，供调整规模等
# 也可以采用
caces = cases_generation(...)
brute.save_cases(cases) # 因为 cases 不可能是 function，因此可以智能区分。注意 save_cases 会自动运行 self.method （也就是暴力算法函数）将结果加到 cases 的 expected 中。

# 之后另一个程序写改进算法，则可以引用 json 测试样例进行对比测试。