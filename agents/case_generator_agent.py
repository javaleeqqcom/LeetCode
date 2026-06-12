from pathlib import Path
import json
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOllama
from schemas.problem_context import ProblemContext
from tools.solution_struct import SolutionStruct, ComplexityHint
from agents.reference_retriever import ReferenceRetriever

# 预置的默认用例生成器模板（作为 AI 的参考格式）
_DEFAULT_CASE_GENERATOR_TEMPLATE = r'''
def case_generator(scale: int) -> dict:
    """scale 映射到题目规模（如数组长度）"""
    n = max(1, int(round(scale)))
    # 根据题目生成输入参数，格式必须为 {"input": tuple|dict}
    # 示例（元组格式）：
    return {
        "input": (nums, l, r)
    }
'''

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
        # 1. 提取复杂度提示
        complexity: ComplexityHint = problem.solution_struct.complexity_hint
        # 构建分析说明文本
        analysis_str = (
            f"Time complexity: {complexity.time_complexity or 'unknown'}. "
            f"Space complexity: {complexity.space_complexity or 'unknown'}. "
            f"Estimated max n: {complexity.estimated_n_limit or 'unspecified'}. "
            f"Notes: {complexity.notes or ''}"
        )

        # 2. RAG 参考上下文（使用复杂度类型或备注作为查询）
        rag_query = complexity.time_complexity or "general"
        if complexity.notes:
            rag_query += " " + complexity.notes
        rag_context = self.build_rag_context([rag_query])

        # 3. 构造 Prompt（必须与模板要求的变量名完全一致）
        response = self.chain.invoke({
            "question": problem.description,                # 题目描述
            "student_code": problem.solution_struct.source_code,  # 学生代码
            "case_generator_code": _DEFAULT_CASE_GENERATOR_TEMPLATE, # 参考模板
            "analysis": analysis_str,                       # 复杂度分析
            "rag_context": rag_context,                     # RAG 内容
        })
        # 返回生成的用例生成器代码（字符串）
        return response.content