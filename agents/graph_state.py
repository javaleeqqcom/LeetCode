from typing import TypedDict, Optional
from schemas.analysis_schema import ProblemAnalysis


class AgentState(TypedDict):

    question_text: str

    student_code: str

    file_suffix: str

    analysis: Optional[ProblemAnalysis]

    retrieved_context: Optional[list]

    case_generator_code: Optional[str]

    conversion_code: Optional[str]