from pathlib import Path
import json
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOllama
from schemas.problem_context import ProblemContext
from tools.solution_struct import SolutionStruct
from agents.reference_retriever import ReferenceRetriever

class CaseGeneratorAgent:
    def __init__(self, llm=None):
        self.llm = llm or ChatOllama(model="qwen3-coder-30b-q8:latest", temperature=0)
        self.retriever = ReferenceRetriever()
        prompt_text = Path("prompts/case_generator.prompt.md").read_text(encoding="utf-8")
        self.prompt = ChatPromptTemplate.from_template(prompt_text)
        self.chain = self.prompt | self.llm

    def build_rag_context(self, knowledge_requirements: List[str]) -> str:
        refs = self.retriever.retrieve(knowledge_requirements)
        # 将参考结构序列化为文本
        ref_str = "\n\n".join([r.to_json() for r in refs])
        return ref_str

    def run(self, problem: ProblemContext) -> str:
        # 1. 获取复杂度提示（来自 SolutionStruct 或外部分析器）
        complexity = problem.solution_struct.complexity_hint
        # 2. RAG 参考
        knowledge = problem.solution_struct.complexity_hint.notes or ""
        # 实际知识需求可由 AnalyzeAgent 提供，这里简化从 complexity 获取
        rag_context = self.build_rag_context([complexity.time_complexity or "basic"])

        # 3. 构造 Prompt
        response = self.chain.invoke({
            "title": problem.title,
            "description": problem.description,
            "constraints": problem.constraints,
            "solution_json": problem.solution_struct.to_json(),
            "complexity": complexity,
            "rag_context": rag_context,
        })
        # 假设 LLM 直接返回符合框架格式的 JSON 数组（test_cases）
        return response.content   # 返回生成的用例列表（字符串）