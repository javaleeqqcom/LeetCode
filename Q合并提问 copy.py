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
  # r"暴力VS改进.py",
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
首先解决用C++跑暴力算法的功能：
1. 可多线程化（可以先写单线程的代码，但是后面要能扩展为多线程）
1.1 方案一：用Python多解释器调用单个C++循环线程（一个进程分支跑多次循环，避免反复开辟子线程浪费资源）
1.2 方案二：用 C++ 多进程分配（但是为了迎合未来多语种，每一种语言都写一遍多线程可能工程量巨大，而且你的分身也认为此方案过于复杂，目前不适合考虑）
2. 动态增加测试用例方案
2.1 一般测试用例生成函数默认采用 Python（随机分布函数 random 支持友好，编程简洁）
2.2 未来增加支持 AI-agentic 智能地生成 Rust 测试用例代码，或者直接用 Rust 重构 SolutionRunner。（但是目前我没有学习 Rust 的需求，故仅保留支持升级 Rust 的架构）
3. 现在需要先修改 _execute_dict_case 和 SolutionRunner 中的部分代码，增加对 C/C++ 的支持：
3.1 在构造 SolutionRunner 时若未编译 .cpp 或 .c 则自动编译
3.2 _execute_dict_case 自动执行 .o 或 .exe 采用合适的 IO 接口传参数
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