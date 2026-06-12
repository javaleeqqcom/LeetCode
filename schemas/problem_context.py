from dataclasses import dataclass, field
from typing import List, Dict, Any
from tools.solution_struct import SolutionStruct

@dataclass
class ProblemContext:
    title: str
    description: str
    examples: List[Dict[str, Any]]   # 题面示例
    constraints: str                 # 约束描述（如 n <= 10^5）
    tags: List[str]                  # 算法标签
    solution_struct: SolutionStruct   # 学生代码的结构化描述