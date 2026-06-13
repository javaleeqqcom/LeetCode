# agents/case_generator_agent.py
from pathlib import Path
from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOllama
from schemas.problem_context import ProblemContext
from tools.solution_struct import ComplexityHint
from agents.reference_retriever import ReferenceRetriever
from agents.agent_io import AgentIO
from langchain_core.messages import BaseMessage  # 👈 导入正确的基类

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
        """拼接 RAG 检索到的参考样例"""
        refs = self.retriever.retrieve(knowledge_requirements)
        return "\n\n".join([r.to_json() for r in refs])

    def build_prompt(self, problem: ProblemContext)-> List[BaseMessage]:
        """
        构造完整的 Prompt。
        """
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

        return msg
        # 拼接所有消息内容为纯文本
        return "\n\n".join(str(x.content) for x in msg)

    def run(self, problem: ProblemContext, dry_run: bool = False) -> Optional[str]:
        """
        执行 Agent 流程。

        - 若 dry_run=True：只生成 Prompt 并保存/复制到剪贴板，不调用 LLM。
        - 若 dry_run=False：调用 LLM 并返回清洗后的代码字符串。
        """
        prompt_text = self.build_prompt_text(problem)
        idx = AgentIO.next_index(problem.problem_dir)

        # 保存 Prompt 文件
        prompt_path = AgentIO.get_log_dir(problem.problem_dir) / f"AI_prompt_{idx:03d}.log"
        prompt_path.write_text(prompt_text, encoding="utf-8")
        print(f"Prompt已保存: {prompt_path}")

        if dry_run:
            # 复制到剪贴板
            if AgentIO.copy_to_clipboard(prompt_text):
                print("✅ Prompt 已复制到剪贴板，可直接粘贴到 Ollama 对话框。")
            else:
                print("⚠️ 剪贴板复制失败，请手动打开上面的文件复制内容。")
            return None

        # 正式调用 LLM
        try:
            response = self.llm.invoke(
                self.prompt.format_messages(
                    question=problem.description,
                    student_code=problem.solution_struct.source_code,
                    case_generator_code=_DEFAULT_CASE_GENERATOR_TEMPLATE,
                    analysis="...",          # 实际会被格式化为 analysis 变量，此处简化
                    rag_context="..."
                )
            )
            assert isinstance(response.content, str), "LLM 返回非字符串"
            code = AgentIO.clean_llm_code(response.content)
        except Exception as e:
            raise RuntimeError(
                f"""LLM调用失败
请打开以下文件手动提问：
{prompt_path}
原始错误：{e}"""
            )

        # 保存生成的代码
        code_path = AgentIO.get_auto_dir(problem.problem_dir) / f"case_generator_{idx:03d}.py"
        code_path.write_text(code, encoding="utf-8")
        print(f"代码已保存: {code_path}")

        return code