# tools/solution_runner.py
import os,sys,io
import math
import inspect
from pathlib import Path
import logging
import datetime, time
from typing import Any, Callable, Dict, List, Tuple, Union, Optional, get_type_hints, get_args, get_origin
import ast, re, json
import types
import traceback
# from charset_normalizer.api import from_bytes  # 自动检测编码（与py3.14多线程不兼容）
from concurrent import futures,interpreters
from functools import partial  # 固定 test_queue 参数之用于多线程调用
from heapq import merge

__DEBUG__ = False
__FULL_PATH__ = False

# ========== 安全导入：基于当前文件路径 ==========
# 获取 solution_runner.py 所在目录（即 tools 目录）
_TOOLS_DIR = Path(__file__).resolve().parent
# 将 tools 目录添加到 sys.path，确保模块可导入
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
elif os.path.exists(_TOOLS_DIR/"tools"):
    _TOOLS_DIR = _TOOLS_DIR/"tools"
    sys.path.insert(0, str(_TOOLS_DIR))
if __DEBUG__:
    print(f"tools dir:{_TOOLS_DIR}")

# 直接导入，无需 try-except
from tools.examples_parser import parse_test_cases
from tools.args_parser import _STANDARD_TYPE,_CASE_TYPE,_DEFAULT_TEST_CASES_GENERATOR_FILE_NAME
from tools.compacted_json import CompactedJson
from tools.ai_prompts import TEST_CASE_GENERATOR

"""
一个标准的测试样例的格式为：
    - 字典: {"input": case [,"output":Any, "expected":Any,"error":str , ...]}
    - 其中的 case 可以是：
        - 字典：其键为被测函数的变量名，其值则为变量值
        - 元组：按被测函数的变量顺序排列的变量值
"""

# ========== 全局辅助函数（放在类外部或类内静态方法）==========
_compacted_json = CompactedJson(hex_len=16)

def _sanitize_filename(name: str) -> str:
    """安全文件名转换"""
    for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        name = name.replace(ch, '_')
    return name.strip().rstrip('.')

def _create_solution_module(source_code_lst: List[Optional[str]])-> types.ModuleType:
    """
    创建黑箱执行器代码字符串
    ⚠️ 不导入任何学生代码可能用的库
    返回黑箱函数
    """
    _types = __import__("types")

    module = _types.ModuleType('solution_module')
    module.__dict__.update({
        '__builtins__': __builtins__,
        '__name__': 'solution_module',
        '_sys':__import__("sys"),
    })
    # 将 tools 目录添加到 sys.path，确保模块可导入
    _sys_path = module.__dict__['_sys'].path
    if str(_TOOLS_DIR) not in _sys_path:
        _sys_path.insert(0, str(_TOOLS_DIR))

    for source_code in source_code_lst:
        if source_code is not None:
            exec(source_code, module.__dict__)
    return module

def _get_unique_log_path(relPath: os.PathLike, file_name: str) -> Path:
    """生成唯一的日志文件路径（保存到 self.relPath 目录下）"""
    # 确保 relPath 是一个路径对象
    log_dir = Path(relPath)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 确保文件名以 .log 结尾
    if not file_name.endswith('.log'):
        file_name += '.log'
    
    # 生成完整路径
    log_path = log_dir / _sanitize_filename(file_name)
    
    # 如果文件已存在，添加序号
    if log_path.exists():
        stem = log_path.stem
        suffix = log_path.suffix
        counter = 1
        while True:
            new_name = f"{stem}_{counter}{suffix}"
            log_path = log_dir / new_name
            if not log_path.exists():
                break
            counter += 1
    
    return log_path
    
def _is_wrong(result:_EXPECTED_CASE)->bool:
    return 'expected' in result and 'output' in result and result['expected'] != result['output']

def _log_result(result:_EXPECTED_CASE,log_lines:List,log_prefix:str = "",log_path:Optional[os.PathLike]=None):
    log_path = _get_unique_log_path( 
        Path(os.getcwd() if log_path is None else log_path)
        , f"{log_prefix}_{result['cid']}.log"
        )
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_lines))
    return log_path
        
