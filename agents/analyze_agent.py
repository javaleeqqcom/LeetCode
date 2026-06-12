from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_community.chat_models import ChatOllama
from schemas.analysis_schema import ProblemAnalysis
from schemas.problem_context import ProblemContext

class AnalyzeAgent:
    def __init__(self, llm=None):
        self.llm = llm or ChatOllama(model="qwen3-coder-30b-q8:latest", temperature=0)
        self.parser = PydanticOutputParser(pydantic_object=ProblemAnalysis)
        prompt_text = Path("prompts/analyze.prompt.md").read_text(encoding="utf-8")
        self.prompt = ChatPromptTemplate.from_template(
            prompt_text + "\n\n{format_instructions}"
        )
        self.chain = self.prompt | self.llm | self.parser

    def run(self, problem: ProblemContext) -> ProblemAnalysis:
        return self.chain.invoke({
            "title": problem.title,
            "description": problem.description,
            "constraints": problem.constraints,
            "tags": ", ".join(problem.tags),
            # 传递简化的结构信息，不暴露完整代码
            "method_signatures": str(problem.solution_struct.methods),
            "format_instructions": self.parser.get_format_instructions(),
        })