# tools/ai_prompts.py

"""
AI 提示词模板库 - 用于测试用例生成等自动化任务
"""
from typing import List, Dict, Any, Union
from tools.args_parser import _DEFAULT_TEST_CASES_GENERATOR_FILE_NAME

# ============================================================================
# 测试用例生成器 - 系统提示词
# ============================================================================
class TEST_CASE_GENERATOR:
    SYS_PROMPTS:List[str] = [
"你是一个专业的信息竞赛老师。你的任务是根据题目描述和代码，生成全面、高质量的测试用例生成代码，用于检验学生的解答代码<student-code>的正确性。",
"本本工程会提供执行框架，使用多线程并发执行学生代码，并返回执行结果，因此你只需生成测试用例相关代码，通常无需考虑执行框架。",
"代码除了注释用英文书写，注释可用中文书写，注意输出的代码应与代码<code>的语言类型一致，输出内容必须能直接运行为代码（注意不要重复写<code>中的代码）。",
"给定 LeetCode 题目及输入`input`输出`output`要求见<request>（注意 request 中关于输入输出的数值范围中，有些 10 的指数次方在复制时会丢失指数符合，需要你灵活判断，如'104'实际可能为'10^4'），你需要思考测试样例设计逻辑。",
"<code>为被测代码，不可修改！其中包含本工程预定义输入输出转换代码<init-code>，以及学生代码<student-code>，其中必定包含 Solution 类（若不是则应报错，拒绝本次回答）。",

"需要注意的是，由于 leetcode 多语种通用性，其样例的原始输入`input`和输出`output`只能是 JSON 输入类型（_STANDARD_TYPE），因此若学生代码的调用函数参数`params`类型并非_STANDARD_TYPE，则需要本工程定义的<init-code>代码实现转换，若无法转换则你需要修改<args_parser>中的代码以实现调用。",
'测试用例统一格式为：`{"input": input_params [, "output": _STANDARD_TYPE]}`，其中 input_params 有两种格式：元组(Tuple)对应<request>中的`input`中参数没有命名的情况（则其元素的顺序必须按<request>中输入参数的顺序为准）；字典(Dict)对应<request>中的`input`中参数有命名的情况。而 output 为可选项，仅当该问题的答案在构造输入样例时很容易求得，甚至先有答案后构造输入样例的情况下，才允许添加可选项 output 为期望输出。注意不要试图在你的代码中完整地运行学生暴力算法的 Solution 对象来求得 output 输出，因为本工程可以用多线程的方式调用学生暴力算法，不需要你来运行。',
"一般<request>中的参数与<student-code>中主函数的参数是一一对应的。但若对应不上，由于学生代码<student-code>在各编程语言中的函数名和参数 (params) 名及类型是强制固定的，不可修改！则需参考修改<args_parser>中的 main_caller 方法以正确处理参数映射，并以<conversion>模块输出 conversion.py 代码放在 <code> 代码后覆盖原有定义。",

"你需要参考模板<template>设计样例生成代码。<template>的代码不依赖于<student-code>，而是在其之前执行。其核心目的在于生成题目输入`input`，并不实现调用和类型转换。",
"<attentions>为代码设计需要注意的点，请根据本次问题的情况参考。"
]
    
    TEMPLATE_UNIQUE:str = f"""
```{_DEFAULT_TEST_CASES_GENERATOR_FILE_NAME}.py
# 省略导入 init.* 和 answer.* 的代码，仅需写如下代码。所有输出必须可直接运行，非代码的说明必须用注释。
def {_DEFAULT_TEST_CASES_GENERATOR_FILE_NAME}(random_case_num:int [, max_n:int ...])->List[_CASE_TYPE]:
    # random_case_num：生成的随机样例数量，必含。
    # [, max_n:int ...]：用于指代与问题复杂度相关的参数（可以根据问题修改具体名称，可能为空，也可能不止 1 个参数）

    # 固定用例（用于覆盖各种可预见的边界情况，如空输入、临界值等），此处以 input_params 为元组类型为例
    res = [
        {{"input": (arg1, arg2)}}, # 注意所有的 arg* 参数必须为 _STANDARD_TYPE 类型，确保可以 JSON 序列化。
        ...
    ] # 仅当很容易获知答案时，可以添加 "output" 键，注意 output 的值必须为 _STANDARD_TYPE 类型，确保可以 JSON 序列化。

    # [可选：全局状态记录器，用于查重]
    ...

    def 单随机样例生成器 f(规模参数)->Dict[str, _STANDARD_TYPE]:
        ...
        return {{"input": {{"param1": val1, "param2": val2 ,...}}}}, # 此处以字典类型为例
        # 仅当很容易获知答案时，返回：{{"input": input_params, "output": 期望输出（_STANDARD_TYPE 类型）}}
    
    # 生成随机用例
    for(i in 0..random_case_num):
        # [可选：规模参数随 i 增大而增大]
        ...

        res.append(单随机样例生成器 f(规模参数...))
    return res
```
f"""

    TEMPLATE_CALLS="""
```{_DEFAULT_TEST_CASES_GENERATOR_FILE_NAME}.py
# 如下代码本工程会拼接到<code>之后运行，无需重复中的代码。所有输出必须可直接运行，非代码的说明必须用注释。
def {_DEFAULT_TEST_CASES_GENERATOR_FILE_NAME}(random_case_num:int [, max_n:int ...])->List[_CASE_TYPE]:
    # random_case_num：生成的随机样例数量，必含。
    # [, max_n:int ...]：用于指代与问题复杂度相关的参数（可以根据问题修改具体名称，可能为空，也可能不止 1 个参数）

    # 固定用例（用于覆盖各种可预见的边界情况，注意至少有构造函数操作。但是要注意，若学生代码为暴力算法，规模不能过大。）
    res = [
        {"input": (["Solution",...],[...], ...), "output": [None,...]}, # 第一个操作必定是构造函数，无返回值
        ...
    ]
    # 上述为`input`无参数名的情况为例，若<request>中的输入有命名，则以字典格式为准

    # 若难以获得期望`output`，则无需填写`output`，由学生提交的暴力算法计算得出
    # res = [{"input": [["Solution",...],[...], ...],}, ...]

    # 可选：由于该问题是多魔术方法的类实现问题，可能需要继承学生的 Solution 类，进行内部状态的窥探，方能生成合法的操作。但是要注意，只有当学生实现正确时，才可窥探其内部状态。否则，可能会导致错误的操作。
    class inner_Solution(Solution):
        ...
    # 可选：因为 Solution 类的接口受到限制，难以设计低复杂度的实现，你也可以选择重新设计，但是注意最终的目标是为了检验 Solution 的实现是否正确。
    class easy_Solution:
        ...

    def 单随机样例生成器 f(规模参数)->Dict[str, _STANDARD_TYPE]:
        # 返回格式：{"input": {"methods":["Solution",...],"params":[(__init__的args参数),...其余方法的参数（也可能为空元组表示无参数调用）]}}
        # 上述为`input`有参数名的情况为例，若<request>中的输入无参数名，则应返回元组格式的 `input` 值。若可以轻松获得期望`output`，则应填写`output`值。

        # 对于多方法调用问题，input 列表应包含所有操作所需的参数（按调用顺序）
        ...
        # obj = inner_Solution(...) # 若定义了 inner_Solution ，可以利用其辅助构建用例
        ...
    
    # 生成随机用例（注意若使用了 inner_Solution ，则需注意其复杂度，若`复杂度(规模)`过高，可能会影响测试效率）
    for(i in 0..random_case_num):
        # [可选：规模参数随 i 增大而增大]
        ...

        res.append(单随机样例生成器 f(规模参数...))
    return res
```
f"""

    CONVERSION_UNIQUE = """
```conversion.py
# 丰富 input_parser_registry 转换器（可选）如遇到新的数据类型，可以参考  添加对应的转换器
# def 示例转换函数1(params1:A_STAND_TYPE)->DIY_TYPE: # 注意禁止使用 lambda 等不可序列化对象，因为这会导致多线程无法复制环境变量
#     ...
# input_parser_registry[(A_STAND_TYPE,DIY_TYPE)] = 示例转换函数1

# 当返回值为特殊类型时，需要利用 output_parser_registry 转化为 _STANDARD_TYPE：
# def 示例转换函数2(params1:DIY_TYPE)->_STANDARD_TYPE:
#     ...
# output_parser_registry[DIY_TYPE] = 示例转换函数2

# 仅当 input_parser_registry 等无法实现转化，或参数无法位置一一对应时，才需要重写 main_caller* 函数。当 input_params 为元组类型时，请重新设计 main_caller_args ，系统拼接在 <init-code> 之后覆盖原有函数；同理当 input_params 为字典类型时，请重新设计 main_caller_kwargs
```
"""
    CONVERSION_CALLS = """
```conversion.py
# 该代码会拼接在<code>之后运行，无需引用<init-code>中的函数即可调用，其中的 main_caller 会被覆盖。
def main_caller(instance: object, main_method:None,args:？):
    # 当 Solution 类存在多个方法时，必须重写 main_caller 函数。而且 main_method = None，因为不存在唯一的主方法
    # test_case 格式：{"input": input_params}
    params = test_case["input"]
    
    # 在此手动处理调用逻辑，例如：
    # - 参数重新排列
    # - 多方法调用序列
    # - 特殊类型转换（可以重用<init-code>中定义的函数）
    
    # 返回实际执行结果（用于与 output 比较）
    return actual_result
```
"""

    ATTENTIONS_UNIQUE = [
        "<student-code>仅有唯一非魔术方法且默认构造函数无参数，则你不需要调用构造函数，本工程会自动执行 `solution=Solution()`进行构造。",
        "本工程会利用 input_parser_registry 函数尽可能逐个地将输入`input`的参数从 _STANDARD_TYPE 转化为 Solution 所需的自定义类型。",
        "若 input 列表中的参数无法与 Solution 主函数的参数名一一对应，则必须重写`main_caller`函数。"
    ]

    ATTENTIONS_CONVERSION = [
        "不要试图在 {_DEFAULT_TEST_CASES_GENERATOR_FILE_NAME} 直接生成特殊类型的输出，因为这会导致本工程的样例保存中的 JSON 序列化失败。",
        "注意：input_parser_registry 仅能用于一种特殊类型转化为 _STANDARD_TYPE。",
        "若你认为<init-code>无法实现特殊类型与 _STANDARD_TYPE 的转化，你可以参考<conversion>模块实现转化和调用。",
        "输出若为特殊类型，则只需将转换函数加入到 output_parser_registry 中。",
        "若参数数量或顺序无法与函数签名一一对应，必须覆盖`main_caller`函数来手动处理调用逻辑。"
    ]
    
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
"尽量用函数化平滑化设计，少用 if-else，代码应极简。如用负指数分布、对数正态分布、泊松分布等取整代替分段函数。",
"{_DEFAULT_TEST_CASES_GENERATOR_FILE_NAME} 函数的输出必须是 JSON 允许的输入类型。",
"固定样例必须有的放矢，并且计算规模不能大，确保暴力算法可以快速执行。",
"除非题目本身明确说明考察多线程，否则禁止使用 threading 等并发模块，本工程会用完全隔离的多线程环境调用测试代码，你无需考虑多线程。",
"测试用例格式统一为：{\"input\": input_params [, \"output\": 期望值]}，并且 input_params 是否采用字典必须与<request>题目要求一致。`output`则仅在答案驱动型问题下为可选（如这些情况：先知道答案再根据答案构造问题考验学生；模拟类问题中答案可从内部状态中轻松获得，但在学生问题的输入中却比较难以较优复杂度获得答案）。",
    ]
    
    @classmethod
    def get_manual_prompt(cls,codes:str,request:str,is_unique_caller:bool,has_custom_type:bool,attached_attentions:List[str]=[])->str:
        attentions = cls.ATTENTIONS.copy()
        if is_unique_caller:
            attentions.extend(cls.ATTENTIONS_UNIQUE)
        else:
            raise ValueError("暂时未完善非唯一调用器的提示模板")
        if has_custom_type:
            attentions.extend(cls.ATTENTIONS_CONVERSION)
        attentions.extend(attached_attentions)

        conversion = None
        if is_unique_caller:
            if has_custom_type:
                conversion = cls.CONVERSION_UNIQUE
        else:
            conversion = cls.CONVERSION_CALLS
            
        templates = []
        if is_unique_caller:
            templates.append(cls.TEMPLATE_UNIQUE)
        else:
            templates.append(cls.TEMPLATE_CALLS)
            
        return f"<system>{''.join(f"\n{i}. {s}" for i,s in enumerate(cls.SYS_PROMPTS,1))}\n</system>\n<request>\n{request}\n</request>\n<code>\n{codes}</code>\n<template>{'\n'.join(templates)}</template>\n<attentions>{''.join(f"\n- {s}" for s in attentions)}\n</attentions>" + (
            f"<conversion>{conversion}</conversion>" if conversion is not None else ""
            )