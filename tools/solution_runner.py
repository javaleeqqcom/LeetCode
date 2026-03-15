# tools/solution_runner.py
import os,sys,io
import inspect
from pathlib import Path
import logging
import datetime, time
from typing import Any, Callable, Dict, List, Tuple, Union, Optional, get_type_hints
import ast, re, json
import types
import traceback
# from charset_normalizer.api import from_bytes  # 自动检测编码（与py3.14多线程不兼容）
from concurrent import futures,interpreters
from functools import partial  # 固定 test_queue 参数之用于多线程调用
from heapq import merge

__DEBUG__ = True

# ========== 安全导入：基于当前文件路径 ==========
# 获取 solution_runner.py 所在目录（即 tools 目录）
_CURRENT_DIR = Path(__file__).resolve().parent
# 将 tools 目录添加到 sys.path，确保模块可导入
if str(_CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_DIR))

# 直接导入，无需 try-except
from examples_parser import parse_test_cases
from custom_init import input_parser_registry, ListNode, TreeNode, Optional, List, Dict
from compacted_json import CompactedJson

"""
一个标准的测试样例的格式为：
    - 字典: {"input": case [,"output":Any, "expected":Any,"error":str , ...]}
    - 其中的 case 可以是：
        - 字典：其键为被测函数的变量名，其值则为变量值
        - 元组：按被测函数的变量顺序排列的变量值
"""
_CASE_TYPE = Dict[str, Union[Dict[str, Any], Tuple, Any]]

# ========== 全局辅助函数（放在类外部或类内静态方法）==========
_compacted_json = CompactedJson(hex_len=16)

def _sanitize_filename(name: str) -> str:
    """安全文件名转换"""
    for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        name = name.replace(ch, '_')
    return name.strip().rstrip('.')

def _create_solution_module(source_code_lst: Tuple[str])-> types.ModuleType:
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
        '_sys':__import__("sys")
    })

    for source_code in source_code_lst:
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
    
def _is_wrong(result:_CASE_TYPE)->bool:
    return 'expected' in result and 'output' in result and result['expected'] != result['output']

def _log_result(result:_CASE_TYPE,log_lines:List,log_prefix:str = "",log_path:Optional[os.PathLike]=None):
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

