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
  r"src\bigint_vid.h",
  r"src\safe_iter_base.h",
  r"tools\safe_iter_base.c",
  r"tools\safe_iter.pyx",
  r"src\container.h"
]

source_texts = []
for file in source_files:
  with open(file,"r",encoding="utf-8") as fp:
    lines = fp.readlines()
    print(f"read file: {file} ,lines = {len(lines)}")
    source_texts.append(
      f"```{file}\n{filter_empty(lines,NOT_EMPTY_LINES)}```"
      ) # 去掉空行的空格


template_text = """附件pyx的代码已经经过严格测试通过。
但是二叉树的迭代亟需优化（链表以不需要且通过测试）
我已经写了如下代码（./src 已加入路径）：
{}
{}
{}
{}
{}
1. 注意需要考虑将来伪泛型的架构，我查了一下：
- Cython 的 fused 并不支持加入到 vector
- Cython 的 IF 已经被认为准备弃用
- 函数指针方案会增加运行开销
2. 为了测试方便编程，保持基类对链表的兼容性的同时，修改二叉树。
3. 请补全将 safe_iter_kit.pyx 拆分为如下部分：
- safe_iter_base.c （用宏编程当链表时去掉大整数的内存占用，需要包含所有涉及 RevisitEntry 定义的方法）
- container.h （我已经实现在 tools\container.c，调用库的确保正确）
- safe_iter.pyx （Cython 迭代类和包装类）
4. 因此最终方案：
- 大整数完全依附于 SafeIterBase，因此一并 C 化
- 注意只有 tree_iter_kit.pyx 需要使用 container.h 、 bigint_vid.h 、 early_stop，因此下放到子类
- C语言写的迭代类，为了方便定义节点在 _revisit 中的下标，改为以 RevisitEntry 为单位返回，如此可方便需要返回节点本身和位置的 flatten 高效迭代。
- 注意利用结构体成员顺序进行C多态，使得“继承类”的 _revisit 等元素可以被基类识别其共同前缀成员。
5. 架构重点：
- 因此需要将  stack（queue）统一为容器结构体，通过函数指针实现  stack（queue）的泛型，加入到 SafeIterBase
- SafeIterBase 尽量做到链表和树共用一套编译后的代码，通过 utarray.h 的泛型实现
- 为了兼容链表，链表也采用 queue，只不过容量仅有 2，替代 self._cur，同时不需要 __next__
- TreeIterBase版的RevisitEntry 中的 vid 和 early_stop 仅树需要用，而链表是不需要的，因此只需要在 TreeIterBase 中定义即可
- TreeIterBase 调用 container 的 push 的同时需要引用 +1，但是 pop 不需要 -1，因为可以等 cheak_safe 后，当返回非负1 时（不安全）减1（因为 _seen 已经持有引用计数，不安全说明没有新增 _seen 节点，而最终释放时是以 _seen 为准）
- SafeIterBase 所需的 prepare_next 定义一个兼容 C 的全局/静态函数作为桥梁，用到 Context 架构
6. 请先优化已有代码，根据注释中的报错修复代码，并初步实现 链表类 .pyx
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