# tools/solution_runner.py
import os,sys,io
import math
import inspect
from pathlib import Path
import logging
import datetime, time
from typing import Any, Callable, Dict, List, Tuple, Union, Optional, get_type_hints, get_args, get_origin,NotRequired,TypedDict,Deque
import ast, re, json
import types
import traceback
# from charset_normalizer.api import from_bytes  # 自动检测编码（与py3.14多线程不兼容）
from concurrent import futures
from multiprocessing import shared_memory # 实现跨进程共享内存
import signal
from queue import Empty
from collections import deque
import multiprocessing
from functools import partial  # 固定 test_queue 参数之用于多线程调用
from heapq import merge # 多路有序列表最优归并（optimal merge pattern）
from dataclasses import dataclass # 这是 Python 3.7+ 自带的标准库，专门用于此类场景。它会自动帮你生成 __init__、__repr__ 等方法。
__DEBUG__ = True
__FULL_PATH__ = False
# LeetCode 中的学生提交总是以此类命名
_SOLUTION_TYPE_NAME_ = "Solution"
# 获取 solution_runner.py 所在目录（即 tools 目录）
_TOOLS_DIR = Path(__file__).resolve().parent
# ========== 安全导入：基于当前文件路径 ==========
if __DEBUG__:
    # 将 tools 目录添加到 sys.path，确保模块可导入
    if str(_TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(_TOOLS_DIR))
    elif os.path.exists(_TOOLS_DIR/"tools"):
        _TOOLS_DIR = _TOOLS_DIR/"tools"
        sys.path.insert(0, str(_TOOLS_DIR))
    print(f"tools dir:{_TOOLS_DIR}")
# 直接导入，无需 try-except
from .examples_parser import parse_test_cases
from .args_parser import _BASE_TYPE,_PARAMS,_CASE,_EXECUTE_CALLER,_is_base_type,parse_output_to_standard
from .def_conversion import main_caller_args,main_caller_kwargs
from .compacted_json import CompactedJson
from .solution_struct import SolutionStruct
from .ai_prompts import _CUSTOM_CALLER_NAME   # 仅保留 caller 名称常量

"""
一个标准的测试样例的格式为：
    - 字典: {"input": case [,"output":Any, "expected":Any,"error":str , ...]}
    - 其中的 case 可以是：
        - 字典：其键为被测函数的变量名，其值则为变量值
        - 元组：按被测函数的变量顺序排列的变量值
"""
class _RESULT(_CASE): # TypedDict 类
    elapsed: NotRequired[float]
    error: NotRequired[str]
    traceback: NotRequired[str]
# ========== 全局辅助函数（放在类外部或类内静态方法）==========
_compacted_json = CompactedJson(hex_len=16)
# ================= 全局共享样例（子进程初始化） =================
_GLOBAL_CASES = None
_GLOBAL_CASES_SHM = None
_GLOBAL_GROUP_QUEUE = None
_GLOBAL_OUTPUT_QUEUE = None
_GLOBAL_EARLY_STOP_EVENT = None
def _init_process_worker(
    shm_name: str,
    shm_size: int,
    group_queue,
    output_queue,
    early_stop_event,
):
    """
    子进程初始化：
    连接共享内存中的 test_cases
    """
    global _GLOBAL_CASES
    global _GLOBAL_CASES_SHM
    global _GLOBAL_GROUP_QUEUE
    global _GLOBAL_OUTPUT_QUEUE
    global _GLOBAL_EARLY_STOP_EVENT

    _GLOBAL_GROUP_QUEUE = group_queue
    _GLOBAL_OUTPUT_QUEUE = output_queue
    _GLOBAL_EARLY_STOP_EVENT = early_stop_event

    shm = shared_memory.SharedMemory(name=shm_name)
    if shm.buf is None:
        raise MemoryError("_init_process_worker: Can not connect to shared memory.")

    _GLOBAL_CASES_SHM = shm

    raw = bytes(shm.buf[:shm_size])

    _GLOBAL_CASES = json.loads(raw.decode("utf-8"))

def _sanitize_filename(name: str) -> str:
    """安全文件名转换"""
    for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        name = name.replace(ch, '_')
    return name.strip().rstrip('.')
