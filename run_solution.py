# run_solution.py
from tools.solution_runner import SolutionRunner
from tools.custom_init import *

obj = SolutionRunner("P3129_V6.py")
cases = obj.read_test_case("P3129_bt0.json")
# print(cases)
results = obj.run(cases, only_log_wrong=True) # only_log_wrong 失效

right = 0
for case in results:
    if case['expected'] != case['output']:
        print(f"wrong: {case}")
    else:
        right += 1
print(f"right/total: {right}/{len(results)}")


