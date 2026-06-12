from typing import TypedDict, Optional, List
from schemas.problem_context import ProblemContext
from schemas.analysis_schema import ProblemAnalysis

class AgentState(TypedDict):
    problem: Optional[ProblemContext]
    analysis: Optional[ProblemAnalysis]
    retrieved_case_context: Optional[str]
    retrieved_conversion_context: Optional[str]
    generated_case_code: Optional[str]
    generated_cases: Optional[list]          # List[_CASE]
    brute_force_results: Optional[list]
    evaluation: Optional[dict]