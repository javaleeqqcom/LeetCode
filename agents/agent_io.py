# agents/agent_io.py
from pathlib import Path
import re
import sys
import subprocess

class AgentIO:

    @classmethod
    def get_auto_dir(cls, problem_dir:Path)->Path:
        path = problem_dir / "auto"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def get_log_dir(cls, problem_dir:Path)->Path:
        path = problem_dir / "agent_logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def next_index(cls, problem_dir: Path , prefix = "case_generator_") -> int:
        auto_dir = cls.get_auto_dir(problem_dir)
        max_id = -1
        for f in auto_dir.glob(f"{prefix}*.py"):
            m = re.match(rf"{prefix}(\d+)\.py", f.name)
            if m:
                max_id = max(max_id, int(m.group(1)))
        return max_id + 1

    @classmethod
    def clean_llm_code(cls, text: str) -> str:
        text = text.strip()
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S) # 去除思考过程
        m = re.search(r"```(?:python)?\s*(.*?)\s*```", text, flags=re.S) # 提取Python代码框内部
        if m:
            return m.group(1).strip()
        pos = text.find("def ")
        if pos >= 0:
            return text[pos:]
        return text

    # ========== 新增：剪贴板支持（待改进：encoding 暂时写死） ==========
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