from typing import Optional,List,Callable
import inspect
from args_parser import _BASE_TYPE,_ARGS,_KWARGS,parse_standard_input,parse_output_to_standard

# _EXECUTE_CALLER 标准的函数: Solution 有唯一带参数的非静态方法时，input_params 为字典类型时，类似地以 main_caller_kwargs 函数进行调用
def main_caller_kwargs(bind_func: Callable, kwargs:_KWARGS)->_BASE_TYPE:

    # 获取函数参数签名
    sig = inspect.signature(bind_func)
    assert len(kwargs) == len(sig.parameters), f"传入 kwargs 字典的参数个数与函数 {bind_func.__name__} 参数个数不匹配"


    # 仅当 input_params 的键与函数参数名完全一致时，才能进行转换，否则需要单独设计 main_caller_kwargs 函数
    formated_kwargs = {
        # key: parse_standard_input(value, sig.parameters[key].annotation,bind_func.__name__ ,key) # 错误 sig.parameters[key] 是签名类，而 annotation 转为具体，但是 parse_standard_input 内部要求 sig_type 是抽象
        key: parse_standard_input(value, sig.parameters[key],bind_func.__name__ ,key) 
        for key , value in kwargs.items()
    }

    res = bind_func(**formated_kwargs)
    # 将结果转换为标准输出格式
    return parse_output_to_standard(res)