# def _create_solution_module(source_code_lst: List[Optional[str]])-> types.ModuleType:
def _create_solution_module(source_code_lst: List[str])-> types.ModuleType:
    """
    创建黑箱执行器代码字符串
    ⚠️ 不导入任何学生代码可能用的库
    返回黑箱函数
    """
    _types = __import__("types")
    module = _types.ModuleType('solution_module')
    module.__package__ = "tools"
    module.__package__ = "tools"
    module.__dict__.update({
        '__builtins__': __builtins__,
        '__name__': 'solution_module',
        '_sys':__import__("sys"),
    })
    # 将 tools 目录添加到 sys.path，确保模块可导入
    _sys_path = module.__dict__['_sys'].path
    if str(_TOOLS_DIR) not in _sys_path:
        _sys_path.insert(0, str(_TOOLS_DIR))
        # _sys_path.insert(0, str(_TOOLS_DIR.parent))
    for source_code in source_code_lst:
        # if source_code is not None:
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
def _is_wrong(result:_RESULT)->bool:
    return 'expected' in result and 'output' in result and result['expected'] != result['output']
def _log_result(result:_RESULT,log_lines:List,log_prefix:str = "",log_path:Optional[os.PathLike]=None):
    log_path = _get_unique_log_path(
        Path(os.getcwd() if log_path is None else log_path)
        , f"{log_prefix}_{result['cid']}.log"
        )
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_lines))
    return log_path
def _execute_dict_case(
    caller: _EXECUTE_CALLER,
    solution_or_function,
    case: _CASE
) -> Tuple[_RESULT, List[str]]:
    """执行单个测试用例（核心封装）"""
    log_lines = []
    # 根据基类 _BASE_CASE 构造结果字典
    result_dict:_RESULT = {**case}
    # 日志格式
    def _add_log(content: str):
        log_lines.append(f"{case['cid']}:\t{content}")
    # 记录时间执行时间
    start_time = time.perf_counter()
    original_stdout = None
    try:
        _add_log(f"Running '{solution_or_function.__name__ if callable(solution_or_function) else type(solution_or_function)}' with case: {case.get('test_case_key', f"{case['cid']}")}")
        # 提取输入
        input_val = case['input']
        # 记录输入到 log
        _add_log(f">>> INPUT\n{_compacted_json.dumps(input_val, indent=2)}")
        # 保存原始 stdout
        original_stdout = sys.stdout
        # 创建字符串缓冲区捕获 print 输出
        captured_output = io.StringIO()
        # 重定向 stdout
        sys.stdout = captured_output
        # 执行方法并返回结果
        output_val = caller(solution_or_function,input_val)
        # 恢复 stdout
        sys.stdout = original_stdout
        # 获取并记录 print 内容
        print_content = captured_output.getvalue()
        if print_content.strip():
            _add_log(f">>> PRINT OUTPUT:\n{print_content}")
        # 将其转化为 LeetCode 的通用的输出类型（原生 JSON 的输入类型）
        output:_BASE_TYPE = parse_output_to_standard(output_val)
        elapsed = time.perf_counter() - start_time
        # 记录结果
        result_dict['output'] = output
        result_dict['elapsed'] = elapsed
        _add_log(f"<<< OUTPUT (elapsed: {elapsed:.6f}s)\n{_compacted_json.dumps(output, indent=2)}")
        # 若有期望输出则打印
        if 'expected' in result_dict:
            _add_log(f">>> EXPECTED \n{_compacted_json.dumps(result_dict['expected'], indent=2)}")
    except Exception as e:
        # 异常时也恢复 stdout
        if original_stdout is not None:
            sys.stdout = original_stdout
        elapsed = time.perf_counter() - start_time
        result_dict['error'] = str(e)
        result_dict['traceback'] = traceback.format_exc()
        result_dict['elapsed'] = elapsed
        _add_log("!!! EXCEPTION OCCURRED:")
        _add_log(traceback.format_exc())
    return result_dict, log_lines
# 用于 Deque 的队列元素
@dataclass
class _IN_QELE:
    group_id:int
    start:int
    end:int
@dataclass
class _OUT_QELE:
    group_id:int
    wcnt:int
    results:List[_RESULT]
def _geom_queue_generator( total_cases: int, queue: multiprocessing.Queue, rate: float = 0.1) -> int:
    """将测试用例分割为若干个子列表，越往后子列表的大小呈等比递减，以便维持各线程基本同时收工"""
    group_id, idx = 0, 0
    # 将剩余的用例按 rate 递减加入到 queue 中，至少要有 1 个用例
    while idx < total_cases:
        chunk_size = max(1, int((total_cases - idx) * rate))
        end = min(idx + chunk_size, total_cases)
        queue.put(
            _IN_QELE(
                group_id,
                idx,
                end
            )
        )
        idx += chunk_size
        group_id += 1
    return group_id

