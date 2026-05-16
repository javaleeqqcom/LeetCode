from typing import Optional,List,Callable
import inspect
from args_parser import _BASE_TYPE,_ARGS,_KWARGS,parse_standard_input,parse_output_to_standard

# _EXECUTE_CALLER 标准的函数: Solution 有唯一带参数的非静态方法时，input_params 为元组类型时，系统会自动选择 main_caller_args 函数进行调用（仅检测首个样例，因此必须全样例一致）
def main_caller_args(bind_func: Callable, args:_ARGS)->_BASE_TYPE:

    # 获取函数参数签名
    sig = inspect.signature(bind_func)
    formated_args = (
        parse_standard_input(value,sig_type,bind_func.__name__,i) 
        for i,(value , sig_type) in enumerate(zip(args , sig.parameters.values()))
        )

    res = bind_func(*formated_args)
    # 将结果转换为标准输出格式
    return parse_output_to_standard(res)
