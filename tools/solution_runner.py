# tools/solution_runner.py
import os
import inspect
from pathlib import Path
import logging
import datetime, time
from typing import Any, Callable, Dict, List, Tuple, Union, Optional, get_type_hints
import ast, re
import types
import traceback
from charset_normalizer.api import from_bytes  # 自动检测编码
try:
    from examples_parser import parse_test_cases,CompactLeafListEncoder
    from custom_init import input_parser_registry, ListNode, TreeNode, Optional, List, Dict
except:
    from tools.examples_parser import parse_test_cases,CompactLeafListEncoder
    from tools.custom_init import input_parser_registry, ListNode, TreeNode, Optional, List, Dict

"""
一个标准的测试样例的格式为：
    - 字典: {"input": case [,"output":Any, "expected":Any,"error":str , ...]}
    - 其中的 case 可以是：
        - 字典：其键为被测函数的变量名，其值则为变量值
        - 元组：按被测函数的变量顺序排列的变量值
"""
_CASE_TYPE = Dict[str, Union[Dict[str, Any], Tuple, Any]]


# ========== 全局辅助函数（放在类外部或类内静态方法）==========
def _compact_json(obj: List[_CASE_TYPE]) -> str:
    """智能JSON序列化：外层缩进，叶子节点紧凑"""
    return json.dumps(
        obj,
        cls=CompactLeafListEncoder,
        indent=2,
        ensure_ascii=False,
        default=str
    )

def _sanitize_filename(name: str) -> str:
    """安全文件名转换"""
    for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        name = name.replace(ch, '_')
    return name.strip().rstrip('.')

def _get_unique_log_path(base_name: str) -> str:
    """生成唯一日志路径"""
    if not base_name.endswith('.log'):
        base_name += '.log'
    if not os.path.exists(base_name):
        return base_name
    counter = 1
    while counter < 1000:
        candidate = f"{base_name.rstrip('.log')}.{counter}.log"
        if not os.path.exists(candidate):
            return candidate
        counter += 1
    raise Exception("无法生成唯一日志路径")

