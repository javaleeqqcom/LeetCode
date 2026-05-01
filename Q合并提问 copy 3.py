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
  r"tools\solution.cpp",
  # r"Q执行如下.txt"
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
然而想要将该C++的编程题目执行方式集成到项目中，需要解决：
- 调用去题目耦合化，不能出现`sol.maxRotateFunction`这种依赖具体问题名字的执行，否则换一道题，就要修改一次调用程序。
- JSON自动参数化，不能依靠手动输入具体的参数，而应当按 JSON 格式传入参数。
- 兼容多线程，这个应该采用 stdio 和多进程解决，注意要像 demo 那样一个进程执行多轮测试样例，避免进程开销。
但是该 demo 最严重的问题是，无法其调用必须依赖AI-prompt编写，增加了AI成本，因此该 demo 应当放弃，应重新认识 Python 为何称为胶水语言，因此应改用 pybind11 的方法调用，以兼容原来的架构。
请重新设计 demo，摒弃这种落后的调用方式，不准用 stdio 传递参数，因为你这样传递最后还是得 AI 编写 JSON -> C++ 变量\结构体的转换，还不如直接让AI生成测试样例直传Solution，然后用多进程暴力执行。
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