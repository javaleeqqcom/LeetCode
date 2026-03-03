# run_solution.py
from tools.solution_runner import SolutionRunner
from tools.custom_init import *

obj = SolutionRunner("1545_V1.py")
cases = obj.read_test_case("1545_V0_bt.json")
print(cases)
results = obj.run(cases,log_suffix= "_V0")
