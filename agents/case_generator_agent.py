from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

from langchain_community.chat_models import ChatOllama

from rag.retriever import RAGRetriever


class CaseGeneratorAgent:

    def __init__(self, llm=None):

        self.llm = llm or ChatOllama(
            model="qwen3-coder-30b-q8:latest",
            temperature=0,
        )

        self.retriever = RAGRetriever()

        prompt_text = Path(
            "prompts/case_generator_prompt.md"
        ).read_text(encoding="utf-8")

        self.prompt = ChatPromptTemplate.from_template(
            prompt_text
        )

        self.chain = self.prompt | self.llm

    def build_rag_context(self, rag_queries):

        chunks = []

        for q in rag_queries:
            docs = self.retriever.search(q, topk=2)

            for d in docs:
                chunks.append(d["document"])

        return "\n\n".join(chunks)

    def run(
        self,
        question: str,
        student_code: str,
        language: str,
        analysis,
    ):

        rag_context = self.build_rag_context(
            analysis.rag_queries
        )

        return self.chain.invoke({
            "question": question,
            "student_code": student_code,
            "language": language,
            "analysis": analysis.model_dump_json(indent=2),
            "rag_context": rag_context,
        })