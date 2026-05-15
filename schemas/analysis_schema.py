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

    rag_queries: List[str]

    corrected_code: Optional[str] = None

    correction_reason: Optional[str] = None