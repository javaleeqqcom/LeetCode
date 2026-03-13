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
from charset_normalizer.api import from_bytes  # 自动检测编码
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

# solution_runner.py 文件顶部（类定义之前）
def _execute_in_interpreter_worker(
    interpreter_id: int,
    student_code: str,
    method_name: str,
    group_queue: interpreters.Queue,
    output_queue: interpreters.Queue,
) -> tuple:
    """
    模块级 worker 函数，在子解释器中执行测试用例
    
    参数:
        interpreter_id: 解释器 ID
        student_code: 学生代码字符串（可 pickle）
        method_name: 方法名
        group_queue_id: 队列 ID（整数）
        output_queue_id: 队列 ID（整数）
    """
    print(f"线程{interpreter_id}：开始")

    import time
    import sys
    import io
    import types
    import traceback
    from concurrent import interpreters
    from custom_init import ListNode, TreeNode, Optional, List, Dict
    
    print(f"线程{interpreter_id}：成功导入外部库")

    # 在子解释器中重建学生代码环境
    mod = types.ModuleType('student_solution')
    mod.__dict__.update({
        'ListNode': ListNode,
        'TreeNode': TreeNode,
        'Optional': Optional,
        'List': List,
        'Dict': Dict,
        '__builtins__': __builtins__,
    })
    exec(student_code, mod.__dict__)
    
    # 创建 Solution 实例和方法
    Solution = mod.Solution
    instance = Solution()
    method = getattr(instance, method_name)
    
    start_time = time.time()
    process_case_num = 0

    print(f"线程{interpreter_id}：成功创建 Solution 实例和方法。")
    
    try:
        while True:
            # 从队列获取任务
            try:
                group_id, cases = group_queue.get_nowait()
            except interpreters.QueueEmpty:
                if group_queue.empty():
                    break
                time.sleep(0.001)
                continue
            
            results_buff = []
            
            for case in cases:
                log_lines = []
                result_dict = case.copy()
                
                def _add_log(content: str):
                    log_lines.append(f"{case.get('cid', 'unknown')}: {content}")
                
                try:
                    original_stdout = sys.stdout
                    captured_output = io.StringIO()
                    
                    input_val = case['input']
                    
                    if isinstance(input_val, dict):
                        sys.stdout = captured_output
                        output = method(**input_val)
                        sys.stdout = original_stdout
                        
                    elif isinstance(input_val, tuple):
                        sys.stdout = captured_output
                        output = method(*input_val)
                        sys.stdout = original_stdout
                    else:
                        raise ValueError("input 必须是字典或元组")
                    
                    result_dict['output'] = output
                    _add_log(f"OUTPUT: {output}")
                    
                except Exception as e:
                    sys.stdout = original_stdout
                    result_dict['error'] = str(e)
                    result_dict['traceback'] = traceback.format_exc()
                    _add_log(f"ERROR: {traceback.format_exc()}")
                
                results_buff.append(result_dict)
            
            # 输出结果到队列
            output_queue.put((group_id, results_buff))
            process_case_num += len(results_buff)
            
            # 调试输出
            print(f"解释器 {interpreter_id}: 完成组 {group_id} ({len(results_buff)} 个用例)")
        
    except Exception as e:
        print(f"解释器 {interpreter_id}: 顶层异常 {type(e).__name__}: {e}")
        output_queue.put((None, []))
        raise
    
    end_time = time.time()
    elapsed = end_time - start_time
    print(f"解释器 {interpreter_id}: 处理 {process_case_num} 个用例耗时: {elapsed:.3f}s")
    
    return (interpreter_id, process_case_num, elapsed)

