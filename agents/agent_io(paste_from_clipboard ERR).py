# agents/agent_io.py
from pathlib import Path
from typing import List, Optional
from langchain_core.messages import BaseMessage
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
        
    @staticmethod
    def send_messages_to_clipboard(messages: List[BaseMessage], problem_dir: Path) -> bool:
        """
        将消息列表序列化为文本并复制到剪贴板。
        若复制失败，则自动保存到日志文件并返回 False。
        """
        text = "\n\n".join(str(m.content) for m in messages)
        if AgentIO.copy_to_clipboard(text):
            return True
        # 复制失败时写入临时日志
        log_dir = AgentIO.get_log_dir(problem_dir)
        log_path = log_dir / f"manual_prompt_{Path(problem_dir).name}.log"
        log_path.write_text(text, encoding="utf-8")
        print(f"剪贴板操作失败，已将 Prompt 保存至: {log_path}")
        return False
    
    # ========== 新增：剪贴板读取（无损处理各种平台编码） ==========
    @staticmethod
    def paste_from_clipboard() -> str:
        """跨平台从剪贴板读取文本，成功返回字符串，失败或为空返回空字符串 "" """
        try:
            if sys.platform == "win32":
                # Windows 的 clip 命令只进不出，读取通常使用 PowerShell 的 Get-Clipboard
                # 使用 utf-16-le 编码可以完美保留 Emoji 和各种特殊字符
                result = subprocess.run(
                    ['powershell', '-NoProfile', '-Command', 'Get-Clipboard'],
                    capture_output=True,
                    check=True
                )
                # PowerShell 输出通常带有 BOM 或特定编码，在 Windows 上尝试 utf-16-le 或 standard cp936/utf-8
                # 最稳妥的方式是让 PowerShell 处理好输出，或者直接通过标准输出读取
                # 这里推荐使用 text=True 并指定 errors='ignore'，或直接用默认系统编码
                return result.stdout.decode('rf-shell-output', errors='replace').strip() 
                
            elif sys.platform == "darwin":
                # macOS 使用 pbpaste，系统默认采用 utf-8 编码
                result = subprocess.run(['pbpaste'], capture_output=True, check=True)
                return result.stdout.decode('utf-8')
                
            else:
                # Linux 自动检测 xclip 或 xsel
                is_xclip = subprocess.run(['which', 'xclip'], capture_output=True).returncode == 0
                if is_xclip:
                    args = ['xclip', '-selection', 'clipboard', '-o']
                else:
                    args = ['xsel', '--clipboard', '--output']
                
                result = subprocess.run(args, capture_output=True, check=True)
                return result.stdout.decode('utf-8')
                
        except Exception as e:
            print(f"从剪贴板读取失败: {e}")
            return ""