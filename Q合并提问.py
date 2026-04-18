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
  "tools/iter_node_tools 极限优化方案.md",
  "tools/safe_iter_kit.pyx",
  "Q报错如下.txt",
  "另附测试相关代码.txt"
]

source_texts = []
for file in source_files:
  with open(file,"r",encoding="utf-8") as fp:
    source_texts.append(filter_empty(fp.readlines(),NOT_EMPTY_LINES)) # 去掉空行的空格

template_text = """附件pyx的代码已经经过严格测试通过。
{}
如下代码的链表部分已经通过压力测试
```safe_iter_kit.pyx
{}
```
执行报错如下：
```
{}
```
注意get_heap 已经改为不使用 SafeIterBase，注意 iter_node_tools.pyx 是完全正确的，__next__、_prepare_next、__getitem__ 都是照抄原来的代码应该没错，请重点分析 get_heap。
{}""".format(*source_texts)

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
