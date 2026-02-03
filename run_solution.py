from typing import List, Tuple, Dict, Set, Optional, Any, Union, Callable, Iterable

from tools.solution_runner import SolutionRunner
from P82_V0 import Solution
run = SolutionRunner(Solution)
cases = run.read_test_case("P82q1.txt")
print(cases)
results = run.run(cases,log_suffix= "_V0")
print(results)
