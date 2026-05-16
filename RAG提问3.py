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
  r"rag_knowledge\case_generator\unique_call.leetcode_3660.py",
  r"rag_knowledge\conversion\python\defalut_args.py",
  r"rag\chunker.py",
  r"rag\docs_inclusion.py",
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
原 case_generator 和 conversion 的 RAG 數據庫混在一起，不合適。
我擬定如下目錄和代碼：
{}
{}
每一個目錄設置一個獨立的 RAG。
由于 case_generator 和 conversion 是完全独立的阶段，因此分不同 RAG 数据库。
对于 case_generator：
- 目前的切分不够智能，应当按步骤和功能再独立切分，例如：
`A.独特元素的个数` 和 `B.选择数组数值分布` 可以通过在注释中增加特殊标记，让 RAG 切片程序识别，并将其切分成独立的模块。而且完整的函数直接向量化可能会过长。
- 查询时匹配到候选局部模块统计相关性得分，选择总分最高的一个文件将其函数 F 完整地提取出来。
- 若有排除在 F 外的其他高得分模块，也可以作为补充进行参考。
- 目前测试样例仅通过 python 生成，一般不考虑采用其他语言实现，若需要高性能，可以用 Python 调用 Rust 实现局部模块，则届时可另外建立RAG。
对于 conversion：
- 其高度依赖语言特性，因此不同语言必须不同文件夹和 RAG
- 而 Args、Kwargs、多caller 的区分，暂时没有确定应当同一 RAG 还是不同 RAG，可能需要实践摸索才能确定。
现在需要先增加通过注释主动的切片规则，通过注释标记实现一套规则，要能自由调整上下文界限（例如有一些功能的输入需要依赖特殊的上一步的输出，因此需要将上一步的一部分纳入；而有的则不需要）：
{}
目前的代码已经有记录文件追溯，增量更新的功能，如下以供参考：
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