def _geom_queue_generator( test_cases: List[Any], queue: interpreters.Queue, rate: float = 0.1) -> int:
    """将测试用例分割为若干个子列表，越往后子列表的大小呈等比递减，以便维持各线程基本同时收工"""
    group_id, idx = 0, 0
    # 将剩余的用例按 rate 递减加入到 queue 中，至少要有 1 个用例
    while idx < len(test_cases):
        chunk_size = max(1, int((len(test_cases) - idx) * rate))
        queue.put((group_id, test_cases[idx:idx+chunk_size]))
        idx += chunk_size
        group_id += 1
    return group_id

def _execute_dict_case(
    caller: Callable,
    instance:'学生代码中的"Solution"类的实例',
    case: _EXPECTED_CASE,
    main_method:Optional[str]=None
) -> Tuple[_EXPECTED_CASE, List[str]]:
    """执行单个测试用例（核心封装）"""
    log_lines = []
    result_dict = case.copy()
    # 日志格式
    def _add_log(content: str):
        log_lines.append(f"{case['cid']}:\t{content}")
    
    original_stdout = None
    try:
        _add_log(f"Running '{the_fun.__name__}' with case: {case.get('test_case_key', f"{case['cid']}")}")
        
        input_val = case['input']
        if exchange is None:
            # 获取函数参数签名
            sig = inspect.signature(the_fun)
            
            assert isinstance(input_val,dict)
            
            _add_log(f">>> INPUT\n{_compacted_json.dumps(input_val, indent=2)}")

            format_input = {
                key:_exchange_DIY_types(
                        the_fun,
                        sig.parameters[key].annotation,
                        value,
                        f"参数 {key}"
                        )
                for key,value in input_val.items()
            }            
        else:
            
            _add_log(f">>> INPUT\n{_compacted_json.dumps(input_val, indent=2)}")

            format_input = exchange(input_val)

        # 保存原始 stdout
        original_stdout = sys.stdout

        # 创建字符串缓冲区捕获 print 输出
        captured_output = io.StringIO()
        # 重定向 stdout
        sys.stdout = captured_output
        output = the_fun(**format_input)

        # 恢复 stdout
        sys.stdout = original_stdout
        # 获取并记录 print 内容
        print_content = captured_output.getvalue()
        if print_content.strip():
            _add_log(f">>> PRINT OUTPUT:\n{print_content}")

        # 将其转化为 LeetCode 的通用的输出类型（原生 JSON 的输入类型）
        output = parse_output_to_standard(output)
        
        elapsed = time.perf_counter() - time.perf_counter()
        result_dict['output'] = output
        result_dict['elapsed'] = elapsed
        _add_log(f"<<< OUTPUT (elapsed: {elapsed:.6f}s)\n{_compacted_json.dumps(output, indent=2)}")
        
    except Exception as e:
        # 异常时也恢复 stdout
        if original_stdout is not None:
            sys.stdout = original_stdout
        elapsed = time.perf_counter() - time.perf_counter()
        result_dict['error'] = str(e)
        result_dict['traceback'] = traceback.format_exc()
        result_dict['elapsed'] = elapsed
        _add_log("!!! EXCEPTION OCCURRED:")
        _add_log(traceback.format_exc())
    
    return result_dict, log_lines

