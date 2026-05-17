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
  r"rag_knowledge\case_generator\unique_call.array.leetcode_3660.py",
  r"rag_knowledge\conversion\python\defalut_args.py",
  r"agents\case_generator_agent.py",
  r"rag\docs_inclusion.py",
  r"prompts\case_generator_prompt.md",
  r"rag\chunker.py",
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
- 对于 case_generator：
  - 目前的切分不够智能，应区分 RAG向量片段 和 AI-prompt 片段。
  - 其中RAG向量片段通过 `@RAG_*`标记区分，用于语义相似性查询和推荐。
  - 而 AI-prompt 片段则通过 RAG 溯源信息进行还原，用于向AI提问。
  - 提供示例 AI-prompt 包含两个部分：1. 完整文件 ； 2. 独立模块（可选）：
  1. 完整文件
    - @EXAMPLE_* 是完整文件标记，不再作为 RAG 向量输入，因为通常上下文过长。而是通过统计候选 RAG片段总分高者，进行溯源文件提取。
  2. 独立模块（可选）：
    - @RAG_* 则需要剔除 `@RAG_\w+:` 后才作为 RAG 向量输入，否则所有chunk都包含 `@RAG_\w+:` 会降低特异性，同时可避免 AI 将 @RAG_* 当成不可预测的指令。
    - 只有 @RAG_EXPORT: yes 的模块才允许排除在完整文件外独立作为补充供AI参考。
    - 注意有 @RAG_DEP 标记的，需要将其依赖的模块一并提取（被依赖放在前面，且可递归），在分片时需检查不能用循环依赖（必须有向无环图）。若 B 模块依赖 A 模块，且 A,B 都是高分独立模块时，则将 A,B 按序合并，避免重复输入 AI prompt。
    - @RAG_MODULE_SETTING 仅当作为独立模块（排除在完整文件外）时，转换为注释放在前面，用于描述模块设定，以避免不必要的 @RAG_DEP 。
    - 目前测试样例仅通过 python 生成，一般不考虑采用其他语言实现，若需要高性能，可以用 Python 调用 Rust 实现局部模块，则届时可另外建立RAG。
- 对于 conversion：
  - 其高度依赖语言特性，因此不同语言必须不同文件夹和 RAG
  - 而 Args、Kwargs、多caller 的区分，暂时没有确定应当同一 RAG 还是不同 RAG，可能需要实践摸索才能确定。
  - 由于 conversion 目前较短，暂时不采用 @RAG_... 的分片方式，而是按文件切分，以后需要时再升级细分。
目前的代码已经有记录文件追溯，增量更新的功能，如下以供参考：
{}
目前的 AI-agent代码：
{}
而目前的AI-prompt模板：
{}
现在需要先增加通过注释主动的切片规则，通过注释标记实现一套规则，要能自由调整上下文界限（例如有一些功能的输入需要依赖特殊的上一步的输出，因此需要将上一步的一部分纳入；而有的则不需要）：
{}
建议通过新建 rag/semantic_chunker.py 实现，可以引用 chunker.py 的一些方法，请实现 semantic_chunker.py，使得能够识别 @RAG_ 等。
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