from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class ScaleConfig(BaseModel):
    num: int = 1000
    mean_scale: float = 10
    second_moment: float = 1000
    distribution: str = "lognormal"


class ComplexityInfo(BaseModel):
    time_complexity: str
    space_complexity: str
    bottleneck: str


class ProblemAnalysis(BaseModel):

    language: str

    main_function: str

    function_type: str
    # unique_call / multi_call

    input_style: str
    # args / kwargs

    need_conversion: bool

    custom_types: List[str] = []

    complexity: ComplexityInfo

    scale_config: ScaleConfig

    test_strategy: List[str]

    edge_cases: List[str]

    stress_patterns: List[str]

    algorithm_type: str
    difficulty: str
    # rag_queries: List[str]需将 rag_queries 替换为 knowledge_requirements
    knowledge_requirements: List[str] = []   # 不再暴露 rag_queries
    notes: Optional[str] = None

    corrected_code: Optional[str] = None

    correction_reason: Optional[str] = None