class SolutionRunner:
    def __init__(self, solution_file: str, main_method: Optional[str] = None) -> None:
        """
        初始化 SolutionRunner，自动加载学生代码文件。
        :param solution_file: 学生代码文件路径（如 "P82_V0.py"）
        :param main_method: 指定主方法名（当Solution有多个方法时），默认None表示自动选择唯一方法
        """
        # 1. 读取并自动检测编码（支持中文）
        with open(solution_file, 'rb') as f:
            raw = f.read()
        result = from_bytes(raw).best()
        student_code = str(result) if result else raw.decode('utf-8', errors='ignore')
        
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
        exec(student_code, mod.__dict__)
        
        # 4. 获取Solution类
        if 'Solution' not in mod.__dict__:
            raise ValueError("学生代码中未定义 Solution 类")
        self.Solution = mod.Solution
        self.solution_file = solution_file
        
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
        path_list: Union[str, os.PathLike, List[Union[str, Path]]],
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
        
        cwd = Path.cwd()
        test_cases = []
        
        # 创建临时实例获取绑定方法签名
        temp_instance = self.Solution()
        bound_method = getattr(temp_instance, self.method_name)
        sig = inspect.signature(bound_method)
        
        for file_path in all_files:
            try:
                parsed_list = parse_test_cases(str(file_path))
            except Exception as e:
                raise RuntimeError(f"解析测试文件失败: {file_path}") from e
            
            for raw_case in parsed_list:
                
                # 确保是标准CASE_TYPE格式
                if isinstance(raw_case, dict) and 'input' in raw_case:
                    converted_case = raw_case
                elif isinstance(raw_case, (dict, tuple)):
                    converted_case = {'input': raw_case}
                else:
                    raise ValueError(f"测试用例格式非法: {type(raw_case)}")
                
                # 验证绑定
                if isinstance(converted_case['input'], dict):
                    sig.bind(**converted_case['input'])
                elif isinstance(converted_case['input'], tuple):
                    sig.bind(*converted_case['input'])
                else:
                    raise ValueError("测试用例的input必须是字典或元组")
                
                test_cases[key] = converted_case
        
        return test_cases

    def run(
        self,
        test_cases: List[_CASE_TYPE],  # 严格要求是 List[CASE_TYPE]
        log_suffix: Optional[str] = None,
        only_log_wrong: bool = False,
        early_stop: Optional[Union[int, float]] = None,
        thread: int = 1,
        timeout_s: Optional[float] = 10,
    ) -> List[Dict[str, Any]]:
        """执行测试用例（自动处理实例化）"""
        # ========== 1. 验证输入格式 ==========
        for idx, case in enumerate(test_cases):
            if not isinstance(case, dict):
                raise ValueError(f"测试用例 {idx} 必须是字典格式")
            if 'input' not in case:
                raise ValueError(f"测试用例 {idx} 缺少 'input' 键")
            if not isinstance(case['input'], (dict, tuple)):
                raise ValueError(f"测试用例 {idx} 的 'input' 必须是字典或元组")
        
        # ========== 2. 执行所有用例 ==========
        results = []
        error_count = 0
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        func_name = getattr(self.method, '__name__', 'unknown')
        
        for idx, case in enumerate(test_cases):
            # 执行单用例（核心封装，便于多进程改造）
            result, log_lines = self._execute_single_case(
                case=case,
                case_idx=idx,
                func_name=func_name,
                today=today
            )
            results.append(result)
            
            # 记录日志
            if log_suffix is not None and log_lines:
                self._write_case_log(case, log_lines, log_suffix)
            
            # 早停检查
            if self._check_early_stop(early_stop, error_count, len(results), result):
                break
        
        return results

    def _execute_single_case(
        self,
        case: _CASE_TYPE,
        case_idx: int,
        func_name: str,
        today: str
    ) -> Tuple[_CASE_TYPE, List[str]]:
        """执行单个测试用例（核心封装）"""
        log_lines = []
        result_dict = case.copy()
        
        def _add_log(content: str):
            ts = time.strftime("%H:%M:%S", time.localtime())
            log_lines.append(f"{ts}\t{content}")
        
        try:
            _add_log(f"[{today}] Running '{func_name}' with case: {case.get('test_case_key', f'#{case_idx+1}')}")
            
            input_val = case['input']
            instance = self.Solution()
            
            if isinstance(input_val, dict):
                _add_log(f">>> INPUT\n{_compact_json(input_val)}")
                output = self.method(instance, **input_val)
            elif isinstance(input_val, tuple):
                _add_log(f">>> INPUT\n{_compact_json(list(input_val))}")
                output = self.method(instance, *input_val)
            else:
                raise ValueError("测试用例的input必须是字典或元组")
            
            elapsed = time.perf_counter() - time.perf_counter()
            result_dict['output'] = output
            result_dict['elapsed'] = elapsed
            _add_log(f"<<< OUTPUT (elapsed: {elapsed:.6f}s)\n{_compact_json(output)}")
            
        except Exception as e:
            elapsed = time.perf_counter() - time.perf_counter()
            result_dict['error'] = str(e)
            result_dict['traceback'] = traceback.format_exc()
            result_dict['elapsed'] = elapsed
            _add_log("!!! EXCEPTION OCCURRED:")
            _add_log(traceback.format_exc())
        
        return result_dict, log_lines

    def _write_case_log(self, case: Dict[str, Any], log_lines: List[str], log_suffix: str):
        """写入单个用例日志（原子操作）"""
        key = case.get('test_case_key', f"case_{case.get('idx', 0)+1}")
        safe_key = _sanitize_filename(key)
        log_path = _get_unique_log_path(f"{safe_key}{log_suffix}")
        
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(log_lines))

    def _check_early_stop(
        self,
        early_stop: Optional[Union[int, float]],
        error_count: int,
        total: int,
        last_result: Dict[str, Any]
    ) -> bool:
        """检查是否触发早停"""
        if early_stop is None or 'error' not in last_result:
            return False
        
        if isinstance(early_stop, int) and (error_count + 1) >= early_stop:
            print(f"⚠️ Early stop: {error_count + 1} errors >= threshold {early_stop}")
            return True
        
        if isinstance(early_stop, float):
            error_rate = (error_count + 1) / total
            if error_rate >= early_stop:
                print(f"⚠️ Early stop: error rate {error_rate:.1%} >= {early_stop:.1%}")
                return True
        return False

    def get_expected_cases(self, run_results: List[_CASE_TYPE]) -> List[_CASE_TYPE]:
        """从run结果中过滤出成功的测试用例，并将'output'重命名为'expected'"""
        expected_cases = []
        success_count = 0
        total_count = len(run_results)
        
        for result in run_results:
            if 'error' not in result:
                expected_case = result.copy()
                expected_case['expected'] = expected_case.pop('output')
                expected_case.pop('elapsed', None)
                expected_cases.append(expected_case)
                success_count += 1
        
        print(f"✅ 从 {total_count} 个测试用例中筛选出 {success_count} 个有效用例")
        return expected_cases

    def save_test_cases(self, test_cases: List[_CASE_TYPE], file_path: Optional[str] = None) -> str:
        """保存测试用例到JSON文件"""
        if file_path is None:
            base_name = os.path.splitext(os.path.basename(self.solution_file))[0]
            file_path = f"{base_name}.json"
        
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(test_cases, f, cls=CompactLeafListEncoder, indent=2, ensure_ascii=False)
        
        print(f"💾 已保存 {len(test_cases)} 个测试用例到: {file_path}")
        return file_path