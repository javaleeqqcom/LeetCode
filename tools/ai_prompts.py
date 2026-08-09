# tools/ai_prompts.py

"""
AI 提示词模板库 - 用于测试用例生成等自动化任务
"""
from typing import List, Dict, Any, Union
from .args_parser import _CASE,_BASE_TYPE

_DEFAULT_TEST_CASES_GENERATOR_FILE_NAME = "test_cases_generator"
# 自定义 caller 的命名暂时固定为
_CUSTOM_CALLER_NAME = "custom_caller"

# 待补充，若自定义 caller 必须遵循 _EXECUTE_CALLER 标准，请参考 args_parser.py

# ============================================================================
# 测试用例生成器 - 系统提示词
# ============================================================================
class TEST_CASE_GENERATOR:
    SYS_PROMPTS = [
        "你是信息竞赛测试数据设计专家。",
        "你的任务是生成单个测试用例生成函数 case_generator(scale)。",
        "scale 表示计算规模，而不是严格输入长度。",
        "测试用例生成必须重点覆盖：边界情况、随机情况、极端结构、退化结构、卡复杂度结构。",
        "你只负责生成单个测试用例，不负责批量生成。",
        "除非测试用例可以根据 expected 构造，否则不要生成 expected，外部框架会自动计算。",
        "输出必须是可直接运行的代码。",
        "除注释外不要输出解释。",
        "优先使用 input 元组格式。",
        "仅当参数语义非常复杂时，才允许使用 dict 输入。",
    ]
    
    TEMPLATE_UNIQUE = r'''
```case_generator.py
from typing import Dict, Any
import random as rd
import numpy as np

def case_generator(scale:int) -> Dict[str, Any]:
    """
    scale:
        表示计算规模。
        应根据题目含义映射到:
        - 数组长度
        - 点数
        - 边数
        - 树深度
        - 操作次数
        等。
    """

    # 根据题意限制规模
    n = max(1, int(round(scale)))

    # TODO:
    # 根据题目特点设计：
    # - 边界情况
    # - 极端结构
    # - 随机结构
    # - 卡复杂度结构

    return {
        "input": (
            ...
        )
    }
'''

    TEMPLATE_CALLS=f"""
```{_DEFAULT_TEST_CASES_GENERATOR_FILE_NAME}.py
# 如下代码本工程会拼接到<code>之后运行，无需重复中的代码。所有输出必须可直接运行，非代码的说明必须用注释。
def {_DEFAULT_TEST_CASES_GENERATOR_FILE_NAME}(random_case_num:int [, max_n:int ...])->List[{_CASE.__name__}]:
    # random_case_num：生成的随机样例数量，必含。
    # [, max_n:int ...]：用于指代与问题复杂度相关的参数（可以根据问题修改具体名称，可能为空，也可能不止 1 个参数）

    # 固定用例（用于覆盖各种可预见的边界情况，注意至少有构造函数操作。但是要注意，若学生代码为暴力算法，规模不能过大。）
    res = [
        {{"input": (["Solution",...],[...], ...), "cid":"#1", "expected": [None,...]}}, # 第一个操作必定是构造函数，无返回值
        ...
    ]
    # 上述为`input`无参数名的情况为例，若<request>中的输入有命名，则以字典格式为准

    # 若难以获得期望`expected`，则无需填写`expected`，由学生提交的暴力算法计算得出
    # res = [{{"input": [["Solution",...],[...], ...], "cid":"#1"}}, ...]

    # 可选：由于该问题是多魔术方法的类实现问题，可能需要继承学生的 Solution 类，进行内部状态的窥探，方能生成合法的操作。但是要注意，只有当学生实现正确时，才可窥探其内部状态。否则，可能会导致错误的操作。
    class inner_Solution(Solution):
        ...
    # 可选：因为 Solution 类的接口受到限制，难以设计低复杂度的实现，你也可以选择重新设计，但是注意最终的目标是为了检验 Solution 的实现是否正确。
    class easy_Solution:
        ...

    def 单随机样例生成器 f(规模参数)->Dict[str, {_BASE_TYPE.__name__}]:
        # 返回格式：{{"methods":["Solution",...],"params":[(__init__的args参数),...其余方法的参数（也可能为空元组表示无参数调用）]}}
        # 上述为`input`有参数名的情况为例，若<request>中的输入无参数名，则应返回元组格式的 `input` 值。若可以轻松获得期望`expected`，则应填写`expected`值。

        # 对于多方法调用问题，input 列表应包含所有操作所需的参数（按调用顺序）
        ...
        # obj = inner_Solution(...) # 若定义了 inner_Solution ，可以利用其辅助构建用例
        ...
    
    # --- 规模参数生成 (Outside the main loop) ---
    # 采用负指数分布生成规模，并排序，确保 n 随 i 增大而增大
    # 生成 random_case_num 个规模参数
    scales = []
    lam = 3.0 / max_n  # 调整 lambda 以适应 max_n 的范围
    
    for _ in range(random_case_num):
        # 使用负指数分布生成随机数，确保小规模数据多，大规模数据少
        sample = random.expovariate(lam)
        # 将生成的浮点数限制在有效范围内并转为整数
        # 长度=1的只需生成一次
        n = max(2, min(max_n, int(sample)))
        scales.append(n)
    
    # 关键步骤：在外面生成并排序
    # 这样可以保证测试用例从小规模到大规模排列，避免大用例卡死
    scales.sort()
    
    # 生成随机用例（注意若使用了 inner_Solution ，则需注意其复杂度，若`复杂度(规模)`过高，可能会影响测试效率）
    for i, n in enumerate(scales):
        ...

        res.append({{
            "input":单随机样例生成器 f(规模参数...),
            "cid":i
        }})
    return res
```
f"""

    CONVERSION_UNIQUE = f"""
```conversion.py
# 丰富 input_parser_registry 转换器（可选）如遇到新的数据类型，可以参考  添加对应的转换器
# def 示例转换函数1(params1:{_BASE_TYPE.__name__})->Any: # 注意禁止使用 lambda 等不可序列化对象，因为这会导致多线程无法复制环境变量
#     ...
# input_parser_registry[({_BASE_TYPE.__name__},Any)] = 示例转换函数1

# 当返回值为特殊类型时，需要利用 output_parser_registry 转化为 _STANDARD_TYPE：
# def 示例转换函数2(params1:Any)->{_BASE_TYPE.__name__}:
#     ...
# output_parser_registry[Any] = 示例转换函数2

# 仅当 input_parser_registry 等无法实现转化，或参数无法位置一一对应时，请根据你的需要写一个 {_CUSTOM_CALLER_NAME} 函数。下面以链表环节点检测问题为例，其输入参数为 (head_list, pos) 元组形式，示例如下：
def {_CUSTOM_CALLER_NAME}(bind_func: Callable, args:_ARGS)->_BASE_TYPE:
    # 将测试用例 (head_list, pos) 转换为 Solution.detectCycle 所需的参数。
    # bind_func 返回的节点需要转化为位置值，-1 表示无环。
    head_list, pos = args
    assert isinstance(head_list, list)
    assert isinstance(pos,int) and -1<=pos<len(head_list)

    # 空链表
    if not head_list:
        return -1

    # 构造所有节点并排列为list（尽量利用 args_parser.py 已有函数简化设计）
    nodes = ListNode_flatten(List2ListNode(head_list),len(head_list))

    # 根据 pos 设置环
    if pos != -1: # 有环
        nodes[-1].next = nodes[pos]

    # 调用学生提交的函数
    circle = bind_func(nodes[0])

    # 检查学生是否改变链表结构
    assert ListNode_flatten(nodes[0],len(head_list)) == nodes

    # 计算环的相对位置
    if circle is None:
        return -1
    else:
        for res,cur in enumerate(nodes):
            if cur == circle:
                return res
        raise ValueError(f"{{bind_func.__name__}}返回值非法!")
```
"""
    
    CONVERSION_CALLS = f"""
```conversion.py
# 该代码会拼接在<code>之后运行，无需引用<init-code>中的函数即可调用，其中的 {_CUSTOM_CALLER_NAME} 会被覆盖。
def {_CUSTOM_CALLER_NAME}(instance: object, args:_PARAMS)->{_BASE_TYPE.__name__}:
    # 当 Solution 类存在多个方法时，runner 会把 Solution 实例和
    # test_case["input"] 传入本函数。
    params = args
    
    # 在此手动处理调用逻辑，例如：
    # - 参数重新排列
    # - 多方法调用序列
    # - 特殊类型转换（可以重用<init-code>中定义的函数）
    
    # 返回实际执行结果（用于与 expected 比较）
    return actual_result
```
"""

    ATTENTIONS_UNIQUE = [
        "<student-code>仅有唯一非魔术方法且默认构造函数无参数，则你不需要调用构造函数，本工程会自动执行 `solution=Solution()`进行构造。",
        "本工程会利用 input_parser_registry 函数尽可能逐个地将输入`input`的参数从 {_BASE_TYPE.__name__} 转化为 Solution 所需的自定义类型。",
        "若 input 列表中的参数无法与 Solution 主函数的参数名一一对应，则必须重写`{_CUSTOM_CALLER_NAME}`函数。"
    ]

    ATTENTIONS_CONVERSION = [
        "不要试图在 {_DEFAULT_TEST_CASES_GENERATOR_FILE_NAME} 直接生成特殊类型的输出，因为这会导致本工程的样例保存中的 JSON 序列化失败。",
        "注意：input_parser_registry 仅能用于一种特殊类型转化为 _STANDARD_TYPE。",
        "若你认为<init-code>无法实现特殊类型与 {_BASE_TYPE.__name__} 的转化，你可以参考<conversion>模块实现转化和调用。",
        "输出若为特殊类型，则只需将转换函数加入到 output_parser_registry 中。",
        "若参数数量或顺序无法与函数签名一一对应，必须覆盖`{_CUSTOM_CALLER_NAME}`函数来手动处理调用逻辑。"
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
"测试用例格式统一为：{\"input\": input_params [, \"expected\": 期望值]}，并且 input_params 是否采用字典必须与<request>题目要求一致。`expected`则仅在答案驱动型问题下为可选（如这些情况：先知道答案再根据答案构造问题考验学生；模拟类问题中答案可从内部状态中轻松获得，但在学生问题的输入中却比较难以较优复杂度获得答案；可以仅填写部分样例的expected，如模拟判定类问题，部分回答如真（或假）可以简单判定，则仅填写expected为真的样例）。",
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
