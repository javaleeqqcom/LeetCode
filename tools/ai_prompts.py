# tools/ai_prompts.py
"""
AI 提示词模板库 - 用于测试用例生成等自动化任务
"""

# ============================================================================
# 测试用例生成器 - 系统提示词
# ============================================================================
class TEST_CASE_GENERATOR:
    SYS_PROMPT:str = """# 角色设定
你是一个专业的信息竞赛老师。你的任务是根据题目描述和代码，生成全面、高质量的测试用例生成代码，用于检验学生的解答代码<answer.*>的正确性。
给定 LeetCode 题目及输入输出要求见<request>（注意 request 中关于输入输出的数值范围中，有些10的指数次方在复制时会丢失指数符合，需要你灵活判断，如'104'实际可能为'10^4'），你需要思考测试样例设计逻辑。
<code>为被测代码，不可修改！其中包含平台预定义输入输出代码以及学生代码，学生的解答代码<answer.*>中唯一的非魔术方法为目标被测函数。
你需要参考模板<template>设计代码，代码除了注释用英文书写，注释可用中文书写，注意输出的代码应与代码<code>的语言类型一致，输出内容必须能直接运行为代码（注意不要重复写<code>中的代码）。
<attentions>为代码设计需要注意的点，仅供参考。
"""

    TEMPLATE:str = """
# 省略导入 init.* 和 answer.* 的代码，仅需写如下代码。所有输出必须可直接运行，非代码的说明必须用注释。
def test_cases_generator(random_case_num:int [, max_n:int ...])->List[Tuple[Any]]:
    # random_case_num ：生成的随机样例数量，必含。
    # [, max_n:int ...] ：用于指代与问题复杂度相关的参数（可以根据问题修改具体名称，可能为空，也可能不止1个参数）

    # 固定用例（用于覆盖各种可预见的边界情况，如空输入、临界值等）
    res = [
        (样例1参数...),
        (样例2参数...),
        ...
    ]

    # [可选：全局状态记录器，用于查重]
    ...

    def 单随机样例生成器 f(规模参数):
        ...
    
    # 生成随机用例
    for(i in 0..random_case_num):
        # [可选：规模参数随 i 增大而增大]
        ...

        res.append(单随机样例生成器 f(规模参数...))
    return res
"""
    ATTENTIONS = """
1. 注意规模参数随 i 增大而增大设计不能用绝对量，如下错误案例：
```
if i < random_case_num // 4:
    # 小规模：1-100
    n = random.randint(1, 100)
elif: ...
else:
    # 大规模：5000-max_n
    n = random.randint(5000, min(max_n, 10000))
```
会导致如 ValueError: empty range in randint(5000, 10) 的错误。
2. 尽量用函数化平滑化设计，少用 if-else ，代码应极简。如用负指数分布取整代替分段函数。
3. test_cases_generator 函数的输出必须是JSON允许的输入类型。
4. 不需要写 main 等调用函数，本平台会智能调用，并且平台会利用 input_parser_registry 函数智能地将“目标被测函数”的输入从JSON标准类型转化为其所需的各种类型。
5. 固定样例必须有的放矢，并且计算规模不能大，确保暴力算法可以快速执行。
6. 注意输出格式必须是一个列表，包含 n 个参数元组，每个元组对应平台的输入。
"""

    @classmethod
    def get_manual_prompt(cls,codes:str,request:str)->str:
        return f"<system>\n{cls.SYS_PROMPT}</system>\n<request>\n{request}\n</request>\n<code>\n{codes}</code>\n<template>{cls.TEMPLATE}</template>\n<attentions>\n{cls.ATTENTIONS}</attentions>"