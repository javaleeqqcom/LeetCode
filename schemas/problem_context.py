# schemas/problem_context.py

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

from tools.solution_struct import SolutionStruct

@dataclass
class ProblemContext:
    title: str
    description: str

    examples: List[Dict[str, Any]]
    constraints: str
    tags: List[str]

    solution_struct: SolutionStruct

    # 新增
    problem_dir: Path