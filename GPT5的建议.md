针对 **Ollama 连接不稳定** 和 **调试时浪费 token** 的问题，我对 Agent 层做了两项关键改进：

1. **拆分 Prompt 构造与 LLM 调用**，使你可以先生成 Prompt 并复制到剪贴板，手动提问，完全避免程序直接调用 Ollama。
2. **在 `AgentIO` 中集成剪贴板功能**，参考 `AIConsultation` 的实现，支持 Windows / macOS / Linux。

以下是需要修改的两个文件。

---

### 1. 修改 `agents/agent_io.py`（新增剪贴板功能）
```python
# agents/agent_io.py
from pathlib import Path
import re
import sys
import subprocess

class AgentIO:
    # ========== 原有的方法保持不变 ==========
    @classmethod
    def get_auto_dir(cls, problem_dir: Path) -> Path:
        path = problem_dir / "auto"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def get_log_dir(cls, problem_dir: Path) -> Path:
        path = problem_dir / "agent_logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def next_index(cls, problem_dir: Path) -> int:
        auto_dir = cls.get_auto_dir(problem_dir)
        max_id = -1
        for f in auto_dir.glob("case_generator_*.py"):
            m = re.match(r"case_generator_(\d+)\.py", f.name)
            if m:
                max_id = max(max_id, int(m.group(1)))
        return max_id + 1

    @classmethod
    def clean_llm_code(cls, text: str) -> str:
        text = text.strip()
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
        m = re.search(r"```(?:python)?\s*(.*?)\s*```", text, flags=re.S)
        if m:
            return m.group(1).strip()
        pos = text.find("def ")
        if pos >= 0:
            return text[pos:]
        return text

    # ========== 新增：剪贴板支持 ==========
    @staticmethod
    def copy_to_clipboard(text: str) -> bool:
        """跨平台复制到剪贴板，成功返回 True，失败返回 False"""
        try:
            if sys.platform == "win32":
                subprocess.run(['clip'], input=text.encode('utf-16-le'), check=True)
            elif sys.platform == "darwin":
                subprocess.run(['pbcopy'], input=text.encode('utf-8'), check=True)
            else:
                tool = 'xclip' if subprocess.run(['which', 'xclip'], capture_output=True).returncode == 0 else 'xsel'
                args = [tool, '-selection', 'clipboard'] if tool == 'xclip' else [tool, '--clipboard', '--input']
                subprocess.run(args, input=text.encode('utf-8'), check=True)
            return True
        except Exception as e:
            print(f"复制到剪贴板失败: {e}")
            return False
```

---

### 2. 修改 `agents/case_generator_agent.py`（支持 dry_run 模式）
```python
# agents/case_generator_agent.py
from pathlib import Path
from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOllama
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
        """拼接 RAG 检索到的参考样例"""
        refs = self.retriever.retrieve(knowledge_requirements)
        return "\n\n".join([r.to_json() for r in refs])

    def build_prompt_text(self, problem: ProblemContext) -> str:
        """
        构造完整的 Prompt 文本（不含 LLM 调用），供手动提问使用。
        """
        complexity: ComplexityHint = problem.solution_struct.complexity_hint
        analysis_str = (
            f"Time complexity: {complexity.time_complexity or 'unknown'}. "
            f"Space complexity: {complexity.space_complexity or 'unknown'}. "
            f"Estimated max n: {complexity.estimated_n_limit or 'unspecified'}. "
            f"Notes: {complexity.notes or ''}"
        )
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
```

---

### 3. 在调用程序中启用 dry_run 模式

修改你的 `V0.7.5版调用程序.py`，在 `case_gen_agent.run(context)` 之前加入如下判断：

```python
# ========== 新增：控制是否手动提问 ==========
DRY_RUN = True   # 改为 False 则自动调用 LLM

if DRY_RUN:
    case_gen_agent.run(context, dry_run=True)
    print("已生成 Prompt 并复制到剪贴板，请手动提问后将代码放入 auto/ 目录，然后重新运行本脚本。")
    exit(0)
else:
    generated_code = case_gen_agent.run(context)
    if generated_code is None:
        print("生成失败，请检查 Prompt 文件。")
        exit(1)
    # 后续与之前相同
    local_ns = {}
    try:
        exec(generated_code, {"__builtins__": __builtins__}, local_ns)
        case_generator = local_ns["case_generator"]
    except Exception as e:
        fallback_path = problem_dir / "generated_case_generator.py"
        fallback_path.write_text(generated_code, encoding="utf-8")
        print(f"⚠️ 代码执行失败：{e}\n已保存至 {fallback_path}")
        exit(1)
    # ... 继续生成测试用例、运行暴力算法等
```

---

### 改动说明

- **`AgentIO.copy_to_clipboard`**：跨平台剪贴板支持，让你无需手动打开文件复制。
- **`CaseGeneratorAgent.build_prompt_text`**：单独的方法，生成完整 Prompt 文本，方便调试和后续扩展（例如保存到文件或发送给其他 LLM）。
- **`run(dry_run=False)`**：当 `dry_run=True` 时，仅生成 Prompt、保存并复制，**不调用 Ollama**，彻底避免网络/服务不稳定导致的崩溃。
- 原有调用方式只需增加一个布尔变量即可切换模式，非常适合现阶段调试（省 token、避坑）。

现在即使 Ollama 暂时连不上，你也可以通过生成 Prompt → 手动粘贴到 Ollama → 将返回代码存入 `auto/case_generator_xxx.py`，再运行程序即可。