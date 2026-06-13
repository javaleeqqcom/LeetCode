# agents/case_generator_agent.py
from pathlib import Path
from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import BaseMessage
from schemas.problem_context import ProblemContext
from tools.solution_struct import ComplexityHint
from agents.reference_retriever import ReferenceRetriever
from agents.agent_io import AgentIO

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
        self.llm = llm or ChatOllama(
            model="qwen3-coder-30b-q8:latest",
            temperature=0
        )
        self.retriever = ReferenceRetriever()
        prompt_text = Path("prompts/case_generator.prompt.md").read_text(encoding="utf-8")
        self.prompt = ChatPromptTemplate.from_template(prompt_text)
        self.chain = self.prompt | self.llm

    def build_rag_context(self, knowledge_requirements: List[str]) -> str:
        """拼接 RAG 检索到的参考样例，异常时返回空字符串"""
        try:
            refs = self.retriever.retrieve(knowledge_requirements)
            return "\n\n".join([r.to_json() for r in refs])
        except Exception as e:
            print(f"RAG 检索失败（将使用空上下文）: {e}")
            return ""

    def build_prompt(self, problem: ProblemContext) -> List[BaseMessage]:
        """
        构造完整的 Prompt，返回标准 BaseMessage 列表。
        """
        complexity: ComplexityHint = problem.solution_struct.complexity_hint
        analysis_str = (
            f"Time complexity: {complexity.time_complexity or 'unknown'}. "
            f"Space complexity: {complexity.space_complexity or 'unknown'}. "
            f"Estimated max n: {complexity.estimated_n_limit or 'unspecified'}. "
            f"Notes: {complexity.notes or ''}"
        )
        # RAG 查询关键字
        rag_query = complexity.time_complexity or "general"
        if complexity.notes:
            rag_query += " " + complexity.notes
        rag_context = self.build_rag_context([rag_query])

        msg = self.prompt.format_messages(
            question=problem.description,
            student_code=problem.solution_struct.source_code,
            case_generator_code=_DEFAULT_CASE_GENERATOR_TEMPLATE,
            analysis=analysis_str,
            rag_context=rag_context,
        )
        return msg

    def run(self, problem: ProblemContext, dry_run: bool = False) -> Optional[str]:
        """
        执行 Agent 流程。

        - dry_run=True：只生成 Prompt 并复制到剪贴板/日志，不调用 LLM。
        - dry_run=False：调用 LLM 并返回清洗后的代码字符串。
        """
        messages = self.build_prompt(problem)
        idx = AgentIO.next_index(problem.problem_dir)

        # 保存完整的 Prompt 文本作为调试日志
        prompt_text = "\n\n".join(str(m.content) for m in messages)
        prompt_path = AgentIO.get_log_dir(problem.problem_dir) / f"AI_prompt_{idx:03d}.log"
        prompt_path.write_text(prompt_text, encoding="utf-8")
        print(f"Prompt已保存: {prompt_path}")

        if dry_run:
            # 尝试复制到剪贴板，失败则保存为临时日志
            success = AgentIO.send_messages_to_clipboard(messages, problem.problem_dir)
            if success:
                print("✅ Prompt 已复制到剪贴板，可直接粘贴到 Ollama 对话框。")
            else:
                print(f"⚠️ 复制失败，Prompt 已保存至 {prompt_path}，请手动复制。")
            # return None

            # 开一个 thread 
            # 输入内容作为 case_generator.py
            # 或者输入空按Enter，从剪贴板读取
            # AgentIO.paste_from_clipboard()

        # 正式调用 LLM
        try:
            response = self.llm.invoke(messages)
            assert isinstance(response.content, str), "LLM 返回非字符串"
            code = AgentIO.clean_llm_code(response.content)
        except Exception as e:
            raise RuntimeError(
                f"LLM调用失败，请打开手动提问文件：\n{prompt_path}\n原始错误：{e}"
            )

        # 保存生成的代码
        code_path = AgentIO.get_auto_dir(problem.problem_dir) / f"case_generator_{idx:03d}.py"
        code_path.write_text(code, encoding="utf-8")
        print(f"代码已保存: {code_path}")
        return code
    