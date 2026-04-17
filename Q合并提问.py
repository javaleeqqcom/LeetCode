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
  "tools/LinkIterKit.pyx",
  "Q报错如下.txt",
]

source_texts = []
for file in source_files:
  with open(file,"r",encoding="utf-8") as fp:
    source_texts.append(filter_empty(fp.readlines(),NOT_EMPTY_LINES)) # 去掉空行的空格

template_text = """附件pyx的代码已经经过严格测试通过。
{}
如下代码除了打印之外都正确，因为我新增了 _format_repr 函数，但是测试发现 raw 被误识别为 bool， next 不能判空，而是会返回错误类型。
```LinkIterKit.pyx
{}
```
执行如下。
```
{}
```
另外原生节点代码：
```
# 示例：LeetCode 常见结构（学生可按题追加）
class ListNode:
    def __init__(self, val:_BASE_TYPE=0, next:Optional[ListNode]=None):
        self.val = val
        self.next = next
    # 方便调试，且与 leetcode 不冲突
    def __repr__(self) -> str:
        return KitBase._format_repr(True,"val",next=(False,"val") if self.next else None)
```
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
