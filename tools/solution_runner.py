# tools/solution_runner.py
import os,sys,io
import math
import inspect
import copy
import contextlib
import warnings
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
import ctypes
__DEBUG__ = os.getenv("LEETCODE_RUNNER_DEBUG", "0") == "1"
__FULL_PATH__ = os.getenv("LEETCODE_RUNNER_FULL_PATH", "0") == "1"
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
def _values_equal(expected: Any, output: Any) -> bool:
    """Compare normalized LeetCode values without NumPy truth-value ambiguity."""
    if isinstance(expected, float) or isinstance(output, float):
        if isinstance(expected, (int, float)) and isinstance(output, (int, float)):
            return math.isclose(float(expected), float(output), rel_tol=1e-9, abs_tol=1e-9)
    if isinstance(expected, dict) and isinstance(output, dict):
        return expected.keys() == output.keys() and all(
            _values_equal(expected[key], output[key]) for key in expected
        )
    if isinstance(expected, (list, tuple)) and isinstance(output, (list, tuple)):
        return len(expected) == len(output) and all(
            _values_equal(left, right) for left, right in zip(expected, output)
        )
    try:
        return bool(expected == output)
    except (TypeError, ValueError):
        return False


def _is_wrong(result:_RESULT)->bool:
    return (
        'expected' in result
        and 'output' in result
        and not _values_equal(result['expected'], result['output'])
    )
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
    # 学生算法常会原地修改 list/tree。每个用例必须隔离，否则后续算法
    # 会读到已经被前一次执行篡改的输入。
    result_dict:_RESULT = copy.deepcopy(case)
    # 日志格式
    def _add_log(content: str):
        log_lines.append(f"{case['cid']}:\t{content}")
    # 记录时间执行时间
    start_time = time.perf_counter()
    try:
        _add_log(f"Running '{solution_or_function.__name__ if callable(solution_or_function) else type(solution_or_function)}' with case: {case.get('test_case_key', f"{case['cid']}")}")
        # 提取输入
        input_val = copy.deepcopy(case['input'])
        # 记录输入到 log
        _add_log(f">>> INPUT\n{_compacted_json.dumps(input_val, indent=2)}")
        captured_output = io.StringIO()
        with contextlib.redirect_stdout(captured_output):
            output_val = caller(solution_or_function,input_val)
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
        elapsed = time.perf_counter() - start_time
        result_dict['error'] = str(e)
        result_dict['traceback'] = traceback.format_exc()
        result_dict['elapsed'] = elapsed
        _add_log("!!! EXCEPTION OCCURRED:")
        _add_log(traceback.format_exc())
    return result_dict, log_lines

class CrashRecord(ctypes.Structure):
    _fields_ = [
        ('cases_index', ctypes.c_uint64),   # 当前正在执行的用例在列表中的下标
        ('timestamp',    ctypes.c_double),   # 开始执行时的时间戳
    ]
    
def _execute_in_process_worker(
    worker_id: int,
    source_code_lst: List[str],
    method_name: Optional[str],
    caller_name: str,
    log_path: os.PathLike,
    skip_error: bool,
    log_wrong: bool,
    input_queue: multiprocessing.Queue,      # 接收 int 下标
    output_queue: multiprocessing.Queue,     # 发送 _RESULT
    early_stop_event: multiprocessing.Event,
    status_slot,                             # RawValue(CrashRecord)
    shm_name: str, # 测试样例共享 shared_memory 键名
    shm_size: int,
):
    # ---------- 加载测试用例（一次性）----------
    from multiprocessing import shared_memory
    shm = shared_memory.SharedMemory(name=shm_name)
    try:
        raw = bytes(shm.buf[:shm_size])
        test_cases = json.loads(raw.decode("utf-8"))

        # ---------- 创建虚拟模块 ----------
        module = _create_solution_module(source_code_lst)
        _Solution = module.__dict__[_SOLUTION_TYPE_NAME_]
        caller = module.__dict__[caller_name]
        instance_or_function = _Solution()
        if method_name:
            instance_or_function = getattr(instance_or_function, method_name)

        # ---------- 处理任务 ----------
        while not early_stop_event.is_set():
            idx = input_queue.get()
            if idx is None:
                break

            case = test_cases[idx]
            status_slot.cases_index = idx
            status_slot.timestamp = time.time()

            result, log_lines = _execute_dict_case(caller, instance_or_function, case)
            if 'error' in result:
                error_log_path = _log_result(result, log_lines, "ERROR_", log_path)
                output_queue.put(result)
                if not skip_error:
                    early_stop_event.set()
                    raise RuntimeError(
                        f"执行报错（日志: {error_log_path}）：\n{result['error']}"
                    )
            else:
                if _is_wrong(result) and log_wrong:
                    _log_result(result, log_lines, "Wrong_", log_path)
                output_queue.put(result)

            status_slot.cases_index = 0
            status_slot.timestamp = 0.0
    finally:
        # 子进程只关闭自己的句柄；共享内存由主进程 unlink。
        status_slot.cases_index = 0
        status_slot.timestamp = 0.0
        shm.close()