def _execute_in_process_worker(
    worker_id: int,
    source_code_lst: List[str],
    method_name: Optional[str],
    caller_name: str,
    log_path: os.PathLike,
    skip_error: bool,
    log_wrong: bool,
    shm_name: str,
    shm_size: int,
    group_queue: multiprocessing.Queue,
    output_queue: multiprocessing.Queue,
    early_stop_event: multiprocessing.Event,
    status_list,                # ✅ 新增：共享状态列表（Manager.list 代理）
):
    # ---------- 自行初始化全局变量 ----------
    global _GLOBAL_CASES, _GLOBAL_GROUP_QUEUE, _GLOBAL_OUTPUT_QUEUE, _GLOBAL_EARLY_STOP_EVENT
    from multiprocessing import shared_memory as shm_module
    shm = shm_module.SharedMemory(name=shm_name)
    raw = bytes(shm.buf[:shm_size])
    _GLOBAL_CASES = json.loads(raw.decode("utf-8"))
    _GLOBAL_GROUP_QUEUE = group_queue
    _GLOBAL_OUTPUT_QUEUE = output_queue
    _GLOBAL_EARLY_STOP_EVENT = early_stop_event

    # ✅ 安装 SIGTERM 信号处理器（TLE 时记录日志，不打印堆栈）
    def sigterm_handler(signum, frame):
        current_info = status_list[worker_id]
        if current_info:
            cid = current_info[0]
            # 从全局用例中查找对应的 case 数据（用于记录输入）
            case_data = None
            for case in _GLOBAL_CASES: # 待改进，全局扫描 O(CASES) ，以后用哈希 O(1)
                if case.get('cid') == cid:
                    case_data = case
                    break
            # 构造 result 和 log_lines，仿照 _execute_dict_case 的 error 处理
            result: _RESULT = case_data.copy()
            result.update({'error': 'Time Limit Exceeded (TLE)',})
            log_lines = []
            log_lines.append(f"Worker {worker_id} terminated due to TLE")
            log_lines.append(f"CID: {cid}")
            if case_data:
                log_lines.append(f">>> INPUT\n{_compacted_json.dumps(case_data.get('input'), indent=2)}")
            # 调用框架统一的日志记录函数
            tle_log_path = _log_result(result, log_lines, "TLE_", log_path)
            print(f"\n⚠️ 解释器 {worker_id} TLE，日志已保存: {tle_log_path}", flush=True)
        else:
            print(f"\n⚠️ 解释器 {worker_id} 收到终止信号，但无当前用例信息", flush=True)
        sys.exit(1)

    signal.signal(signal.SIGTERM, sigterm_handler)

    # ---------- 原有逻辑 ----------
    if __DEBUG__:
        print(f"线程{worker_id}：开始")
    start_time = time.time()
    module = _create_solution_module(source_code_lst)
    _Solution = module.__dict__[_SOLUTION_TYPE_NAME_]
    caller: _EXECUTE_CALLER = module.__dict__[caller_name]
    if method_name is None:
        instance_or_function = _Solution
    else:
        instance_or_function = getattr(_Solution(), method_name)
    process_case_num = 0
    try:
        while not _GLOBAL_EARLY_STOP_EVENT.is_set():
            try:
                qval = _GLOBAL_GROUP_QUEUE.get_nowait()
                assert isinstance(qval, _IN_QELE), f"Queue value of group_queue must be of type {_IN_QELE}. But value received:{qval}"
            except Empty:
                if _GLOBAL_GROUP_QUEUE.empty():
                    break
                time.sleep(0.001)
                continue
            results_buff = []
            wrong_count = 0
            cases = _GLOBAL_CASES[qval.start:qval.end]
            for case in cases:
                # ✅ 更新共享状态：记录当前正在执行的用例
                status_list[worker_id] = (case['cid'], time.time())
                result, log_lines = _execute_dict_case(caller, instance_or_function, case)
                if 'error' in result:
                    error_log_path = _log_result(result, log_lines, "ERROR_", log_path)
                    if skip_error:
                        print(f"\n跳过报错用例（日志: {error_log_path}）")
                        wrong_count += 1
                    else:
                        # ✅ 保留当前状态以便主进程查看
                        status_list[worker_id] = (case['cid'], time.time(), "ERROR")
                        early_stop_event.set()
                        raise Exception(f"执行报错（日志: {error_log_path}）：\n{result['error']}")
                elif _is_wrong(result):
                    if log_wrong:
                        _log_result(result, log_lines, "Wrong_", log_path)
                    wrong_count += 1
                results_buff.append(result)
            # 完成一组后清除状态
            status_list[worker_id] = None
            _GLOBAL_OUTPUT_QUEUE.put(_OUT_QELE(qval.group_id, wrong_count, results_buff))
            process_case_num += len(results_buff)
            if __DEBUG__:
                print(f"\n解释器 {worker_id}: 完成组 {qval.group_id} ({len(results_buff)} 个用例)", end="")
    except Exception as e:
        early_stop_event.set()
        raise Exception(f"\n解释器 {worker_id}: 顶层异常 {type(e).__name__}: {e}")
    finally:
        # 保证退出前清除状态
        status_list[worker_id] = None
    end_time = time.time()
    if __DEBUG__:
        print(f"解释器 {worker_id}: 处理 {process_case_num} 个用例耗时：{end_time - start_time:.3f}s")
    return (worker_id, process_case_num, end_time - start_time)

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
        self.solution_file = solution_file
        # 从 solution_file 路径中提取相对目录（即文件所在目录）
        solution_path = Path(solution_file).resolve()
        self.relPath = solution_path.parent
        self.file_name = os.path.splitext(os.path.basename(solution_path))[0]
        # 是否有自定义转换函数文件，若无则以默认转换函数为准
        conversion_path: Path = self.relPath / "conversion.py"
        if conversion_path.exists():
            self.has_custom_caller = True
        else:
            self.has_custom_caller = False
            conversion_path = _TOOLS_DIR / "def_conversion.py"
        # 2.1 读取预执行代码
        self.student_code = self._read_code(solution_file)
        self.source_code_lst = [
            self._read_code(_TOOLS_DIR / "args_parser.py"),
            self.student_code,
            self._read_code(conversion_path),
        ]
        # 2.2 若创建了 conversion.py 则纳入，覆盖原有代码
        if (self.relPath / "conversion.py").exists():
            self.source_code_lst.append(self._read_code(self.relPath / "conversion.py"))
        # 3 创建 solution 的虚拟环境
        self.solution_module = _create_solution_module(self.source_code_lst)
        # 4. 获取Solution类
        if _SOLUTION_TYPE_NAME_ not in self.solution_module.__dict__:
            raise ValueError(f"学生代码中未定义 {_SOLUTION_TYPE_NAME_} 类")
        module_Solution = self.solution_module.__dict__[_SOLUTION_TYPE_NAME_]

        # 5. 提取所有非魔术方法，构建结构化列表（供 build_solution_struct 使用）
        self.all_methods = []  # 每个元素: (name, method_obj, signature, source_code)
        methods_basic = []      # 保留原有简单列表用于 main_method 判断
        for name, method in inspect.getmembers(module_Solution, predicate=inspect.isfunction):
            if not (name.startswith('__') and name.endswith('__')):
                # 获取签名
                try:
                    sig = inspect.signature(method)
                except (ValueError, TypeError):
                    sig = inspect.Signature()   # 无法获取时使用空签名
                # 获取源码
                try:
                    src = inspect.getsource(method)
                except OSError:
                    src = ""
                self.all_methods.append((name, method, sig, src))
                methods_basic.append((name, method))

        # 6. 确定主方法
        if main_method is not None:
            # 使用指定的方法名
            method_dict = dict(methods_basic)
            if main_method not in method_dict:
                raise ValueError(f"指定的主方法 '{main_method}' 不存在于 {_SOLUTION_TYPE_NAME_} 类中")
            self.main_method = main_method
        else:
            # 自动选择唯一方法
            if len(methods_basic) == 1:
                self.main_method, _ = methods_basic[0]
            else:
                print("存在多个方法，执行时必须定义 solution_callers 才能使用 run 及任何后继方法！")
                self.main_method = None  # 用 None 表示可调用方法不唯一

        # 7. 若主方法唯一，初始化实例、签名及类型信息
        if self.main_method is not None:
            self.instance = module_Solution()
            main_method_obj = getattr(self.instance, self.main_method)
            self.sig = inspect.signature(main_method_obj)
            self.sig_names = list(self.sig.parameters.keys())
            self.sig_types = [v.annotation for v in self.sig.parameters.values()]
            self.has_custom_type = not all(_is_base_type(t) for t in self.sig_types)
            if __DEBUG__:
                print(f"sig.parameters: {self.sig.parameters}")
                print(f"主方法参数名: {self.sig_names}")
                print(f"主方法参数类型: {self.sig_types}")
        else:
            self.has_custom_type = None
            
    def build_solution_struct(self) -> SolutionStruct:
        """导出跨语言统一结构，供 AI‑Agent 使用"""
        from .solution_struct import (           # 避免循环导入，在函数内部导入
            SolutionStruct, Language, MethodStruct, ParamStruct,
            ReturnStruct, ConstraintStruct
        )
        methods = []
        for name, method_obj, sig, src in self.all_methods:
            params = []
            for p_name, param in sig.parameters.items():
                # 排除 self
                if p_name == "self":
                    continue
                type_str = str(param.annotation) if param.annotation is not param.empty else "Any"
                # 简单提取 origin_type（可根据需要扩展）
                origin = getattr(param.annotation, "__origin__", None)
                origin_str = origin.__name__ if origin else None
                default = param.default if param.default is not param.empty else None
                params.append(ParamStruct(
                    name=p_name,
                    type_str=type_str,
                    origin_type=origin_str,
                    nullable=False,               # 暂不分析
                    default_value=default,
                    constraints=ConstraintStruct()
                ))
            ret_annotation = sig.return_annotation
            ret_type_str = str(ret_annotation) if ret_annotation is not sig.empty else "None"
            ret_origin = getattr(ret_annotation, "__origin__", None)
            ret_origin_str = ret_origin.__name__ if ret_origin else None
            return_info = ReturnStruct(
                type_str=ret_type_str,
                origin_type=ret_origin_str
            )
            methods.append(MethodStruct(
                name=name,
                params=params,
                return_info=return_info,
                source_code=src
            ))
        return SolutionStruct(
            language=Language.PYTHON,
            class_name=_SOLUTION_TYPE_NAME_,
            source_code=self.student_code,
            methods=methods
        )

    def read_test_case(
        self,
        path_list: Union[os.PathLike, List[os.PathLike]] = []
    ) -> List[_CASE]:
        """读取并解析测试用例文件（支持 _CASE_TYPE 格式，兼容元组和字典）"""
        _path_list = path_list if isinstance(path_list, list) else [path_list]
        if 0 == len(_path_list):
            _path_list = list(Path(self.relPath).glob("*.json"))
            if 0 == len(_path_list):
                raise ValueError(f"read_test_case: path_list 为空，已尝试查找默认样例文件，但未找到，请检查当前目录{self.relPath}。")
            else:
                print(f"read_test_case: path_list 为空，已尝试查找默认样例文件，找到{len(_path_list)}个样例文件。")
        test_cases = []
        global_is_ARGS = False   # 用于跨文件检测格式一致性
        global_is_KWARGS = False
        # ========== 定义在循环外，file_path 作为参数传入 ==========
        def _format_input(case: _CASE, file_path: Path, i: int) -> _CASE:
            nonlocal global_is_ARGS, global_is_KWARGS
            # JSON 必须是标准格式（含"input"键）
            assert isinstance(case, dict) and 'input' in case, '格式非法，JSON 样例文件不含"input"键。'
            # 判断当前 case 的格式
            if isinstance(case['input'], dict):
                assert global_is_ARGS is False, f"样例文件 {file_path if __FULL_PATH__ else file_path.stem} 中第 {i+1} 个样输入类型不一致，前面是元组 _ARGS 类型"
                global_is_KWARGS = True
            elif isinstance(case['input'], list):
                assert global_is_KWARGS is False, f"样例文件 {file_path if __FULL_PATH__ else file_path.stem} 中第 {i+1} 个样输入类型不一致，前面是字典 _KWARGS 类型"
                global_is_ARGS = True
                case['input'] = tuple(case['input'])  # 统一转换为元组
            else:
                raise ValueError(f"文件 {file_path if __FULL_PATH__ else file_path.stem} 第 {i+1} 个用例 input 类型不正确，实际为 {type(case['input'])}")
            case['cid'] = f"{file_path if __FULL_PATH__ else file_path.stem}_{i}"
            return case
        # ========== 主循环 ==========
        for p in _path_list:
            file_path = Path(p) if os.path.exists(p) else Path(self.relPath) / p
            assert file_path.exists(), f"read_test_case: {file_path} 文件不存在"
            if file_path.suffix.lower() == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                assert isinstance(raw_data, list), f"JSON 文件 {file_path} 根节点必须是列表"
                for i, item in enumerate(raw_data):
                    test_cases.append(_format_input(item, file_path, i))
            else:
                try:
                    parsed_list = parse_test_cases(file_path)
                    for i, item in enumerate(parsed_list):
                        assert isinstance(item, dict) and 'input' in item
                        test_cases.append(_format_input(_CASE(**item,cid=i), file_path, i))
                except Exception as e:
                    raise RuntimeError(f"解析测试文件失败：{file_path}") from e
        return test_cases
    @classmethod
    def _check_cases_is_kwargs(cls, case:Any)->bool:
        if not isinstance(case, dict):
            raise ValueError(f"测试用例 {case['cid']} 必须至少含有 'input' 键的字典类型")
        if 'input' not in case:
            raise ValueError(f"测试用例 {case['cid']} 缺少 'input' 键")
        if isinstance(case['input'], dict):
            return True
        elif isinstance(case['input'], (tuple,list)):
            return False
        else:
            raise ValueError(f"测试用例 {case['cid']} 的 'input' 必须是字典或元组")
    def run(
        self,
        test_cases: List[_CASE],  # 严格要求是 List[CASE_TYPE]
        log_wrong: bool = True,        # 默认记录错误的测试样例
        log_folder: Optional[str] = None,
        early_stop: Optional[Union[int, float]] = None,
        skip_error = False,
        thread: int = 1,
        timeout_s:float = 10,
        summary: bool = False,
    ) -> List[_RESULT]:
        """执行测试用例（自动处理实例化）"""
        # ========== 1. 验证输入格式 ==========
        assert isinstance(test_cases, list), "test_cases 必需是 list 类型"
        if 0 == len(test_cases):
            Warning("SolutionRunner.run：test_cases 为空列表，无需执行。")
            return []
        if __DEBUG__: # 检查所有对象
            for case in test_cases:
                self._check_cases_is_kwargs(case)
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
            if self.has_custom_caller:
                caller = self.solution_module.__dict__[_CUSTOM_CALLER_NAME]
                if __DEBUG__:
                    print(f"调用了 {_CUSTOM_CALLER_NAME}")
            if self._check_cases_is_kwargs(test_cases[0]):
                caller:_EXECUTE_CALLER = main_caller_kwargs
            else:
                caller:_EXECUTE_CALLER = main_caller_args
            if self.main_method is not None:
                bind_func = getattr(self.instance, self.main_method)
            else:
                raise ValueError("暂不支持无 main_method。")
            for case in test_cases:
                if self.main_method is not None:
                    # 执行单用例（核心封装，便于多进程改造）
                    result, log_lines = _execute_dict_case(
                        caller,
                        bind_func,
                        case
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
        else: # 多进程
            if self.has_custom_caller:
                caller_name = _CUSTOM_CALLER_NAME
            elif self._check_cases_is_kwargs(test_cases[0]):
                caller_name = "main_caller_kwargs"
            else:
                caller_name = "main_caller_args"

            ctx = multiprocessing.get_context("spawn")
            group_queue = ctx.Queue()
            output_queue = ctx.Queue()
            early_stop_event = ctx.Event()

            manager = multiprocessing.Manager()          # ✅ 创建 Manager
            status_list = manager.list([None] * thread)  # ✅ 每个 worker 一个槽位，用于记录异常样例（cid，时间戳）

            # 分割测试用例到队列
            groups_num = _geom_queue_generator(len(test_cases), group_queue, rate=1.0/thread)
            output_buff:List[Optional[List[_RESULT]]] = [None]*groups_num
            cases_bytes = json.dumps(test_cases, ensure_ascii=False).encode("utf-8")
            shm = shared_memory.SharedMemory(create=True, size=len(cases_bytes))
            try:
                shm.buf[:len(cases_bytes)] = cases_bytes
                shm_name = shm.name
                shm_size = len(cases_bytes)
                processes = []
                for i in range(thread):
                    tp = ctx.Process(
                        target=_execute_in_process_worker,
                        args=(
                            i,
                            self.source_code_lst,
                            self.main_method,
                            caller_name,
                            log_path,
                            skip_error,
                            log_wrong,
                            shm_name,
                            shm_size,
                            group_queue,
                            output_queue,
                            early_stop_event,
                            status_list,          # ✅ 传递共享状态（后续主进程只读，子进程可读写对应进程id下标）
                        )
                    )
                    processes.append(tp)
                    tp.start()

                # 收集结果 + 进度超时检测
                output_count = wrong_count = 0
                total_count = len(test_cases)
                last_progress = time.time()

                while output_count < total_count:
                    try:
                        qe = output_queue.get(timeout=0.1)
                        if isinstance(qe, _OUT_QELE):
                            output_buff[qe.group_id] = qe.results
                            output_count += len(qe.results)
                            wrong_count += qe.wcnt
                            last_progress = time.time()
                            print(f"主线程：(已收集/总样例数): ({output_count}/{total_count})", end="\r")
                            # 普通错误触发早停
                            if self._check_early_stop(output_count, wrong_count, early_stop):
                                early_stop_event.set()
                    except Empty:
                        # 超时检测
                        for wid,status in enumerate(status_list):
                            if status is None: continue
                            cid,ts = status
                            if time.time() - ts > timeout_s:
                                print(f"\n⚠️ Worker {wid} 超时：最后用例: {cid}")
                                if processes[wid].is_alive():
                                    processes[wid].terminate()   # 触发 SIGTERM → 软终止打印
                                early_stop_event.set() # 有进程超时触发早停
                        # 所有进程已退出则跳出循环
                        if not any(tp.is_alive() for tp in processes):
                            break

                # 确保所有进程终止
                for tp in processes:
                    if tp.is_alive():
                        tp.terminate()
                    tp.join()

                # 合并结果（和之前一样）
                valid_lists = [out for out in output_buff if out]
                results = list(merge(*valid_lists, key=lambda x: x['cid']))
            finally:
                shm.close()
                shm.unlink()

        # 单/多进程：总结结果
        if summary:
            self.summary_results(results,verbose=True)
        return results
    @classmethod
    def summary_results(cls,results:List[_RESULT],verbose = True)-> Tuple[int,int]:
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
    def get_expected_cases(self, run_results: List[_RESULT]) -> List[_CASE]:
        """从run结果中过滤出成功的测试用例，重新编号以#开头的cid，并将'output'重命名为'expected'"""
        expected_cases = []
        case_id = 0
        max_cases_digit = len(str(len(run_results)))
        total_count = len(run_results)
        for result in run_results:
            if 'error' not in result:
                case_id += 1
                output = result.copy()
                # print(f"output={output}")
                # ✅ zero padding
                output['cid'] = f"#{self.relPath.stem}_{case_id:0{max_cases_digit}d}"
                if 'expected' not in output: # 此时须确保 output 存在
                    output['expected'] = output.pop('output')
                output.pop('elapsed', None)
                expected_cases.append(output)
        print(f"✅ 从 {total_count} 个测试用例中筛选出 {case_id} 个有效用例")
        return expected_cases
    def auto_path_cases(self) -> Path:
        base_name = os.path.splitext(os.path.basename(self.solution_file))[0]
        # 保存到相对目录下
        return self.relPath / f"{base_name}.json"
    def save_test_cases(self, test_cases: List[_CASE], file_path: Optional[os.PathLike] = None) -> Path:
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
    
    # def get_cases_generator(self,documentation:Union[os.PathLike,str],AI=None,attached_attentions:List[str]=[])->str:
    #     """自动向AI提问得到问题的测试样例生成器"""
    #     if not os.path.exists(documentation):
    #         documentation = self.relPath/documentation
    #     with open(documentation , encoding="utf-8") as fp:
    #         request_text = fp.read()
    #     codes = f"<init-code>\n{self.source_code_lst}\n</init-code>\n<student-code>\n{self.student_code}\n</student-code>"
    #     if AI is not None:
    #         raise ValueError("暂时不支持自动提问")
    #         return None
    #     # AI 未指定，或者网络等错误
    #     # self.main_method 为 None时，无法检测 self.has_custom_type ，因此依靠 is_unique_caller 兜底，而将 has_custom_type 视为 False
    #     return TEST_CASE_GENERATOR.get_manual_prompt(codes,request_text, self.main_method is not None ,bool(self.has_custom_type),attached_attentions)