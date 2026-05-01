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
  r"tools\run_cpp_test.py",
  r"396. Rotate Function\bt.hpp",
  r"tools\solution.cpp",
  r"Q执行如下.txt"
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
现为了新增 C++ 执行的方式，写了如下 demo：
{}
{}
{}
执行成功：
{}
现在需要将该功能集成到现有的项目中，为了让结构更清晰，需要将 solution_runner.py 分为三部分：
- 原 solution_runner.py 中 .py 解析的部分改为 solution_runner_py.py
- 为了实现不同语言的多线程，solution_runner.py 的多线程改为 multi_thread_runner.py （以后要改为 Cython 加速版，或者用 Rust 重写）
- 现在新增的执行 C/C++ 的代码放在 solution_runner_cpp.py 或 solution_runner_cpp.cpp 中（.py 作为胶水调用 .cpp，而.cpp实现单个线程执行多个样例直到输入停止信号，不知道 #include "bt.hpp" 是否能兼容调用 .c 的代码）
- 将来新增不同的语言，只要能用命令行和stdio 交互，都可以用此方法拓展吧。
请分析一下该方案的可行性，并给出代码框架。
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