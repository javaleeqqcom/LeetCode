from tools.AIConsultation import AIConsultation as AIC

README = AIC(r"README.md")

debug_retriever = AIC(r"rag\debug_retriever.py")
RAG_DEBUG = AIC(r"RAG_DEBUG.txt")
embedding = AIC(r"rag\embedding.py")
retriever=AIC(r"rag\retriever.py")
index_builder = AIC(r"rag\index_builder.py")
RAG_DOC = AIC(r"rag\RAG_DOC.md")

AGENTS_DOC = AIC(r"agents\AGENTS_DOC.md")
agent_io = AIC(r"agents\agent_io.py")
analyze_agent = AIC(r"agents\analyze_agent.py")
build_graph = AIC(r"agents\build_graph.py")
case_generator_agent = AIC("agents\case_generator_agent.py")
graph_state = AIC(r"agents\graph_state.py")

template_text = fr"""
{README}
我已经初步构建了 RAG 系统和 Agent，DOC分别如下：
{RAG_DOC}
{AGENTS_DOC}
由于当前尚未成熟，不能直接一步到位，要节约token，所以尽量用半监督执行，因此进行 V0.7.6 版本改进：
{AIC(r"V0.7.6版调用程序.py")}
但是执行输出的结果：
{AIC(r"V0.7.6报错.txt")}
我检查了prompt：
{AIC(r"Question\TEST.2902\agent_logs\AI_prompt_002.log")}
以及LLM返回的代码：
{AIC(r"Question\TEST.2902\auto\case_generator_002.py")}
LLM使用了 random 却没有声明。
目前有两种方案：
- 统一在 case_generator 前添加固定的所有可能要用到的库，并在prompt中明确说明你的代码会接在此后。
- 通过 python依赖库自动补齐 依赖库
其中可能需要修改的代码：
{agent_io}
{case_generator_agent}
请参考联网GPT的建议修改代码：
{AIC(r"GPT的改进方案V0.7.6.b.md")}
最后我的建议，由于该免费GPT思考深度受限，其实：
        "List": "from typing import List",
        "Dict": "from typing import Dict",
  - 可以合并为 from typing import List,Dict
- 因此采用指向父依赖的字典更合适：
  - {{"List":("typing"),"Dict":("typing"),"Counter":("collections"),"np":"numpy" , "numpy":(,) ,...}}
  - 至于 from ... import 根据依赖树用专家工程还原
  - 对于有歧义的库，如 random 有 numpy.random ，则暂时用优先级替代，默认深度小的 random 库胜出，毕竟有歧义本来就是写代码的LLM应当负责任的。可以在预设时就禁止 {"random":("numpy")} 这种组合，避免歧义。
  - 字典的 values 分两种：
    - str：说明是key是别名，values 标准原始名
    - tuple：按层级从子到父，用于多级 import 还原，若为空 () 则直接 import，否则需要 from
  - 最后生成 import：
    - 首先处理别名，因为别名后缀是 ` as ...` 不能合并多行
    - 然后用堆排序，从深度高到低，同深度字典树，合并如`from typing import List,Dict`的。 
"""
# 可以参考GPT联网搜索下的建议：
# {AIC(r"GPT的改进方案V0.7.6.a.md")}

# 使用示例
line_count = template_text.count('\n')
print(f"待合并文本共 {line_count} 行")

if AIC.copy_to_clipboard(template_text):
  print("✅ 已成功复制到剪贴板。")
else:
  print("❌ 复制失败，请检查系统环境。")


# - 原 safe_iter_kit.pyx 有一个风险点，对于树，其 stack 和 queue 并没有持有原生节点的引用计数
# - 因此需要修改为入 stack（queue） 就增加引用，而 check_safe 仅当为重复（in _seen 为真）时减少引用计数，销毁时按 _seen 减少引用计数