def _execute_in_interpreter_worker(
    interpreter_id: int,
    source_code_lst: List[Optional[str]],
    method_name:str,
    group_queue: interpreters.Queue,
    output_queue: interpreters.Queue,
    early_stop_queue: interpreters.Queue,
    log_path:os.PathLike,
    skip_error = False,
    log_wrong = True,
) -> tuple:
    """
    模块级 worker 函数，在子解释器中执行测试用例
    所有参数必须是可共享的基本类型（字符串、整数）
    """
    if __DEBUG__:
        print(f"线程{interpreter_id}：开始")
    # ========== 所有导入在子解释器内部完成 ==========

    # 创建子解释器的环境模块
    module = _create_solution_module(source_code_lst)

    if __DEBUG__:
        print(f"\n线程{interpreter_id}: 队列重建成功",end="")

    # 创建 Solution 实例和方法
    instance = module.__dict__['Solution']()
    the_fun = getattr(instance,method_name)
    if _EXCHANGE_FUN_NAME in  module.__dict__:
        _exchange = module.__dict__[_EXCHANGE_FUN_NAME]
        assert callable(_exchange) and (inspect.isfunction(_exchange) or inspect.ismethod(_exchange)), f"环境中定义了非法的 {_EXCHANGE_FUN_NAME} 变量，该变量固定为输入转换函数，不可为其他用途。"
    else:
        _exchange = None
    
    start_time = time.time()
    process_case_num = 0

    if __DEBUG__:
        print(f"\n线程{interpreter_id}：成功创建 Solution 实例和方法。",end="")
    
    try:
        while early_stop_queue.empty():
            try:
                group_id, cases = group_queue.get_nowait()
            except interpreters.QueueEmpty:
                if group_queue.empty():
                    break
                time.sleep(0.001)
                continue
            
            results_buff = []
            wrong_count = 0
            
            for case in cases:
                result,log_lines = _execute_single_case(the_fun,case,_exchange)

                if 'error' in result:
                    error_log_path = _log_result(result,log_lines,"ERROR_",log_path)
                    if skip_error:
                        Warning(f"\n跳过报错用例（已经保存日志到 {error_log_path}）")
                        wrong_count += 1 # error 当然也算“错误”
                    else:
                        # 出现报错，触发早停，以分组编号作为早停信息
                        early_stop_queue.put(group_id)
                        raise Exception(f"\n执行报错（已经保存日志到 {error_log_path}）：\n{result['error']}")
                elif _is_wrong(result): 
                    if log_wrong:
                        _log_result(result,log_lines,"Wrong_",log_path)
                    wrong_count += 1 

                results_buff.append(result)
            
            # 将 (分组id，该组错误数量，改组结果列表) 加入到输出队列
            output_queue.put((group_id, wrong_count, results_buff))
            process_case_num += len(results_buff)
            
            if __DEBUG__:
                print(f"\n解释器 {interpreter_id}: 完成组 {group_id} ({len(results_buff)} 个用例)",end="")
        
    except Exception as e:
        early_stop_queue.put(None) # 早停所有线程
        raise Exception(f"\n解释器 {interpreter_id}: 顶层异常 {type(e).__name__}: {e}")
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    if __DEBUG__:
        print(f"解释器 {interpreter_id}: 处理 {process_case_num} 个用例耗时：{elapsed:.3f}s")
    
    return (interpreter_id, process_case_num, elapsed)

