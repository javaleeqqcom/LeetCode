# run_solution.py
from tools.solution_runner import SolutionRunner
from tools.custom_init import *

obj = SolutionRunner("P82_V0.py")
cases = obj.read_test_case("P82q1.txt")
print(cases)
results = obj.run(cases,log_suffix= "_V0")
