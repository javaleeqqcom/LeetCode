import re
import subprocess
import sys

def filter_empty(lines, not_empty_lines = False):
  tlines = [
    "" if re.match(r"^\s+$", line) else line.rstrip() 
    for line in lines
  ] # 处理每一行：去掉右侧空格（含换行符），保留中间的空行（变为空字符串）
  if not_empty_lines:
    tlines = list(filter(len,tlines))
  else:
    while tlines and tlines[-1] == "":
      tlines.pop() # 仅删除【文件末尾】的连续空行
  return '\n'.join(tlines)

NOT_EMPTY_LINES = True
source_files =[
  r"tools\solution_runner.py",
  r"暴力VS改进.py",
  r"Question\3660. Jump Game IX\bt.py",
  r"Q执行如下.txt",
]

source_texts = []
for file in source_files:
  with open(file,"r",encoding="utf-8") as fp:
    lines = fp.readlines()
    print(f"read file: {file} ,lines = {len(lines)}")
    source_texts.append(
      f"```{file}\n{filter_empty(lines,NOT_EMPTY_LINES)}```"
      ) # 去掉空行的空格


template_text = r"""
现在采用 Python 3.14 的多GIL多进程，可以实现动态分配任务到多个CPU核心，尽可能使得每个线程同时执行完毕。
代码如下：
{}
{}
之前设计时，学生代码放在根目录，可以正常执行，但是现在代码放在：
{}
则如下错误：
{}
""".format(*source_texts)

import sys
import subprocess

def copy_to_clipboard(text: str) -> bool:
  try:
    if sys.platform == "win32":
      # Windows: clip.exe 配合 utf-16 是最稳定的组合，能完美处理中文和特殊字符
      # 不需要 shell=True，直接传递字节流
      subprocess.run(
          ['clip'], 
          input=text.encode('utf-16-le'), 
          check=True
      )
    elif sys.platform == "darwin":
      subprocess.run(['pbcopy'], input=text.encode('utf-8'), check=True)
    else:
      # Linux
      tool = 'xclip' if subprocess.run(['which', 'xclip'], capture_output=True).returncode == 0 else 'xsel'
      args = [tool, '-selection', 'clipboard'] if tool == 'xclip' else [tool, '--clipboard', '--input']
      subprocess.run(args, input=text.encode('utf-8'), check=True)
    
    return True
  except Exception as e:
    print(f"复制失败: {e}")
    return False

# 使用示例
line_count = template_text.count('\n')
print(f"待合并文本共 {line_count} 行")

if copy_to_clipboard(template_text):
  print("✅ 已成功复制到剪贴板。")
else:
  print("❌ 复制失败，请检查系统环境。")


# - 原 safe_iter_kit.pyx 有一个风险点，对于树，其 stack 和 queue 并没有持有原生节点的引用计数
# - 因此需要修改为入 stack（queue） 就增加引用，而 check_safe 仅当为重复（in _seen 为真）时减少引用计数，销毁时按 _seen 减少引用计数