def _execute_single_case(
    the_fun:Callable,
    case: _CASE_TYPE
) -> Tuple[_CASE_TYPE, List[str]]:
    """执行单个测试用例（核心封装）"""
    log_lines = []
    result_dict = case.copy()
    
    def _add_log(content: str):
        log_lines.append(f"{case['cid']}:\t{content}")
    
    try:
        # 保存原始 stdout
        original_stdout = sys.stdout

        _add_log(f"Running '{the_fun.__name__}' with case: {case.get('test_case_key', f'{case['cid']}')}")
        
        input_val = case['input']
        # instance = self.Solution()
        
        # 创建字符串缓冲区捕获 print 输出
        captured_output = io.StringIO()
        
        if isinstance(input_val, dict):
            _add_log(f">>> INPUT\n{_compacted_json.dumps(input_val, indent=2)}")
            # 重定向 stdout
            sys.stdout = captured_output
            output = the_fun( **input_val)
            # 恢复 stdout
            sys.stdout = original_stdout
            # 获取并记录 print 内容
            print_content = captured_output.getvalue()
            if print_content.strip():
                _add_log(f">>> PRINT OUTPUT:\n{print_content}")
            
        elif isinstance(input_val, tuple):
            _add_log(f">>> INPUT\n{_compacted_json.dumps(list(input_val), indent=2)}")
            # 重定向 stdout
            sys.stdout = captured_output
            output = the_fun( *input_val)
            # 恢复 stdout
            sys.stdout = original_stdout
            # 获取并记录 print 内容
            print_content = captured_output.getvalue()
            if print_content.strip():
                _add_log(f">>> PRINT OUTPUT:\n{print_content}")
        else:
            raise ValueError("测试用例的input必须是字典或元组")
        
        elapsed = time.perf_counter() - time.perf_counter()
        result_dict['output'] = output
        result_dict['elapsed'] = elapsed
        _add_log(f"<<< OUTPUT (elapsed: {elapsed:.6f}s)\n{_compacted_json.dumps(output, indent=2)}")
        
    except Exception as e:
        # 异常时也恢复 stdout
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
    source_code_lst: Tuple[str],
    method_name:str,
    group_queue_id: int,
    output_queue_id: int,
    early_stop_queue: interpreters.Queue,
    log_prefix:str,
    log_folder:os.PathLike,
    skip_error = False,
    log_wrong = True,
) -> tuple:
    """
    模块级 worker 函数，在子解释器中执行测试用例
    所有参数必须是可共享的基本类型（字符串、整数）
    """
    print(f"线程{interpreter_id}：开始")
    # ========== 所有导入在子解释器内部完成 ==========

    # 创建子解释器的环境模块
    module = _create_solution_module(source_code_lst)

    # 确保所有导入在子解释器内部完成
    # 通过 ID 重建队列
    
    group_queue = interpreters.Queue( group_queue_id)
    output_queue = interpreters.Queue( output_queue_id)
    print(f"线程{interpreter_id}: 队列重建成功")

    # 创建 Solution 实例和方法
    instance = module.__dict__['Solution']()
    the_fun = getattr(instance,method_name)
    
    start_time = time.time()
    process_case_num = 0

    print(f"线程{interpreter_id}：成功创建 Solution 实例和方法。")
    
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
                result,log_lines = _execute_single_case(the_fun,case)

                if 'error' in result:
                    error_log_path = _log_result(result,log_lines,f"{log_prefix}_ERROR_",log_folder)
                    if skip_error:
                        Warning(f"跳过报错用例（已经保存日志到 {error_log_path}）")
                        wrong_count += 1 # error 当然也算“错误”
                    else:
                        # 出现报错，触发早停，以分组编号作为早停信息
                        early_stop_queue.put(group_id)
                        raise Exception(f"执行报错（已经保存日志到 {error_log_path}）：\n{result['error']}")
                elif _is_wrong(result): 
                    if log_wrong:
                        _log_result(result,log_lines,f"{log_prefix}_Wrong_",log_folder)
                    wrong_count += 1 

                results_buff.append(result)
            
            # 将 (分组id，该组错误数量，改组结果列表) 加入到输出队列
            output_queue.put((group_id, wrong_count, results_buff))
            process_case_num += len(results_buff)
            
            print(f"解释器 {interpreter_id}: 完成组 {group_id} ({len(results_buff)} 个用例)")
        
    except Exception as e:
        print(f"解释器 {interpreter_id}: 顶层异常 {type(e).__name__}: {e}")
        output_queue.put((None, []))
        raise
    
    end_time = time.time()
    elapsed = end_time - start_time
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
        self.pre_code = self._read_code(_CURRENT_DIR/"custom_init.py")
        
        # 从 solution_file 路径中提取相对目录（即文件所在目录）
        solution_path = Path(solution_file).resolve()
        self.relPath = solution_path.parent
        self.file_name = os.path.splitext(os.path.basename(solution_path))[0]

        # 2. 创建 solution 的虚拟环境
        self.solution_module = _create_solution_module((self.student_code,))

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
            self.method_name = main_method
            self.method = method_dict[main_method]
        else:
            # 自动选择唯一方法
            if len(methods) != 1:
                method_names = [name for name, _ in methods]
                raise ValueError(f"Solution类必须有且仅有一个非魔术方法，当前找到 {len(methods)} 个: {method_names}")
            self.method_name, self.method = methods[0]

        # 6. 提出主方法的参数名和参数类型
        self.instance = module_Solution()
        self.sig  = inspect.signature(getattr(self.instance, self.method_name))
        self.sig_names = list(self.sig.parameters.keys())
        self.sig_types = [v.annotation for v in self.sig.parameters.values()]

        if __DEBUG__:
            print(f"sig.parameters: {self.sig.parameters}")
            print(f"主方法参数名: { self.sig_names}")
            print(f"主方法参数类型: { self.sig_types }")

    def read_test_case(
        self,
        path_list: Union[os.PathLike, List[os.PathLike]],
        file_name_pattern: Optional[str] = None
    ) -> List[_CASE_TYPE]:
        """读取并解析测试用例文件（自动完成类型转换）"""
        from glob import glob
        if not isinstance(path_list, list):
            path_list = [path_list]
            
        all_files = []
        for p in path_list:
            p = Path(p)
            if p.is_file():
                if file_name_pattern is None or p.match(file_name_pattern):
                    all_files.append(p.resolve())
            elif p.is_dir():
                pattern = file_name_pattern if file_name_pattern else "*"
                matched = list(p.glob(pattern))
                all_files.extend(f.resolve() for f in matched if f.is_file())
            else:
                raise FileNotFoundError(f"路径不存在: {p}")
        
        test_cases = []
        
        for file_path in all_files:
            try:
                # ========== 核心修改点：根据文件后缀分流处理 ==========
                if file_path.suffix.lower() == '.json':
                    # 1. 处理 JSON 文件
                    with open(file_path, 'r', encoding='utf-8') as f:
                        raw_data = json.load(f)
                    
                    # 确保是列表格式
                    if not isinstance(raw_data, list):
                        raw_data = [raw_data]
                    
                    for item in raw_data:
                        # 如果JSON里已经是标准格式（含"input"键）
                        if isinstance(item, dict) and 'input' in item:
                            converted_case = item
                        else:
                            # 如果是裸数据，尝试包装
                            converted_case = {'input': item}
                        
                        # === 关键：自动推断输入类型（字典 or 元组）===
                        
                        # 情况 A: 如果 input 是字典（标准格式），直接使用
                        if isinstance(converted_case['input'], dict):
                            # 验证签名
                            self.sig.bind(**converted_case['input'])
                            
                        # 情况 B: 如果 input 是列表/元组，且参数名已知，转换为字典
                        elif isinstance(converted_case['input'], (list, tuple)):
                            if len(self.sig_names) == len(converted_case['input']):
                                # 转换为字典格式，以便后续统一处理
                                converted_case['input'] = dict(zip(self.sig_names, converted_case['input']))
                                self.sig.bind(**converted_case['input'])
                            else:
                                raise ValueError(f"参数数量不匹配: 函数需要 {len(self.sig_names)} 个参数 {self.sig_names}, 但输入为 {converted_case['input']}")
                        
                        # 情况 C: 单个值（仅当函数只有一个参数时）
                        else:
                            if len(self.sig_names) == 1:
                                converted_case['input'] = {self.sig_names[0]: converted_case['input']}
                                self.sig.bind(**converted_case['input'])
                            else:
                                raise ValueError("无法推断单值输入的参数名")
                        
                        test_cases.append(converted_case)
                
                else:
                    # 2. 原有逻辑：处理 TXT 文件
                    # 注意：这里需要传入 params_num，但我们现在无法从文件名得知，所以需要用户传入或在文件名中约定
                    # 为了保持兼容，这里假设用户在 file_name_pattern 或其他方式传入，或者在 parse_test_cases 内部有默认逻辑
                    # 如果你的 parse_test_cases 需要 params_num，这里会报错，建议在 README 中说明 TXT 必须配合 params_num 使用
                    # 或者修改 parse_test_cases 支持不传 params_num 时返回原始对象（如果是 JSON-like 对象）
                    
                    # 这里做一个简单的兼容：尝试用旧方法，如果报错则尝试直接读取（如果 txt 里存的是 json 字符串）
                    try:
                        parsed_list = parse_test_cases(file_path)
                        # ... (原有处理 parsed_list 的逻辑) ...
                        # 由于原有逻辑较为复杂且依赖外部 parser，此处仅展示 JSON 逻辑的完善
                        # 建议：如果 txt 解析报错，可以在这里加一个 fallback：尝试 json.loads 每一行
                    except Exception as e:
                        # Fallback: 尝试直接读取文件内容作为 JSON（针对 .txt 里误存 JSON 的情况）
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read().strip()
                                if content.startswith('[') or content.startswith('{'):
                                    data = json.loads(content)
                                    if not isinstance(data, list):
                                        data = [data]
                                    # 复用上面的 JSON 处理逻辑
                                    for item in data:
                                        # ... (同上 JSON 处理逻辑) ...
                                        # 为了简洁，这里调用一个提取函数，或者直接抛出 NotImplementedError 提示用 .json 后缀
                                        pass
                        except:
                            raise RuntimeError(f"解析测试文件失败 (非JSON格式): {file_path}") from e
            
            except Exception as e:
                raise RuntimeError(f"解析测试文件失败: {file_path}") from e
        
        return test_cases
    
    def run_as_expected(self, 
        test_cases: Union[List[_CASE_TYPE] , List[Tuple]],  # 严格要求是 List[CASE_TYPE]
        early_stop: Optional[Union[int, float]] = None,
        thread: int = 1,
        timeout_s: Optional[float] = 10
    )-> List[_CASE_TYPE]:
        # ========== 自动处理 test_cases 为元组列表的情况 ============
        assert isinstance(test_cases, list), "test_cases 必需是 list 类型"
        if all(map(lambda x: isinstance(x, tuple),test_cases)):
            # 如果是元组列表，则尝试按 self.method 的签名转换为标准 _CASE_TYPE 列表
            test_cases = self.tuple_to_cases(test_cases)
        
        output = self.run(test_cases,log_wrong = False,thread = thread,timeout_s=timeout_s)
        expected_results = self.get_expected_cases(output)

        return expected_results

    def run(
        self,
        test_cases: List[_CASE_TYPE],  # 严格要求是 List[CASE_TYPE]
        log_wrong: bool = True,        # 默认记录错误的测试样例
        log_prefix: Optional[str] = None,
        early_stop: Optional[Union[int, float]] = None,
        thread: int = 1,
        timeout_s: Optional[float] = 10,
        summary: bool = False,
        skip_error = False,
        check_cases_format = True
    ) -> List[_CASE_TYPE]:
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
            
        # ========== 2. 执行所有用例 ==========
        func_name = getattr(self.method, '__name__', 'unknown')\
        
        if log_prefix is None:
            log_prefix = self.file_name

        if -1==thread:
            cpu_count = os.cpu_count()
            thread = cpu_count if cpu_count else 1
        if 1==thread:
            wrong_count = 0
            results = []
            self.method
            solution = self.solution_module.__dict__['Solution']()
            for case in test_cases:
                # 执行单用例（核心封装，便于多进程改造）
                result, log_lines = _execute_single_case(
                    getattr(self.instance, self.method_name),
                    case=case
                )
                results.append(result)

                if 'error' in result:
                    error_log_path = _log_result(result,log_lines,f"{log_prefix}_ERROR_",self.relPath)
                    if skip_error:
                        Warning(f"跳过报错用例（已经保存日志到 {error_log_path}）")
                        wrong_count += 1 # error 当然也算“错误”
                    else:
                        raise Exception(f"执行报错（已经保存日志到 {error_log_path}）：\n{result['error']}")
                elif _is_wrong(result): 
                    if log_wrong:
                        _log_result(result,log_lines,f"{log_prefix}_Wrong_",self.relPath)
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
            
            sys_path_list = str(_CURRENT_DIR.parent)
            print(f"tools_path: {sys_path_list}")
            with futures.InterpreterPoolExecutor(max_workers=thread) as executor:
                futures_list = []
                for i in range(thread):
                    fut = executor.submit(
                        _execute_in_interpreter_worker,
                        i,
                        (self.pre_code,self.student_code),  # 传递代码字符串
                        self.method_name,
                        group_queue.id,
                        output_queue.id,
                        early_stop_queue,
                        log_prefix,
                        self.relPath
                        # 不直接传递 test_cases，而是从队列获取
                    )
                    futures_list.append(fut)
                
                # 收集结果（带超时）
                try:
                    worker_results = [f.result(timeout=timeout_s) for f in futures_list]
                    print(f"所有工作线程完成：{worker_results}")
                except TimeoutError:
                    print(f"⚠️ 执行超时 ({timeout_s}s)")
                
                # 收集输出队列结果
                output_buff = [None]*groups_num
                output_count,wrong_count = 0,0
                total_count = len(test_cases)  
                
                while output_count < len(test_cases):
                    try:
                        group_id, wcnt ,results = output_queue.get(timeout=2.0)
                        if group_id is not None:
                            output_buff[group_id] = results
                            output_count += len(results)
                            wrong_count += wcnt
                            print(f"主线程：(已收集/总样例数): ({output_count}/{total_count})")
                            if self._check_early_stop( output_count, wrong_count ,early_stop):
                                early_stop_queue.put(group_id)
                                break # 触发早停
                    except interpreters.QueueEmpty:
                        continue

            import itertools
            outputs:List[List[Any]] = list(filter(bool,output_buff))
            # 合并结果
            results = [res for output in outputs for res in output]

            print(f"多线程完成：共 {len(results)} 个结果")

        return results    

    @classmethod
    def summary_results(cls,results:List[_CASE_TYPE],verbose = True)-> Tuple[int,int]:
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
    def _check_early_stop(cls,total_cnt:int,wrong_count:int,early_stop:Optional[int|float]=None)->bool:
        """检查是否触发早停"""
        if early_stop is None:return False
        if early_stop < 1:
            return wrong_count > early_stop*total_cnt
        else:
            return wrong_count >= early_stop


    def get_expected_cases(self, run_results: List[_CASE_TYPE]) -> List[_CASE_TYPE]:
        """从run结果中过滤出成功的测试用例，重新编号以#开头的cid，并将'output'重命名为'expected'"""
        expected_cases = []
        case_id = 0
        total_count = len(run_results)
        
        for result in run_results:
            if 'error' not in result:
                case_id += 1
                output = result.copy()

                # print(f"output={output}")

                output['cid'] = f"#{case_id}"
                output['expected'] = output.pop('output')
                output.pop('elapsed', None)
                expected_cases.append(output)

        print(f"✅ 从 {total_count} 个测试用例中筛选出 {case_id} 个有效用例")
        return expected_cases
    
    def save_test_cases(self, test_cases: List[_CASE_TYPE], file_path: Optional[os.PathLike] = None) -> os.PathLike:
        """保存测试用例到JSON文件"""
        if file_path is None:
            base_name = os.path.splitext(os.path.basename(self.solution_file))[0]
            # 保存到相对目录下
            file_path = self.relPath / f"{base_name}.json"  # 生成一个相对路径的文件名(此行代码报错！)
        else:
            # 确保文件路径的目录存在
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(
                _compacted_json.dumps(test_cases, indent=2, ensure_ascii=False)
            )
        
        print(f"💾 已保存 {len(test_cases)} 个测试用例到: {file_path}")
        return Path(file_path)
    
    def tuple_to_cases(self, cases: List[Tuple]) -> List[_CASE_TYPE]:
        """将元组形式的测试样例转换为字典形式
        临时函数：以后优化：需要增加参数类型识别，并且能够自动转换自定义类型
        """
        m = len(self.sig_names)
        if m == 0:
            raise ValueError("被测函数没有参数，无法转换元组格式测试用例")
        
        # 展平所有元组
        flat_values = []
        for case in cases:
            if not isinstance(case, tuple):
                raise ValueError(f"测试用例必须是元组格式，得到: {type(case)}")
            flat_values.extend(case)
        
        # 检查总参数数量是否为参数个数的整数倍
        total_values = len(flat_values)
        if total_values % m != 0:
            raise ValueError(f"总参数数量 {total_values} 不能被参数个数 {m} 整除")
        
        # 按参数数量分块
        result = []
        num_cases = total_values // m
        for i in range(num_cases):
            start_idx = i * m
            chunk = flat_values[start_idx:start_idx + m]
            input_dict = dict(zip(self.sig_names, chunk))
            result.append({
                "input": input_dict,
                "cid": i
                })
        
        return result
            