from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from schemas.analysis_schema import ProblemAnalysis
from schemas.problem_context import ProblemContext
from agents.ollama_config import build_chat_ollama


_ROOT = Path(__file__).resolve().parent.parent

class AnalyzeAgent:
    def __init__(self, llm=None):
        self.llm = llm or build_chat_ollama(json_mode=True)
        self.parser = PydanticOutputParser(pydantic_object=ProblemAnalysis)
        prompt_text = (_ROOT / "prompts" / "analyze.prompt.md").read_text(encoding="utf-8")
        self.prompt = ChatPromptTemplate.from_template(
            prompt_text + "\n\n{format_instructions}"
        )
        self.chain = self.prompt | self.llm | self.parser

    def run(self, problem: ProblemContext) -> ProblemAnalysis:
        return self.chain.invoke({
            "question": f"{problem.title}\n\n{problem.description}\n\n约束：{problem.constraints}",
            "language": problem.solution_struct.language.value,
            "student_code": problem.solution_struct.source_code,
            "constraints": problem.constraints,
            "tags": ", ".join(problem.tags),
            # 传递简化的结构信息，不暴露完整代码
            "method_signatures": str(problem.solution_struct.methods),
            "format_instructions": self.parser.get_format_instructions(),
        })
