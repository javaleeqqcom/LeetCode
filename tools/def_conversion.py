from typing import Optional,List,Callable
import inspect
from .args_parser import _BASE_TYPE,_ARGS,_KWARGS,parse_standard_input,parse_output_to_standard

# 可能的改进：_EXECUTE_CALLER 标准的函数 简化为 两个输入：
# 1. instance_or_func ：当 main_method 不存在时，则代入 Solution 对象，依靠 args 中调用；当 main_method 存在时由父函数传入 bind_func
# 2. args 维持原状

# _EXECUTE_CALLER 标准的函数: Solution 有唯一带参数的非静态方法时，input_params 为元组类型时，系统会自动选择 main_caller_args 函数进行调用（仅检测首个样例，因此必须全样例一致）
def main_caller_args(bind_func: Callable, args:_ARGS)->_BASE_TYPE:

# def main_caller_args(instance: object, main_method:Optional[str],args:_ARGS)->_BASE_TYPE:
    # assert main_method is not None, "当Solution类存在多个方法时，不能采用默认调用方法，必须自定义 main_caller 函数"
    # bind_func = getattr(instance, main_method)

    # 获取函数参数签名
    sig = inspect.signature(bind_func)
    # 先由标准签名绑定器检查参数数量、必填项及位置，避免 zip 静默丢弃
    # 多余参数，或让缺失参数以难懂的下游异常暴露。
    sig.bind(*args)
    formated_args = (
        parse_standard_input(value,sig_type,bind_func.__name__,i) 
        for i,(value , sig_type) in enumerate(zip(args , sig.parameters.values()))
        )

    res = bind_func(*formated_args)
    # 将结果转换为标准输出格式
    return parse_output_to_standard(res)

# _EXECUTE_CALLER 标准的函数: Solution 有唯一带参数的非静态方法时，input_params 为字典类型时，类似地以 main_caller_kwargs 函数进行调用
def main_caller_kwargs(bind_func: Callable, kwargs:_KWARGS)->_BASE_TYPE:

# def main_caller_kwargs(instance: object, main_method:Optional[str],kwargs:_KWARGS)->_BASE_TYPE:
#     assert main_method is not None, "当Solution类存在多个方法时，不能采用默认调用方法，必须自定义 main_caller 函数"
#     bind_func = getattr(instance, main_method)

    # 获取函数参数签名
    sig = inspect.signature(bind_func)
    sig.bind(**kwargs)


    # 仅当 input_params 的键与函数参数名完全一致时，才能进行转换，否则需要单独设计 main_caller_kwargs 函数
    formated_kwargs = {
        # key: parse_standard_input(value, sig.parameters[key].annotation,bind_func.__name__ ,key) # 错误 sig.parameters[key] 是签名类，而 annotation 转为具体，但是 parse_standard_input 内部要求 sig_type 是抽象
        key: parse_standard_input(value, sig.parameters[key],bind_func.__name__ ,key) 
        for key , value in kwargs.items()
    }

    res = bind_func(**formated_kwargs)
    # 将结果转换为标准输出格式
    return parse_output_to_standard(res)

# _EXECUTE_CALLER 标准的函数: Solution 有唯一带参数的非静态方法时，input_params 为字典类型时，类似地以 main_caller_kwargs 函数进行调用
# def main_caller_multi_methods(instance: Callable, args:_ARGS)->_BASE_TYPE:
#     ...
