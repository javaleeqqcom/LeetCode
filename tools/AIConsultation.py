import os
import re
import sys
import subprocess
from typing import Optional

class AIConsultation:
    @staticmethod
    def filter_empty(lines, not_empty_lines=False):
        tlines = [
            "" if re.match(r"^\s+$", line) else line.rstrip()
            for line in lines
        ]
        if not_empty_lines:
            tlines = list(filter(len, tlines))
        else:
            while tlines and tlines[-1] == "":
                tlines.pop()
        return '\n'.join(tlines)

    def __init__(self, file, not_empty_lines=True):
        with open(file, "r", encoding="utf-8") as fp:
            lines = fp.readlines()
            print(f"read file: {file} ,lines = {len(lines)}")
            self.file = file
            self.content = self.filter_empty(lines, not_empty_lines)

    def __repr__(self) -> str:
        return f"```{self.file}\n{self.content}```"

    @staticmethod
    def copy_to_clipboard(text: str) -> bool:
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
            print(f"复制失败: {e}")
            return False
