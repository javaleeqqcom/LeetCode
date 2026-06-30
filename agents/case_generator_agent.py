# agents/case_generator_agent.py
from pathlib import Path
from typing import List, Optional
import time
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import BaseMessage
from schemas.problem_context import ProblemContext
from tools.solution_struct import ComplexityHint
from agents.agent_io import AgentIO
from rag.retriever import RAGRetriever # 直接使用 RAGRetriever，不再使用 ReferenceRetriever

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
    def __init__(self, problem: ProblemContext, llm=None):
        self.problem = problem
        self.llm = llm or ChatOllama(model="qwen3-coder-30b-q8:latest", temperature=0)
        
        self.retriever = RAGRetriever()
        
        prompt_text = Path("prompts/case_generator.prompt.md").read_text(encoding="utf-8")
        self.prompt = ChatPromptTemplate.from_template(prompt_text)
        self.chain = self.prompt | self.llm

    def build_rag_context(self, query: str) -> str:
        """查询 case_generator 知识库，返回格式化文本上下文"""
        try:
            return self.retriever.build_context(
                query=query,
                collection_name="case_generator",
                topk=5
            )
        except Exception as e:
            print(f"RAG 检索失败（将使用空上下文）: {e}")
            return ""

    def build_prompt(self) -> List[BaseMessage]:
        complexity: ComplexityHint = self.problem.solution_struct.complexity_hint
        analysis_str = (
            f"Time complexity: {complexity.time_complexity or 'unknown'}. "
            f"Space complexity: {complexity.space_complexity or 'unknown'}. "
            f"Estimated max n: {complexity.estimated_n_limit or 'unspecified'}. "
            f"Notes: {complexity.notes or ''}"
        )

        # 构造更丰富的查询（标题 + 描述摘要 + 标签 + 复杂度备注）
        query_parts = []
        if self.problem.title:
            query_parts.append(self.problem.title)
        if self.problem.description:
            query_parts.append(self.problem.description[:200])
        if self.problem.tags:
            query_parts.append(" ".join(self.problem.tags))
        if complexity.notes:
            query_parts.append(complexity.notes)
        query = "\n".join(query_parts)

        rag_context = self.build_rag_context(query)   # 现在返回的是文本上下文

        msg = self.prompt.format_messages(
            question=self.problem.description,
            student_code=self.problem.solution_struct.source_code,
            case_generator_code=_DEFAULT_CASE_GENERATOR_TEMPLATE,
            analysis=analysis_str,
            rag_context=rag_context,
        )
        return msg

    def _wait_for_clipboard_code(self, max_attempts: int = 10, delay: float = 2.0) -> Optional[str]:
        """
        循环读取剪贴板，直到获取到有效代码或超过尝试次数。
        每次提示用户复制代码后按 Enter，然后从剪贴板读取。
        返回清洗后的代码字符串，或 None 表示失败。
        """
        print("\n" + "=" * 60)
        print("📋 请将生成的 case_generator 代码复制到剪贴板，然后按 Enter 继续。")
        print("   若剪贴板读取失败，可再次复制后按 Enter 重试。")
        print("=" * 60)

        for attempt in range(1, max_attempts + 1):
            input(f"⏳ 第 {attempt}/{max_attempts} 次尝试：按 Enter 读取剪贴板...")
            raw = AgentIO.paste_from_clipboard()
            if raw:
                code = AgentIO.clean_llm_code(raw)
                if code and "def case_generator" in code:
                    # 自动修复缺失 import
                    code = AgentIO.auto_fix_imports(code)
                    # 沙箱验证
                    valid, err_msg = AgentIO.validate_case_generator(code)
                    if valid:
                        print("✅ 代码修复并验证通过。")
                        return code
                    else:
                        print(f"❌ 代码验证失败：{err_msg}")
                        print("   请修改代码后重新复制到剪贴板，或按 Enter 重试。")
                        # 不返回，进入下一次循环
                else:
                    print("⚠️ 剪贴板内容中未找到 case_generator 函数定义，请检查后重试。")
            else:
                print("❌ 剪贴板为空或读取失败。")
            if attempt < max_attempts:
                print(f"将在 {delay} 秒后重试...")
                time.sleep(delay)

        print("❌ 超过最大重试次数，未能获取有效代码。")
        return None

    def run(self, dry_run: bool = False) -> Optional[str]:
        """
        执行 Agent 流程。
        - dry_run=True：生成 Prompt 后，进入半监督模式，等待用户从剪贴板提供代码。
        - dry_run=False：调用 LLM 生成代码。
        无论哪种模式，成功时返回清洗后的代码字符串；失败返回 None。
        """
        messages = self.build_prompt()
        idx = AgentIO.next_index(self.problem.problem_dir)

        # 保存 Prompt 日志
        prompt_text = "\n\n".join(str(m.content) for m in messages)
        prompt_path = AgentIO.get_log_dir(self.problem.problem_dir) / f"AI_prompt_{idx:03d}.log"
        prompt_path.write_text(prompt_text, encoding="utf-8")
        print(f"📝 Prompt 已保存: {prompt_path}")

        if dry_run:
            # 尝试复制 Prompt 到剪贴板，方便用户粘贴到 LLM 对话框
            AgentIO.send_messages_to_clipboard(messages, self.problem.problem_dir)
            # 进入半监督等待模式
            code = self._wait_for_clipboard_code()
            if code is None:
                print("❌ 未能获取代码，流程终止。")
                return None
        else:
            # 正式调用 LLM
            print("🤖 正在调用 LLM 生成测试用例生成器...")
            try:
                response = self.llm.invoke(messages)
                assert isinstance(response.content, str), "LLM 返回非字符串"
                code = AgentIO.clean_llm_code(response.content)
                code = AgentIO.auto_fix_imports(code)
                # 全自动模式也做验证，失败则抛出明确的 RuntimeError
                valid, err_msg = AgentIO.validate_case_generator(code)
                if not valid:
                    raise RuntimeError(
                        f"LLM 生成的代码验证失败：{err_msg}\n"
                        f"请手动检查或使用 dry_run 模式。\n"
                        f"Prompt 已保存至: {prompt_path}"
                    )
            except Exception as e:
                raise RuntimeError(
                    f"LLM调用或代码验证失败。\n"
                    f"原始错误: {e}\n"
                    f"请检查日志: {prompt_path}"
                )

        # 保存生成的代码
        code_path = AgentIO.get_auto_dir(self.problem.problem_dir) / f"case_generator_{idx:03d}.py"
        code_path.write_text(code, encoding="utf-8")
        print(f"💾 代码已保存: {code_path}")
        return code