class SolutionRunner:
    @classmethod
    def _read_code(cls, code_file: os.PathLike) -> str:
        assert os.path.exists(code_file), f"文件不存在: {code_file}"
        # 确保文件类型为 ".py"
        assert str(code_file).endswith('.py'), f"应当输入 .py 文件，实际为: {code_file}"
        with open(code_file, 'r',encoding='utf-8') as f:
            code = f.read()
        return code

        # 1. 读取并自动检测编码（支持中文）
        # with open(code_file, 'rb') as f:
        #     raw = f.read()
        # result = from_bytes(raw).best()
        # return str(result) if result else raw.decode('utf-8', errors='ignore')

    def __init__(self, solution_file: os.PathLike, main_method: Optional[str] = None) -> None:
        """
        初始化 SolutionRunner，自动加载学生代码文件。
        :param solution_file: 学生代码文件路径（如 "P82_V0.py"）
        :param main_method: 指定主方法名（当Solution有多个方法时），默认None表示自动选择唯一方法
        """
        # 1. 读取并自动检测编码（支持中文）
        self.student_code = self._read_code(solution_file)
        self.solution_file = solution_file

        # 2. 读取预执行代码（如果有）
        self.pre_code = self._read_code(_TOOLS_DIR/"custom_init.py")
        
        # 从 solution_file 路径中提取相对目录（即文件所在目录）
        solution_path = Path(solution_file).resolve()
        self.relPath = solution_path.parent
        self.file_name = os.path.splitext(os.path.basename(solution_path))[0]

        # 2. 创建 solution 的虚拟环境
        self.solution_module = _create_solution_module([self.pre_code ,self.student_code])

        # 4. 获取Solution类
        if 'Solution' not in self.solution_module.__dict__:
            raise ValueError("学生代码中未定义 Solution 类")
        module_Solution = self.solution_module.__dict__['Solution']

        # 5. 提取主方法名
        methods = []
        for name, method in inspect.getmembers(module_Solution, predicate=inspect.isfunction):
            if not (name.startswith('__') and name.endswith('__')):
                methods.append((name, method))
        
        if main_method is not None:
            # 使用指定的方法名
            method_dict = dict(methods)
            if main_method not in method_dict:
                raise ValueError(f"指定的主方法 '{main_method}' 不存在于 Solution 类中")
            self.main_method = main_method
        else:
            # 自动选择唯一方法
            if len(methods) == 1:
                self.main_method, _ = methods[0]
            else:
                print("存在多个方法，执行时必须定义 solution_callers 才能使用 run 及任何后继方法！")
                self.main_method = None # 用 None 表示可调用方法不唯一

        if self.main_method is not None:
            # 6. 提出主方法的参数名和参数类型
            self.instance = module_Solution()
            self.sig  = inspect.signature(getattr(self.instance, self.main_method))
            self.sig_names = list(self.sig.parameters.keys())
            self.sig_types = [v.annotation for v in self.sig.parameters.values()]

            self.has_custom_type = not all(_is_standard_type(t) for t in self.sig_types)

            if __DEBUG__:
                print(f"sig.parameters: {self.sig.parameters}")
                print(f"主方法参数名: { self.sig_names}")
                print(f"主方法参数类型: { self.sig_types }")
        else:
            self.has_custom_type = None

        self.test_cases_generator_code = None
        self.exchange_code = None

    def try_read_cases_and_exchange_codes(self)->bool:
        if (self.relPath/"test_cases_generator.py").exists():
            with open(self.relPath/"test_cases_generator.py", "r", encoding="utf-8") as f:
                self.test_cases_generator_code = f.read()
            if self.has_custom_type is False: # 无自定义类型，不需要 exchange code
                return True
            elif (self.relPath/"exchange.py").exists():
                with open(self.relPath/"exchange.py", "r", encoding="utf-8") as f:
                    self.exchange_code = f.read()
                # 将转换函数导入到 solution_module 中
                exec(self.exchange_code , self.solution_module.__dict__)
                if _EXCHANGE_FUN_NAME not in self.solution_module.__dict__:
                    raise ValueError(f'文件{self.relPath/"exchange.py"}未定义 {_EXCHANGE_FUN_NAME} 函数。')
                _exchange = self.solution_module.__dict__[_EXCHANGE_FUN_NAME]
                assert callable(_exchange) and (inspect.isfunction(_exchange) or inspect.ismethod(_exchange)), f'文件{self.relPath/"exchange.py"}定义了非法的 {_EXCHANGE_FUN_NAME} 变量，该变量固定为输入转换函数，不可为其他用途。'
                return True
        return False

    def test_cases_generator(self,*args,**kwargs)->Union[List[_EXPECTED_CASE] , List[_ARGS_CASE]]:
        if self.test_cases_generator_code is None:
            raise Exception("请先执行 test_cases_generator_code 并成功返回 True.")
        exec( self.test_cases_generator_code ,self.solution_module.__dict__)
        _test_cases_generator = self.solution_module.__dict__['test_cases_generator']
        cases = _test_cases_generator(*args,**kwargs)
        is_dict = None
        for i in range(len(cases)):
            if isinstance(cases[i],dict):
                assert not(is_dict is False),f"前{i-1}个测试用例是元组类型，而第{i}个测试用例则是字典类型，格式不统一。"
                assert "expected" in cases[i] and "input" in cases[i], f"第{i}个测试用例是 _EXPECTED_CASE 类型，但是缺少`input`或`expected`键。"
                cases[i]["cid"] = f"#{self.relPath.stem}_{i}"
                is_dict = True
            else:
                assert isinstance(cases[i],tuple), f"第{i}个测试用例既不是字典类型也不是元组类型。"
                assert not(is_dict is True),f"前{i-1}个测试用例是字典类型，而第{i}个测试用例不是，格式不统一。"
                is_dict = False
        return cases

    def read_test_case(
        self,
        path_list: Union[os.PathLike, List[os.PathLike]] = []
    ) -> List[_CASE_TYPE]:
        """读取并解析测试用例文件（支持 _CASE_TYPE 格式，兼容元组和字典），若无指定文件名则尝试查找默认样例文件"""
        _path_list = path_list if isinstance(path_list, list) else [path_list]
        if 0==len(_path_list):
            _path_list = list(Path(self.relPath).glob("*.json"))
            if 0 == len(_path_list):
                raise ValueError(f"read_test_case: path_list 为空，已尝试查找默认样例文件，但未找到，请检查当前目录{self.relPath}。")
            else:
                print(f"read_test_case: path_list 为空，已尝试查找默认样例文件，找到{len(_path_list)}个样例文件。")

        test_cases = []
        global_is_ARGS = False  # 用于跨文件检测格式一致性
        global_is_KWARGS = False
        
        for p in _path_list:
            file_path = Path(p) if os.path.exists(p) else Path(self.relPath) / p
            assert file_path.exists(), f"read_test_case: {file_path} 文件不存在"

            def _format_input(case:_CASE_TYPE,i:int)->_CASE_TYPE:
                nonlocal global_is_ARGS,global_is_KWARGS,file_path
                # JSON 必须是标准格式（含"input"键）
                assert isinstance(case, dict) and 'input' in case,'格式非法，JSON 样例文件不含"input"键。'
                
                # 判断当前 case 的格式
                if isinstance(case['input'], dict):
                    assert global_is_ARGS is False, f"样例文件 {file_path if __FULL_PATH__ else file_path.stem} 中第 {i+1} 个样输入类型不一致，前面是元组 _ARGS 类型"
                    global_is_KWARGS = True
                    
                elif isinstance(case['input'], list):
                    assert global_is_KWARGS is False, f"样例文件 {file_path if __FULL_PATH__ else file_path.stem} 中第 {i+1} 个样输入类型不一致，前面是字典 _KWARGS 类型"
                    global_is_ARGS = True
                    
                    # 统一转换为元组便于代入函数调用
                    case['input'] = tuple(case['input'])

                else:
                    raise ValueError(f"文件 {file_path if __FULL_PATH__ else file_path.stem} 第 {i+1} 个用例 input 类型不正确，实际为 {type(case['input'])}")

                # 添加 cid
                case['cid'] = f"{file_path if __FULL_PATH__ else file_path.stem}_{i}"
                return case

            # ========== 根据文件后缀分流处理 ==========
            if file_path.suffix.lower() == '.json':
                # 1. 处理 JSON 文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                
                assert isinstance(raw_data,list)
                for i, item in enumerate(raw_data):
                    test_cases.append(_format_input(item, i))
            else:
                # 2. 处理 TXT 文件（兼容旧格式）
                try:
                    parsed_list = parse_test_cases(file_path)
                    
                    for i, item in enumerate(parsed_list):
                        # 如果已经是标准格式
                        if isinstance(item, dict) and 'input' in item:
                            test_cases.append(_format_input(item, i))
                        else:
                            test_cases.append(_format_input({'input': item}, i))
                except Exception as e:
                    raise RuntimeError(f"解析测试文件失败：{file_path}") from e
    
        return test_cases

    def run_as_expected(self, 
        test_cases: Union[List[_EXPECTED_CASE] , List[_ARGS_CASE]], 
        thread: int = 1,
        skip_error: bool = False,
        timeout_s: Optional[float] = 10
    )-> List[_EXPECTED_CASE]:
        # ========== 自动处理 test_cases 为元组列表的情况 ============
        assert isinstance(test_cases, list), "test_cases 必需是 list 类型"
        is_tuples = list(map(lambda x: isinstance(x, tuple),test_cases))
        if all(is_tuples):
            # 如果是元组列表，则尝试按 self.method 的签名转换为标准 _CASE_TYPE 列表
            test_cases = self.tuple_to_cases(test_cases)
        else:
            assert not any(is_tuples), "run_as_expected(test_cases) 不支持混合元组和非元组的情况"
        
        output = self.run(test_cases,log_wrong = False,thread = thread,skip_error = skip_error,timeout_s=timeout_s)
        expected_results = self.get_expected_cases(output)

        return expected_results

    def run(
        self,
        test_cases: List[_EXPECTED_CASE],  # 严格要求是 List[CASE_TYPE]
        log_wrong: bool = True,        # 默认记录错误的测试样例
        log_folder: Optional[str] = None,
        early_stop: Optional[Union[int, float]] = None,
        skip_error = False,
        thread: int = 1,
        timeout_s: Optional[float] = 10,
        summary: bool = False,
        check_cases_format = True
    ) -> List[_EXPECTED_CASE]:
        """执行测试用例（自动处理实例化）"""
        # ========== 1. 验证输入格式 ==========
        if check_cases_format:
            assert isinstance(test_cases, list), "test_cases 必需是 list 类型"
            for case in test_cases:
                if not isinstance(case, dict):
                    raise ValueError(f"测试用例 {case['cid']} 必须至少含有 'input' 键的字典类型")
                if 'input' not in case:
                    raise ValueError(f"测试用例 {case['cid']} 缺少 'input' 键")
                if not isinstance(case['input'], (dict, tuple)):
                    raise ValueError(f"测试用例 {case['cid']} 的 'input' 必须是字典或元组")
            
        # 日志路径
        log_path = self.relPath / (self.file_name if log_folder is None else log_folder)
        os.makedirs(log_path,exist_ok=True)

        if __DEBUG__:
            print("log_path:",log_path)
        # ========== 2. 执行所有用例 ==========
        if -1==thread:
            cpu_count = os.cpu_count()
            thread = cpu_count if cpu_count else 1
        if 1==thread:
            wrong_count = 0
            results = []
            
            for case in test_cases:

                if self.main_method is not None:
                    # 执行单用例（核心封装，便于多进程改造）
                    result, log_lines = _execute_dict_case(
                        getattr(self.instance, self.main_method),
                        case=case,
                        exchange=self.solution_module.__dict__[_EXCHANGE_FUN_NAME]
                    )
                else:
                    raise Exception("暂不支持无 self.main_method 的情况")
            
                results.append(result)

                if 'error' in result:
                    error_log_path = _log_result(result,log_lines,"ERROR_",log_path)
                    if skip_error:
                        Warning(f"跳过报错用例（已经保存日志到 {error_log_path}）")
                        wrong_count += 1 # error 当然也算“错误”
                    else:
                        raise Exception(f"执行报错（已经保存日志到 {error_log_path}）：\n{result['error']}")
                elif _is_wrong(result): 
                    if log_wrong:
                        _log_result(result,log_lines,"Wrong_",log_path)
                    wrong_count += 1 
                    if self._check_early_stop( len(results), wrong_count ,early_stop):
                        break # 触发早停
        else:
            # 创建共享队列
            group_queue = interpreters.create_queue()
            output_queue = interpreters.create_queue()
            early_stop_queue = interpreters.create_queue()
            
            # 分割测试用例到队列
            groups_num = _geom_queue_generator(test_cases, group_queue, rate=1.0/thread)
            
            with futures.InterpreterPoolExecutor(max_workers=thread) as executor:
                futures_list:List[futures.Future] = []
                for i in range(thread):
                    if self.main_method is not None:
                        fut = executor.submit(
                            _execute_in_interpreter_worker,
                            i,
                            [self.pre_code,self.student_code,self.exchange_code],  # 传递代码字符串
                            self.main_method,
                            group_queue,
                            output_queue,
                            early_stop_queue,
                            log_path
                            # 不直接传递 test_cases，而是从队列获取
                        )
                        futures_list.append(fut)
                    else:
                        raise Exception("暂不支持无 self.main_method 的情况")
                
                # 收集结果（带超时）
                try:
                    worker_results = [f.result(timeout=timeout_s) for f in futures_list]
                    print(f"所有工作线程完成，结果为 (组ID，处理的样例数量，花费时间秒)：{worker_results}")
                except TimeoutError:
                    print(f"⚠️ 执行超时 ({timeout_s}s)")
                
                # 收集输出队列结果
                output_buff = [None]*groups_num
                output_count,wrong_count = 0,0
                total_count = len(test_cases)
                
                while output_count < total_count and (
                        early_stop_queue.empty() or any(fut.running() for fut in futures_list)  
                    ):  # 当出现早停信号时，需要检测是否所有子线程均已停止
                    try:
                        group_id, wcnt ,results = output_queue.get(timeout=timeout_s)
                        if group_id is not None:
                            output_buff[group_id] = results
                            output_count += len(results)
                            wrong_count += wcnt
                            print(f"主线程：(已收集/总样例数): ({output_count}/{total_count})",end= "\r")
                            # 检查结果错误数量是否满足早停（非运行错误！）
                            if self._check_early_stop( output_count, wrong_count ,early_stop):
                                early_stop_queue.put(group_id) # 向子线程发出早停信号
                    except interpreters.QueueEmpty:
                        continue
                print("")

            import itertools
            outputs:List[List[Any]] = list(filter(bool,output_buff))
            # 合并结果
            results = [res for output in outputs for res in output]

        if summary:
            self.summary_results(results,verbose=True)
        return results    

    @classmethod
    def summary_results(cls,results:List[_EXPECTED_CASE],verbose = True)-> Tuple[int,int]:
        right = valid = 0
        for case in results:
            if 'expected' in case and 'output' in case:
                valid += 1
                if case['expected'] != case['output']:
                    print(f"wrong: {case}")
                else:
                    right += 1
        if verbose:
            print(f"right / total_valid: {right} / {valid}")
        return right,valid

    @classmethod
    def _check_early_stop(cls,total_cnt:int,wrong_count:int,early_stop:Optional[int|float]=None,verbose=True)->bool:
        """检查是否触发早停"""
        if early_stop is None:return False
        if early_stop < 1:
            if(verbose):print(f"错误样例比例 = {wrong_count}/{total_cnt} = {wrong_count/total_cnt:.4f} > {early_stop:.4f} (阈值)，触发早停。")
            return wrong_count > early_stop*total_cnt
        else:
            if(verbose):print(f"错误样例数量 = {wrong_count} >= {math.ceil(early_stop):d} (阈值)，触发早停。")
            return wrong_count >= early_stop


    def get_expected_cases(self, run_results: List[_EXPECTED_CASE]) -> List[_EXPECTED_CASE]:
        """从run结果中过滤出成功的测试用例，重新编号以#开头的cid，并将'output'重命名为'expected'"""
        expected_cases = []
        case_id = 0
        total_count = len(run_results)
        
        for result in run_results:
            if 'error' not in result:
                case_id += 1
                output = result.copy()

                # print(f"output={output}")

                output['cid'] = f"#{self.relPath.stem}_{case_id}"
                output['expected'] = output.pop('output')
                output.pop('elapsed', None)
                expected_cases.append(output)

        print(f"✅ 从 {total_count} 个测试用例中筛选出 {case_id} 个有效用例")
        return expected_cases
    
    def auto_path_cases(self) -> Path:
        base_name = os.path.splitext(os.path.basename(self.solution_file))[0]
        # 保存到相对目录下
        return self.relPath / f"{base_name}.json"

    def save_test_cases(self, test_cases: List[_EXPECTED_CASE], file_path: Optional[os.PathLike] = None) -> Path:
        """保存测试用例到JSON文件"""
        if file_path is None:
            file_path = self.auto_path_cases()
        else:
            # 确保文件路径的目录存在
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(
                _compacted_json.dumps(test_cases, indent=2, ensure_ascii=False)
            )
        
        print(f"💾 已保存 {len(test_cases)} 个测试用例到: {file_path}")
        return Path(file_path)
    
    def get_cases_generator(self,documentation:Union[os.PathLike,str],AI=None,attached_attentions:List[str]=[])->str:
        """自动向AI提问得到问题的测试样例生成器"""
        if not os.path.exists(documentation):
            documentation = self.relPath/documentation
        with open(documentation , encoding="utf-8") as fp:
            request_text = fp.read()
        codes = f"<init-code>\n{self.pre_code}\n</init-code>\n<student-code>\n{self.student_code}\n</student-code>"
        if AI is not None:
            raise ValueError("暂时不支持自动提问")
            return None
        # AI 未指定，或者网络等错误

        # self.main_method 为 None时，无法检测 self.has_custom_type ，因此依靠 is_unique_caller 兜底，而将 has_custom_type 视为 False
        return TEST_CASE_GENERATOR.get_manual_prompt(codes,request_text, self.main_method is not None ,bool(self.has_custom_type),attached_attentions)
    