from pathlib import Path
import json
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOllama
from schemas.problem_context import ProblemContext
from tools.solution_struct import SolutionStruct, ComplexityHint
from agents.reference_retriever import ReferenceRetriever
from agents.agent_io import AgentIO
from threading import Thread

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

        # 单独构造向AI提问的模板（必须与模板要求的变量名完全一致）
        msg = self.prompt.format_messages(
            question=problem.description,
            student_code=problem.solution_struct.source_code,
            case_generator_code=_DEFAULT_CASE_GENERATOR_TEMPLATE,
            analysis=analysis_str,
            rag_context=rag_context,
        )

        # 用于备份提问的台词
        prompt_text = "\n\n".join( str(x.content) for x in msg )
        idx = AgentIO.next_index(
            problem.problem_dir
        )
        # 待改进，可以用子线程 Thread 避免外存IO等待
        prompt_path = self.save_prompt(
            problem,
            prompt_text,
            idx
        )
        print(f"Prompt已保存: {prompt_path}")

        # 3. 向 LLM 提问，在线等待返回
        try:
            response = self.llm.invoke(msg)
            assert isinstance(response.content,str),"CaseGeneratorAgent.llm.response not valid string."
            code = AgentIO.clean_llm_code( response.content )

        except Exception as e:

            raise RuntimeError(
                f"""
LLM调用失败
请打开以下文件手动提问：
{prompt_path}
原始错误：
{e}
"""
            )

        code_path = self.save_generated_code( problem,  code, idx)
        print( f"代码已保存: {code_path}")
        # 返回生成的用例生成器代码（字符串）
        return response.content
    
    def save_prompt(
    self,
    problem: ProblemContext,
    prompt_text:str,
    idx:int,
    )->Path:

        log_dir = AgentIO.get_log_dir(
            problem.problem_dir
        )

        path = log_dir / f"AI_prompt_{idx:03d}.log"

        path.write_text(
            prompt_text,
            encoding="utf-8"
        )

        return path
    
    def save_generated_code(
    self,
    problem: ProblemContext,
    code:str,
    idx:int,
    )->Path:

        auto_dir = AgentIO.get_auto_dir(
            problem.problem_dir
        )

        path = auto_dir / (
            f"case_generator_{idx:03d}.py"
        )

        path.write_text(
            code,
            encoding="utf-8"
        )

        return path