class SolutionRunner:
    @classmethod
    def _read_code(cls, code_file: os.PathLike) -> str:
        assert os.path.exists(code_file), f"文件不存在: {code_file}"
        # 确保文件类型为 ".py"
        assert str(code_file).endswith('.py'), f"应当输入 .py 文件，实际为: {code_file}"
        raw = Path(code_file).read_bytes()
        errors = []
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError as exc:
                errors.append(f"{encoding}: {exc}")
        raise UnicodeError(
            f"无法解码代码文件 {code_file}；已尝试 UTF-8/BOM/GB18030。"
            + " | ".join(errors)
        )

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
        # 3 创建 solution 的虚拟环境
        self.solution_module = _create_solution_module(self.source_code_lst)
        # 4. 获取Solution类
        if _SOLUTION_TYPE_NAME_ not in self.solution_module.__dict__:
            raise ValueError(f"学生代码中未定义 {_SOLUTION_TYPE_NAME_} 类")
        module_Solution = self.solution_module.__dict__[_SOLUTION_TYPE_NAME_]
        self.solution_class = module_Solution
        self.instance = module_Solution()

        # exec 创建的动态模块通常无法被 inspect.getsource 回溯。直接从
        # 原始学生源码 AST 提取方法，供复杂度分析与 Agent 使用。
        method_sources = {}
        try:
            student_tree = ast.parse(self.student_code)
            for node in student_tree.body:
                if isinstance(node, ast.ClassDef) and node.name == _SOLUTION_TYPE_NAME_:
                    for child in node.body:
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            source = ast.get_source_segment(self.student_code, child)
                            if source:
                                method_sources[child.name] = source
        except SyntaxError:
            # 动态模块创建阶段已会给出真正的语法异常；这里仅保持诊断健壮。
            method_sources = {}

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
                src = method_sources.get(name, "")
                if not src:
                    try:
                        src = inspect.getsource(method)
                    except (OSError, TypeError):
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
                if __DEBUG__:
                    print("存在多个方法；执行时需要 conversion.py 中的 custom_caller。")
                self.main_method = None  # 用 None 表示可调用方法不唯一

        # 7. 若主方法唯一，初始化实例、签名及类型信息
        if self.main_method is not None:
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
        path_list: Optional[Union[os.PathLike, List[os.PathLike]]] = None
    ) -> List[_CASE]:
        """读取并解析测试用例文件（支持 _CASE_TYPE 格式，兼容元组和字典）"""
        if path_list is None:
            _path_list = []
        else:
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
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    raw_data = json.load(f)
                assert isinstance(raw_data, list), f"JSON 文件 {file_path} 根节点必须是列表"
                for i, item in enumerate(raw_data):
                    test_cases.append(_format_input(item, file_path, i))
            else:
                try:
                    params_num = len(self.sig.parameters) if self.main_method is not None else None
                    parsed_list = parse_test_cases(file_path, params_num=params_num)
                    for i, item in enumerate(parsed_list):
                        assert isinstance(item, dict) and 'input' in item
                        test_cases.append(_format_input(_CASE(**item,cid=i), file_path, i))
                except Exception as e:
                    raise RuntimeError(f"解析测试文件失败：{file_path}") from e
        return test_cases
    @classmethod
    def _check_cases_is_kwargs(cls, case:Any)->bool:
        if not isinstance(case, dict):
            raise ValueError(f"测试用例必须是至少含有 'input' 键的字典，实际为 {type(case).__name__}")
        if 'input' not in case:
            raise ValueError(f"测试用例 {case.get('cid', '<unknown>')} 缺少 'input' 键")
        if isinstance(case['input'], dict):
            return True
        elif isinstance(case['input'], (tuple,list)):
            return False
        else:
            raise ValueError(f"测试用例 {case.get('cid', '<unknown>')} 的 'input' 必须是字典或元组")
    def run(
        self,
        test_cases: List[_CASE],  # 严格要求是 List[CASE_TYPE]
        log_wrong: bool = True,        # 默认记录错误的测试样例
        log_folder: Optional[str] = None,
        early_stop: Optional[Union[int, float]] = None,
        skip_error = False,
        thread: int = 1,
        timeout_s:Optional[float] = None,
        summary: bool = False,
    ) -> List[_RESULT]:
        """执行测试用例（自动处理实例化）"""
        # ========== 1. 验证输入格式 ==========
        if not isinstance(test_cases, list):
            raise TypeError("test_cases 必须是 list 类型")
        if 0 == len(test_cases):
            warnings.warn("SolutionRunner.run：test_cases 为空列表，无需执行。", RuntimeWarning)
            return []
        normalized_cases = []
        seen_cids = set()
        for index, case in enumerate(test_cases):
            self._check_cases_is_kwargs(case)
            normalized = copy.deepcopy(case)
            normalized.setdefault('cid', index)
            cid = normalized['cid']
            if not isinstance(cid, (str, int)):
                raise TypeError("测试用例 cid 必须为 str 或 int")
            if cid in seen_cids:
                raise ValueError(f"测试用例 cid 重复：{cid!r}")
            seen_cids.add(cid)
            if isinstance(normalized['input'], list):
                normalized['input'] = tuple(normalized['input'])
            normalized_cases.append(normalized)
        test_cases = normalized_cases

        if early_stop is not None and early_stop <= 0:
            raise ValueError("early_stop 必须大于 0")
        if timeout_s is not None and timeout_s <= 0:
            raise ValueError("timeout_s 必须大于 0 或为 None")
        if self.main_method is None and not self.has_custom_caller:
            raise ValueError("Solution 存在多个方法时必须提供 conversion.py/custom_caller")
        # 日志路径
        log_path = self.relPath / (self.file_name if log_folder is None else log_folder)
        os.makedirs(log_path,exist_ok=True)
        if __DEBUG__:
            print("log_path:",log_path)

        results = []
        wrong_count = 0
        def check_early_stop(verbose=True)->bool:
            nonlocal early_stop,wrong_count,results
            """检查是否触发早停"""
            if early_stop is None: return False
            total_cnt = len(results)
            if early_stop < 1:
                ratio = wrong_count / total_cnt if total_cnt else 0.0
                if ratio >= early_stop:
                    if(verbose):print(f"错误样例比例 = {wrong_count}/{total_cnt} = {ratio:.4f} >= {early_stop:.4f} (阈值)，触发早停。")
                    return True
            elif wrong_count >= math.ceil(early_stop):
                if(verbose):print(f"错误样例数量 = {wrong_count} >= {math.ceil(early_stop):d} (阈值)，触发早停。")
                return True
            return False

        # ========== 2. 执行所有用例 ==========
        if not isinstance(thread, int) or thread == 0 or thread < -1:
            raise ValueError("thread 必须为 -1 或正整数")
        logical_cpu_count = os.cpu_count() or 1
        if -1==thread:
            thread = logical_cpu_count
        elif thread > logical_cpu_count:
            warnings.warn(
                f"工作进程数 {thread} 超过逻辑处理器数 {logical_cpu_count}，"
                "可能因过度调度而降低性能。",
                RuntimeWarning,
                stacklevel=2,
            )
        # 工作进程多于测试用例时只会产生空闲进程，不属于有效并行。
        thread = min(thread, len(test_cases))

        # Windows 无法安全中断同进程中的死循环。指定 timeout 时，即使只用
        # 1 个 worker 也使用隔离子进程；未指定则保留低开销的直接执行。
        use_processes = thread > 1 or timeout_s is not None
        if not use_processes:
            if self.has_custom_caller:
                caller = self.solution_module.__dict__[_CUSTOM_CALLER_NAME]
                if __DEBUG__:
                    print(f"调用了 {_CUSTOM_CALLER_NAME}")
            elif self._check_cases_is_kwargs(test_cases[0]):
                caller:_EXECUTE_CALLER = main_caller_kwargs
            else:
                caller:_EXECUTE_CALLER = main_caller_args
            bind_func = (
                getattr(self.instance, self.main_method)
                if self.main_method is not None
                else self.instance
            )
            for case in test_cases:
                # custom_caller 在多方法场景接收 Solution 实例；默认 caller
                # 则接收唯一主方法的绑定函数。
                result, log_lines = _execute_dict_case(caller, bind_func, case)
                results.append(result)
                if 'error' in result:
                    error_log_path = _log_result(result,log_lines,"ERROR_",log_path)
                    if skip_error:
                        warnings.warn(
                            f"跳过报错用例（已经保存日志到 {error_log_path}）",
                            RuntimeWarning,
                        )
                        wrong_count += 1 # error 当然也算“错误”
                    else:
                        raise Exception(f"执行报错（已经保存日志到 {error_log_path}）：\n{result['error']}")
                elif _is_wrong(result):
                    if log_wrong:
                        _log_result(result,log_lines,"Wrong_",log_path)
                    wrong_count += 1
                    if check_early_stop(): break # 触发早停
        else: # 隔离子进程（一个或多个 worker）
            # ---------- 1. 准备共享内存 ----------
            cases_bytes = json.dumps(test_cases, ensure_ascii=False).encode("utf-8")
            shm = shared_memory.SharedMemory(create=True, size=len(cases_bytes))
            shm.buf[:len(cases_bytes)] = cases_bytes
            shm_name = shm.name
            shm_size = len(cases_bytes)

            # ---------- 2. 创建通信对象 ----------
            ctx = multiprocessing.get_context("spawn")
            input_queue = ctx.Queue()
            output_queue = ctx.Queue()
            early_stop_event = ctx.Event()

            # 为每个子进程创建独立的状态槽
            status_slots = [ctx.RawValue(CrashRecord, 0, 0.0) for _ in range(thread)]

            # 将所有用例下标放入输入队列
            for i in range(len(test_cases)):
                input_queue.put(i)
            # Queue.empty() 在多进程下不可靠，使用显式哨兵结束 worker。
            for _ in range(thread):
                input_queue.put(None)

            # ---------- 3. 确定 caller 名称 ----------
            if self.has_custom_caller:
                caller_name = _CUSTOM_CALLER_NAME
            elif self._check_cases_is_kwargs(test_cases[0]):
                caller_name = "main_caller_kwargs"
            else:
                caller_name = "main_caller_args"

            # ---------- 4. 启动子进程 ----------
            processes = []
            for i in range(thread):
                p = ctx.Process(
                    target=_execute_in_process_worker,
                    args=(
                        i,
                        self.source_code_lst,
                        self.main_method,
                        caller_name,
                        log_path,
                        skip_error,
                        log_wrong,
                        input_queue,
                        output_queue,
                        early_stop_event,
                        status_slots[i],
                        shm_name,
                        shm_size,
                    )
                )
                processes.append(p)
                p.start()

            # ---------- 4. 收集结果 + 超时检测 ----------
            total_count = len(test_cases)
            tle_log_path = log_path  # 可复用

            while len(results) < total_count:
                # 4.1 尝试从输出队列获取正常结果
                try:
                    result = output_queue.get(timeout=0.1)
                    results.append(result)
                    if _is_wrong(result) or 'error' in result:
                        wrong_count += 1
                        # 检查早停条件
                        if not early_stop_event.is_set() and check_early_stop():
                            early_stop_event.set()
                except Empty:
                    pass

                # 4.2 超时检测
                now = time.time()
                for wid, slot in enumerate(status_slots):
                    if (
                        timeout_s is not None
                        and slot.timestamp > 0
                        and (now - slot.timestamp) > timeout_s
                    ):
                        # 该子进程超时！
                        idx = slot.cases_index
                        if idx < total_count:   # 有效性检查
                            case:_CASE = test_cases[idx]
                            # 构造 TLE 结果
                            tle_result:_RESULT = {
                                **case,
                                'error': 'Time Limit Exceeded (TLE)',
                                'traceback': 'Process terminated due to timeout',
                                'elapsed': timeout_s,
                            }
                            # 写日志（与正常日志格式一致）
                            log_lines = [
                                f"TLE: Worker {wid}, cid: {case['cid']}",
                                f">>> INPUT\n{_compacted_json.dumps(case['input'], indent=2)}",
                            ]
                            _log_result(tle_result, log_lines, "TLE_", tle_log_path)
                            # Windows 控制台可能仍使用 GBK，避免状态信息本身因
                            # emoji 编码失败而打断超时清理流程。
                            print(
                                f"\n[TLE] Worker {wid} 超时: {case.get('cid', '')} "
                                f"(>{timeout_s}s), 已记录 TLE 日志",
                                flush=True,
                            )

                            # 将 TLE 结果视为已完成，加入收集列表
                            results.append(tle_result)

                            # TLE 与 ERROR 类似：若无 skip_error 需触发早停
                            wrong_count += 1
                            if not skip_error or (not early_stop_event.is_set() and check_early_stop()):
                                early_stop_event.set()

                        # 强制终止超时进程
                        if processes[wid].is_alive():
                            processes[wid].terminate()
                            processes[wid].join()
                        # 清空状态槽，避免重复处理
                        slot.cases_index = 0
                        slot.timestamp = 0.0

                        # 跳过错误时继续消费剩余样例；单 worker 超时也不会丢任务。
                        if skip_error and not early_stop_event.is_set():
                            replacement = ctx.Process(
                                target=_execute_in_process_worker,
                                args=(
                                    wid,
                                    self.source_code_lst,
                                    self.main_method,
                                    caller_name,
                                    log_path,
                                    skip_error,
                                    log_wrong,
                                    input_queue,
                                    output_queue,
                                    early_stop_event,
                                    status_slots[wid],
                                    shm_name,
                                    shm_size,
                                ),
                            )
                            processes[wid] = replacement
                            replacement.start()

                # 4.3 检查是否所有进程都已结束且结果不足（提前退出）
                if all(not p.is_alive() for p in processes) and len(results) < total_count:
                    # 进程退出与 Queue feeder 刷新并非严格同步，再做一次有界排空。
                    while True:
                        try:
                            result = output_queue.get(timeout=0.05)
                        except Empty:
                            break
                        results.append(result)
                        if _is_wrong(result) or 'error' in result:
                            wrong_count += 1
                    break

            # ---------- 5. 清理 ----------
            # 确保所有子进程终止
            for p in processes:
                if p.is_alive():
                    p.terminate()
                p.join()

            shm.close()
            shm.unlink()
            input_queue.close()
            output_queue.close()

            # 按输入顺序恢复结果，兼容 cid 分别使用整数或字符串。
            case_order = {case['cid']: index for index, case in enumerate(test_cases)}
            results.sort(key=lambda item: case_order[item['cid']])

        # 单/多进程：总结结果
        if summary:
            self.summary_results(results,verbose=True)
        return results
    @classmethod
    def summary_results(cls, results: List[_RESULT], verbose=True) -> Tuple[int, int]:
        right = valid = 0
        error_count = 0
        tle_count = 0
        for case in results:
            # 统计错误与超时
            if 'error' in case:
                if 'TLE' in case['error']:
                    tle_count += 1
                else:
                    error_count += 1
            # 原有正确/错误统计（仅对有 expected 的用例）
            if 'expected' in case and 'output' in case:
                valid += 1
                if not _values_equal(case['expected'], case['output']):
                    if verbose:
                        print(f"wrong: {case}")
                else:
                    right += 1
        if verbose:
            print(f"right / total_valid: {right} / {valid}")
            if error_count > 0:
                print(f"❌ 执行错误用例数: {error_count}")
            if tle_count > 0:
                print(f"⏱️ 超时用例数 (TLE): {tle_count}")
        return right, valid

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