class SolutionRunner:
    def __init__(self, solution_file: os.PathLike, main_method: Optional[str] = None) -> None:
        """
        初始化 SolutionRunner，自动加载学生代码文件。
        :param solution_file: 学生代码文件路径（如 "P82_V0.py"）
        :param main_method: 指定主方法名（当Solution有多个方法时），默认None表示自动选择唯一方法
        """
        # 1. 读取并自动检测编码（支持中文）
        with open(solution_file, 'rb') as f:
            raw = f.read()
        result = from_bytes(raw).best()
        self.student_code = str(result) if result else raw.decode('utf-8', errors='ignore')
        
        # 从 solution_file 路径中提取相对目录（即文件所在目录）
        self.solution_file = str(solution_file)
        solution_path = Path(solution_file).resolve()
        self.relPath = solution_path.parent
        self.file_name = os.path.splitext(os.path.basename(solution_path))[0]

        # 2. 创建虚拟执行环境
        mod = types.ModuleType('student_solution')
        mod.__dict__.update({
            'ListNode': ListNode,
            'TreeNode': TreeNode,
            'Optional': Optional,
            'List': List,
            'Dict': Dict,
            '__builtins__': __builtins__,
        })

        # 3. 执行学生代码（注入类型）
        exec(self.student_code, mod.__dict__)
        
        # 4. 获取Solution类
        if 'Solution' not in mod.__dict__:
            raise ValueError("学生代码中未定义 Solution 类")
        self.Solution = mod.Solution

        # 5. 提取方法
        methods = []
        for name, method in inspect.getmembers(self.Solution, predicate=inspect.isfunction):
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
        
        # 创建临时实例获取绑定方法签名（用于JSON自动推断）
        temp_instance = self.Solution()
        bound_method = getattr(temp_instance, self.method_name)
        sig = inspect.signature(bound_method)
        param_names = list(sig.parameters.keys())
        # 移除 self
        if param_names and param_names == 'self':
            param_names = param_names[1:]
        
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
                            sig.bind(**converted_case['input'])
                            
                        # 情况 B: 如果 input 是列表/元组，且参数名已知，转换为字典
                        elif isinstance(converted_case['input'], (list, tuple)):
                            if len(param_names) == len(converted_case['input']):
                                # 转换为字典格式，以便后续统一处理
                                converted_case['input'] = dict(zip(param_names, converted_case['input']))
                                sig.bind(**converted_case['input'])
                            else:
                                raise ValueError(f"参数数量不匹配: 函数需要 {len(param_names)} 个参数 {param_names}, 但输入为 {converted_case['input']}")
                        
                        # 情况 C: 单个值（仅当函数只有一个参数时）
                        else:
                            if len(param_names) == 1:
                                converted_case['input'] = {param_names[0]: converted_case['input']}
                                sig.bind(**converted_case['input'])
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
    
    def _get_unique_log_path(self, file_name: str) -> Path:
        """生成唯一的日志文件路径（保存到 self.relPath 目录下）"""
        # 确保 relPath 是一个路径对象
        log_dir = Path(self.relPath)
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
            solution = self.Solution() 
            for case in test_cases:
                # 执行单用例（核心封装，便于多进程改造）
                result, log_lines = self._execute_single_case(
                    solution,
                    case=case,
                    func_name=func_name,
                )
                results.append(result)

                error_log_path = self.get_error_log_path(result,log_lines,log_prefix)
                if error_log_path is not None:
                    if skip_error:
                        Warning(f"跳过报错用例（已经保存日志到 {error_log_path}）")
                        wrong_count += 1 # error 当然也算“错误”
                    else:
                        raise Exception(f"执行报错（已经保存日志到 {error_log_path}）：\n{result['error']}")
                elif self.auto_log_wrong(result,log_lines,log_wrong): 
                    wrong_count += 1 
                    if self._check_early_stop( len(results), wrong_count ,early_stop):
                        break # 触发早停

        else:
            # ========== 多线程执行 ==========
            from concurrent import futures, interpreters
            from functools import partial
            
            # 创建共享队列
            group_queue = interpreters.create_queue()
            output_queue = interpreters.create_queue()
            
            # 分割测试用例到队列
            groups_num = self.geometric_decreasing_queue_generator(test_cases, group_queue, rate=1.0/thread)
            
            with futures.InterpreterPoolExecutor(max_workers=thread) as executor:
                # 使用 partial 固定参数，map() 只传入 interpreter_id
                func = partial(
                    _execute_in_interpreter_worker,
                    student_code = self.student_code,
                    method_name = self.method_name,
                    group_queue=group_queue,
                    output_queue=output_queue,
                )
                
                # 执行并收集结果（带超时）
                try:
                    worker_results = list(executor.map(func, range(thread), timeout=timeout_s))
                    print(f"所有工作线程完成: {worker_results}")
                except TimeoutError:
                    print(f"⚠️ 执行超时 ({timeout_s}s)")
                
                # 收集输出队列结果（带超时）
                output_buff = []
                collected_groups = 0
                
                while collected_groups < groups_num:
                    try:
                        group_id, results = output_queue.get(timeout=2.0)
                        if group_id is not None:
                            output_buff.append((group_id, results))
                            collected_groups += 1
                            print(f"主线程: 已收集 {collected_groups}/{groups_num} 组")
                    except interpreters.QueueEmpty:
                        print(f"主线程: 等待结果... ({collected_groups}/{groups_num})")
                        continue
            
            # 合并结果
            results = self.merge_groups(output_buff)
            print(f"多线程完成：共 {len(results)} 个结果")

        if summary:
            self.summary_results(results)
        
        return results
    


    @classmethod
    def geometric_decreasing_queue_generator(cls, test_cases: List[_CASE_TYPE], queue: interpreters.Queue, rate: float = 0.1) -> int:
        """将测试用例分割为若干个子列表，越往后子列表的大小呈等比递减，以便维持各线程基本同时收工"""
        group_id, idx = 0, 0
        # 将剩余的用例按 rate 递减加入到 queue 中，至少要有 1 个用例
        while idx < len(test_cases):
            chunk_size = max(1, int((len(test_cases) - idx) * rate))
            queue.put((group_id, test_cases[idx:idx+chunk_size]))
            idx += chunk_size
            group_id += 1
        return group_id

    @classmethod
    def merge_groups(cls, groups: List[Tuple[int, List[_CASE_TYPE]]]) -> List[_CASE_TYPE]:
        """使用归并排序合并多个已排序列表"""
        # 归并排序
        merged = merge(*groups, key=lambda x: x[0])
        # 提取结果并展平
        return [result for _, group_results in merged for result in group_results]
        
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


    def _execute_single_case(
        self, 
        solution_instance, # 重大改进，必须由上级指定学生代码实例：1. 可以避免重复实例化带来的开销；2. 兼容多线程调用，各子线程独立构造学生代码实例（因为学生代码是黑箱，无法共享）
        case: _CASE_TYPE,  func_name: str
    ) -> Tuple[_CASE_TYPE, List[str]]:
        """执行单个测试用例（核心封装）"""
        log_lines = []
        result_dict = case.copy()
        
        def _add_log(content: str):
            log_lines.append(f"{case['cid']}:\t{content}")
        
        try:
            # 保存原始 stdout
            original_stdout = sys.stdout

            _add_log(f"Running '{func_name}' with case: {case.get('test_case_key', f'{case['cid']}')}")
            
            input_val = case['input']
            # instance = self.Solution()
            
            # 创建字符串缓冲区捕获 print 输出
            captured_output = io.StringIO()
            
            if isinstance(input_val, dict):
                _add_log(f">>> INPUT\n{_compacted_json.dumps(input_val, indent=2)}")
                # 重定向 stdout
                sys.stdout = captured_output
                output = self.method(solution_instance, **input_val)
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
                output = self.method(solution_instance, *input_val)
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

    @classmethod
    def get_error_log_path(cls,result:_CASE_TYPE,log_lines:List,log_prefix:str) -> Optional[os.PathLike]:
        if 'error' in result:
            # 单独记录报错的 log，以 self.solution_file 和 idx 命名
            log_path = self._get_unique_log_path(f"{log_prefix}_ERROR_{result['cid']}.log")
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(log_lines))
            return log_path
        return None

    @classmethod
    def auto_log_wrong(cls,result:_CASE_TYPE,log_lines:List,log_wrong:bool) -> bool:
        if 'expected' in result and 'output' in result and result['expected'] != result['output']: 
            # 记录错误结果的日志
            if log_wrong:
                log_path = self._get_unique_log_path(f"{log_prefix}_Wrong_{result['cid']}.log")
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(log_lines))
            return True
        return False

    def get_expected_cases(self, run_results: List[_CASE_TYPE]) -> List[_CASE_TYPE]:
        """从run结果中过滤出成功的测试用例，重新编号以#开头的cid，并将'output'重命名为'expected'"""
        expected_cases = []
        case_id = 0
        total_count = len(run_results)
        
        for result in run_results:
            if 'error' not in result:
                case_id += 1
                expected_case = result.copy()
                expected_case['cid'] = f"#{case_id}"
                expected_case['expected'] = expected_case.pop('output')
                expected_case.pop('elapsed', None)
                expected_cases.append(expected_case)

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
        # 获取被测函数的参数名
        temp_instance = self.Solution()
        bound_method = getattr(temp_instance, self.method_name)
        sig = inspect.signature(bound_method)
        params = list(sig.parameters.keys())
        
        # 排除 self 参数
        if params and params[0] == 'self':
            params = params[1:]
        
        m = len(params)
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
            input_dict = dict(zip(params, chunk))
            result.append({
                "input": input_dict,
                "cid": i
                })
        
        return result
            