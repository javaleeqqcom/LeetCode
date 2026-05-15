from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

from langchain_core.output_parsers import PydanticOutputParser

# pip install langchain langchain-community
from langchain_community.chat_models import ChatOllama

from schemas.analysis_schema import ProblemAnalysis

class AnalyzeAgent:

    def __init__(self, llm=None):

        self.llm = llm or ChatOllama(
            model="qwen3-coder-30b-q8:latest",
            temperature=0,
        )

        self.parser = PydanticOutputParser(
            pydantic_object=ProblemAnalysis
        )

        prompt_text = Path(
            "prompts/analyze.prompt.md"
        ).read_text(encoding="utf-8")

        self.prompt = ChatPromptTemplate.from_template(
            prompt_text + "\n\n{format_instructions}"
        )

        self.chain = (
            self.prompt
            | self.llm
            | self.parser
        )

    def run(
        self,
        question:str,
        student_code:str,
        language:str,
    )->ProblemAnalysis:

        return self.chain.invoke({
            "question": question,
            "student_code": student_code,
            "language": language,
            "format_instructions":
                self.parser.get_format_instructions(),
        })