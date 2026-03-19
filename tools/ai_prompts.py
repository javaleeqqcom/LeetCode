# tools/ai_prompts.py
"""
AI 提示词模板库 - 用于测试用例生成等自动化任务
"""
from typing import List, Dict, Any, Union

# ============================================================================
# 测试用例生成器 - 系统提示词
# ============================================================================
class TEST_CASE_GENERATOR:
    SYS_PROMPTS:List[str] = [
"你是一个专业的信息竞赛老师。你的任务是根据题目描述和代码，生成全面、高质量的测试用例生成代码，用于检验学生的解答代码<student-code>的正确性。",
"本本工程会提供执行框架，使用多线程并发执行学生代码，并返回执行结果，因此你只需生成测试用例相关代码，通常无需考虑执行框架。",
"代码除了注释用英文书写，注释可用中文书写，注意输出的代码应与代码<code>的语言类型一致，输出内容必须能直接运行为代码（注意不要重复写<code>中的代码）。",
"给定 LeetCode 题目及输入`input`输出`expected`要求见<request>（注意 request 中关于输入输出的数值范围中，有些10的指数次方在复制时会丢失指数符合，需要你灵活判断，如'104'实际可能为'10^4'），你需要思考测试样例设计逻辑。",
"<code>为被测代码，不可修改！其中包含本工程预定义输入输出转换代码<init-code>，以及学生代码<student-code>，其中必定包含 Solution 类（若不是则应报错，拒绝本次回答）。",
"需要注意的是，由于leetcode多语种通用性，其样例的原始输入`input`和输出`expected`只能是JSON输入类型（_STANDARD_TYPE），因此若学生代码的调用函数参数`params`类型并非_STANDARD_TYPE，则需要依赖<init-code>或者你定义的类型转化函数实现转换。",
'单个样例有两种格式，在本次回答中，你只能选择一种格式进行设计：①仅设计输入`input`，依靠暴力算法测得期望输出`expected`，则样例类型为`Tuple[_STANDARD_TYPE,...]`，用一个元组表达题目输入`input`的所有参数；②设计输入`input`和期望输出`expected`，适合答案驱动型测试生成 (Answer-First Generation)的题目，如先知道答案`expected`，再构造题目输入`input`，则样例类型为如下字典：`{"input":Dict[str,_STANDARD_TYPE], "expected":_STANDARD_TYPE}`，注意"input"键的值也是一个字典，包含题目输入参数的键值对。',
"你需要参考模板<template>设计样例生成代码。<template>的代码不依赖于<student-code>，而是在其之前执行。其核心目的在于生成题目输入`input`，并不实现调用和类型转换。",
"由于学生代码<student-code>在各编程语言中的函数名和参数(params)名及类型是强制固定的，不可修改！有时候样例的原始输入`input`和输出`expected`与学生代码函数的参数类型并不一致，甚至可能数量不匹配，或者不止一个调用函数，此时需要设计额外的转换函数。这种情况需要参考<exchange>模块，其用于类型转化或Solution的调用，由本工程拼接到<code>尾部进行调用。",
"<attentions>为代码设计需要注意的点，请根据本次问题的情况参考。"
]
    
    TEMPLATE_UNIQUE:str = """
```test_cases_generator
# 省略导入 init.* 和 answer.* 的代码，仅需写如下代码。所有输出必须可直接运行，非代码的说明必须用注释。
def test_cases_generator(random_case_num:int [, max_n:int ...])->Union[
    List[Tuple[_STANDARD_TYPE,...]] , 
    Dict[str, Union[ Dict[str,_STANDARD_TYPE], _STANDARD_TYPE ]]
]: # ①仅设计输入`input` 或 ②设计输入`input`和期望输出`expected`
    # random_case_num ：生成的随机样例数量，必含。
    # [, max_n:int ...] ：用于指代与问题复杂度相关的参数（可以根据问题修改具体名称，可能为空，也可能不止1个参数）

    # 固定用例（用于覆盖各种可预见的边界情况，如空输入、临界值等）
    res = [...]

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
```
"""

    TEMPLATE_CALLS="""
```test_cases_generator
# 省略导入 init.* 和 answer.* 的代码，仅需写如下代码。所有输出必须可直接运行，非代码的说明必须用注释。
def test_cases_generator(random_case_num:int [, max_n:int ...])->Union[
    List[Tuple[List[str],List[_STANDARD_TYPE],...]] ,
    Dict[str, Union[ Dict[str,_STANDARD_TYPE], _STANDARD_TYPE ]]
]: # ①仅设计输入`input` 或 ②设计输入`input`和期望输出`expected`
    # random_case_num ：生成的随机样例数量，必含。
    # [, max_n:int ...] ：用于指代与问题复杂度相关的参数（可以根据问题修改具体名称，可能为空，也可能不止1个参数）

    # 固定用例（用于覆盖各种可预见的边界情况，注意至少有构造函数操作。但是要注意，若学生代码为暴力算法，规模不能过大。）
    res = [
        (["Solution",...],[...],...),
        (["Solution",...],[...],...),
        ...
    ] # 这里仅以情况①仅设计输入`input`为例

    # 可选：由于该问题是多魔术方法的类实现问题，可能需要继承学生的 Solution 类，进行内部状态的窥探，方能生成合法的操作
    class inner_Solution(Solution):
        ...

    def 单随机样例生成器 f(规模参数)->Tuple[List[str],List[_STANDARD_TYPE],...]:
        # 返回的第一个元素为操作函数名列表，第二个之后为代入被操作函数的参数列表，一般无参数时用空数组代替（具体按<request>定义调整）
        ...
        obj = inner_Solution(...) # 若定义了 inner_Solution
        ...
    
    # 生成随机用例
    for(i in 0..random_case_num):
        # [可选：规模参数随 i 增大而增大]
        ...

        res.append(单随机样例生成器 f(规模参数...))
    return res
```
"""

    EXCHANGE_UNIQUE = """
```exchange
# 丰富 input_parser_registry 转换器（可选）如遇到新的数据类型，可以参考 <init-code> 添加对应的转换器
def ... # 注意禁止使用 lambda 等不可序列化对象，因为这会导致多线程无法复制环境变量
input_parser_registry[(input_type, output_type)]:Callable = ...
# 当返回值为特殊类型时，需要利用 output_parser_registry 转化为 _STANDARD_TYPE：
output_parser_registry[(custom_type)]:Callable = ...
# 仅当 input_parser_registry 等无法实现转化时，才定义 exchange 函数
def exchange(*args):
    # args 为<request>中定义的输入参数，即对应 test_cases_generator 中每个Tuple元素
    ...
    params1 = ...
    params2 = ...
    # 返回<student-code>非魔术方法所需参数，按顺序排列返回
    return params1,params2...
```
"""
    EXCHANGE_CALLS = """
def solution_callers(Solution,methods,*args):
    # 为了兼容多线程，并且由于 Solution 由学生定义，无法确保可序列化，因此需要作为参数传入
    assert methods[0] == "Solution", "测试样例非法！未初始化 Solution 不可能进行其它操作"
    try:
        solution = Solution(...)
        ...
        return 按题目要求检测结果是否合法
    except:
        return 操作非法...
"""

    ATTENTIONS_UNIQUE = [
        "<student-code>仅有唯一非魔术方法且默认构造函数无参数，则你不需要调用构造函数，本工程会自动执行`solution=Solution()`进行构造。",
        "本工程会利用 input_parser_registry 函数尽可能地将“目标被测函数”的输入从JSON标准类型转化为其所需的各种类型。"
    ]

    ATTENTIONS_EXCHANGE = [
        "若你认为<init-code>无法实现特殊类型与 _STANDARD_TYPE 的转化，你可以在`exchange`模块实现相关转化。注意不要试图在 test_cases_generator 直接生成特殊类型的输出，因为这会导致本工程的样例保存中的 JSON 序列化失败。"
    ]
    
    # 3.1. <student-code>仅有唯一非魔术方法且默认构造函数无参数，则你不需要调用构造函数，本工程会自动执行`solution=Solution()`进行构造
    # 3.2. 在满足 3.1 的情况下，若学生的 Solution 类的唯一非魔术方法的参数类型与<request>中的输入类型
    # 并自动识别该非魔术方法名进行调用，则你只需输出"test_cases_generator"代码段；2.有多个非魔术方法或其构造函数有参数，则除了"test_cases_generator"你还需要定义调用方法代码段"caller"。请根据实际情况选择合适的模板进行。

    ATTENTIONS = [
        """注意规模参数随 i 增大而增大设计不能用绝对量，如下错误案例：
```
if i < random_case_num // 4:
    # 小规模：1-100
    n = random.randint(1, 100)
elif: ...
else:
    # 大规模：5000-max_n
    n = random.randint(5000, min(max_n, 10000))
```
会导致如 ValueError: empty range in randint(5000, 10) 的错误。""",
"尽量用函数化平滑化设计，少用 if-else ，代码应极简。如用负指数分布、对数正态分布、泊松分布等取整代替分段函数。",
"test_cases_generator 函数的输出必须是JSON允许的输入类型。",
"固定样例必须有的放矢，并且计算规模不能大，确保暴力算法可以快速执行。",
    ]
    
    @classmethod
    def get_manual_prompt(cls,codes:str,request:str,is_unique_caller:bool,has_custom_type:bool,attached_attentions:List[str]=[])->str:
        attentions = cls.ATTENTIONS.copy()
        if is_unique_caller:
            attentions.extend(cls.ATTENTIONS_UNIQUE)
        if has_custom_type:
            attentions.extend(cls.ATTENTIONS_EXCHANGE)
        attentions.extend(attached_attentions)

        exchange = None
        if is_unique_caller:
            if has_custom_type:
                exchange = cls.EXCHANGE_UNIQUE
        else:
            exchange = cls.EXCHANGE_CALLS

        templates = []
        if is_unique_caller:
            templates.append(cls.TEMPLATE_UNIQUE)
        else:
            templates.append(cls.TEMPLATE_CALLS)
            
        return f"<system>\n{''.join(f"\n{i}. {s}" for i,s in enumerate(cls.SYS_PROMPTS))}</system>\n<request>\n{request}\n</request>\n<code>\n{codes}</code>\n<template>{'\n'.join(templates)}</template>\n<attentions>{''.join(f"\n{i}. {s}" for i,s in enumerate(attentions))}\n</attentions>" + (
            f"<exchange>{exchange}</exchange>" if exchange is not None else ""
            )
