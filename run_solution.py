from tools.solution_runner import *
from P3637 import Solution
run = SolutionRunner(Solution)
cases = run.read_test_case("P3637.txt")
print(cases)
results = run.run(cases)
print(results)
