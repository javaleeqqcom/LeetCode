# tools/solution_runner.py

import os
import inspect
from pathlib import Path
import logging
import json
import datetime, time
from typing import Any, Callable, Dict, List, Tuple, Union, Optional, get_type_hints
import ast,re
import types
import traceback
from charset_normalizer.api import from_bytes  # 自动检测编码

try:
    from examples_parser import parse_test_cases
    from custom_init import input_parser_registry, ListNode, TreeNode, Optional, List, Dict
except:
    from tools.examples_parser import parse_test_cases
    from tools.custom_init import input_parser_registry, ListNode, TreeNode, Optional, List, Dict

def _convert_case_by_signature(case: Union[Dict, Tuple], sig: inspect.Signature) -> Union[Dict, Tuple]:
    """对测试用例执行类型转换（精确匹配）"""
    param_names = list(sig.parameters.keys())
    type_hints = {}
    try:
        type_hints = get_type_hints(sig, globalns={}, localns={})
    except Exception:
        pass

    if isinstance(case, dict):
        input_dict = case.get('input', {})
        converted = {}
        for name in param_names:
            if name not in input_dict:
                continue
            value = input_dict[name]
            target_type = type_hints.get(name)
            source_type = type(value)
            key = (target_type, source_type)
            converter = input_parser_registry.get(key)
            converted[name] = converter(value) if converter is not None else value
        return {**case, 'input': converted}
    elif isinstance(case, tuple):
        converted_values = []
        for i, value in enumerate(case):
            if i >= len(param_names):
                break
            name = param_names[i]
            target_type = type_hints.get(name)
            source_type = type(value)
            key = (target_type, source_type)
            converter = input_parser_registry.get(key)
            converted_values.append(converter(value) if converter is not None else value)
        return tuple(converted_values)
    else:
        raise ValueError(f"不支持的用例类型: {type(case)}")

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
        self.solution_file = solution_file  # 保存solution_file路径
        
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
    ) -> Dict[str, Union[Dict, Tuple]]:
        """读取并解析测试用例文件（自动完成类型转换）"""
# 待新增：支持 .json  （应该用 json5 非常轻松支持）

        from glob import glob
        if not isinstance(path_list, list):
            assert isinstance(path_list, Union[str, Path])
            path_list = [path_list,]
        
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
        test_cases_dict = {}
        # 创建一个临时实例来获取绑定方法的签名（排除self参数）
        temp_instance = self.Solution()
        bound_method = getattr(temp_instance, self.method_name)
        sig = inspect.signature(bound_method)
        
        for file_path in all_files:
            try:
                parsed_list = parse_test_cases(str(file_path))
            except Exception as e:
                raise RuntimeError(f"解析测试文件失败: {file_path}") from e
            
            for i, raw_case in enumerate(parsed_list):
                rel_path = str(file_path.relative_to(cwd)) if cwd in file_path.parents else str(file_path)
                key = f"{rel_path}#{i+1}"
                converted_case = _convert_case_by_signature(raw_case, sig)
                
                # 验证绑定（使用转换后的值和绑定方法的签名）
                if isinstance(converted_case, dict):
                    sig.bind(**converted_case.get('input', {}))
                else:
                    sig.bind(*converted_case)
                
                test_cases_dict[key] = converted_case
        
        return test_cases_dict

    def run(
        self,
        test_cases: Dict[str, Union[Dict, Tuple]],
        log_suffix: Optional[str] = None,
        only_log_wrong = False, # 是否只记录错误结果（通常仅用于大量随机测试样例时）
        early_stop: Optional[Union[int,float]] = None, # 当测试样例出错达到该阈值时，提前停止执行（通常仅用于大量随机测试）
        thread = 1,             # 多进程运行（为1则用单进程，通常仅用于大量随机测试，leetcode 算法题的测试样例之间相互独立，因此可以多进程加速，并且应当选用开销小的多进程方法）
        timeout_s: Optional[float] = 10,  # 超时时间秒（为None则不设置，因为算法题通常都有时间限制，而且设置可以避免死循环，注意多线程时每个线程独立计时，超时返回 None 且判定为错误，需要用错误码区分是那种情况）
    ) -> Dict[str, Any]:
        """执行测试用例（自动处理实例化）"""
# 待修改！

        results = {}
        for key, case in test_cases.items():
            logger = None
            log_file = None
            if log_suffix is not None:
                safe_key = _sanitize_filename(key)
                log_base_name = f"{safe_key}{log_suffix}"
                log_file = _get_unique_log_path(log_base_name)
                logger_name = f"runner_logger_{abs(hash(log_file)) % (10**8)}"
                logger = logging.getLogger(logger_name)
                logger.setLevel(logging.INFO)
                logger.propagate = False
                # 移除旧 handlers（避免重复）
                logger.handlers.clear()
                fh = logging.FileHandler(log_file, encoding='utf-8')
                formatter = logging.Formatter(fmt='%(asctime)s:\t%(message)s')
                # 仅输出 HH:MM:SS，微秒已通过 msecs 提供
                formatter.formatTime = lambda record, datefmt=None: time.strftime("%H:%M:%S", time.localtime(record.created))
                fh.setFormatter(formatter)
                logger.addHandler(fh)
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                func_name = getattr(self.method, '__name__', 'unknown_function')
                logger.info(f"[{today}] Running function '{func_name}' with test case key: {key}")
                logger.info(f"Log file: {log_file}")
            
            try:
                if isinstance(case, dict):
                    input_args = case.get('input', {})
                    if logger:
                        logger.info(f">>> INPUT\n{json.dumps(input_args, indent=2, ensure_ascii=False, default=str)}")
                    start_time = time.perf_counter()
                    instance = self.Solution()
                    result = self.method(instance, **input_args)
                    elapsed = time.perf_counter() - start_time
                elif isinstance(case, tuple):
                    if logger:
                        logger.info(f">>> INPUT\n{json.dumps(list(case), indent=2, ensure_ascii=False, default=str)}")
                    start_time = time.perf_counter()
                    instance = self.Solution()
                    result = self.method(instance, *case)
                    elapsed = time.perf_counter() - start_time
                else:
                    raise ValueError(f"Invalid test case format: {type(case)}")
                results[key] = result
                if logger:
                    logger.info(f"<<< OUTPUT (elapsed: {elapsed:.6f}s)\n{json.dumps(result, indent=2, ensure_ascii=False, default=str)}")
            except Exception as e:
                results[key] = e
                if logger:
                    logger.exception("\n!!! EXCEPTION OCCURRED:")
            finally:
                if logger:
                    # 移除并关闭所有的 handler
                    while logger.handlers:
                        handler = logger.handlers[0]
                        handler.close()
                        logger.removeHandler(handler)
        return results
        
    def get_ask_for_cases(self, ask_file=None):
        """生成用于生成适用于暴力算法的测试用例的token，输出到ask_file中"""
        if ask_file is None:
            # 使用与solution_file同名的txt文件
            base_name = os.path.splitext(os.path.basename(self.solution_file))[0]
            ask_file = f"{base_name}.txt"
        
        # 生成唯一token
        token = f"BRUTE_TOKEN_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(ask_file)), exist_ok=True)
        
        # 获取方法签名和参数信息
        temp_instance = self.Solution()
        bound_method = getattr(temp_instance, self.method_name)
        sig = inspect.signature(bound_method)
        param_names = list(sig.parameters.keys())[1:]  # 排除self参数
        
        # 尝试读取原始solution文件内容用于展示
        try:
            with open(self.solution_file, 'rb') as f:
                raw = f.read()
                result = from_bytes(raw).best()
                brute_code = str(result) if result else raw.decode('utf-8', errors='ignore')
                # 👇 关键修复：清理首尾空白，避免 f-string 中产生多余空行
                brute_code = re.sub(r'[\n\s*]+\n', '\n', brute_code.strip())
        except:
            brute_code = "# 无法读取原始文件内容"
        
        # 构建参数描述
        if param_names:
            param_descriptions = []
            for name in param_names:
                param = sig.parameters[name]
                if param.annotation != inspect.Parameter.empty:
                    if hasattr(param.annotation, 'name'):
                        annotation_str = param.annotation.name
                    else:
                        annotation_str = str(param.annotation)
                    param_descriptions.append(f"{name}: {annotation_str}")
                else:
                    param_descriptions.append(f"{name}: Any")
            parameters_info = ", ".join(param_descriptions)
        else:
            parameters_info = "无参数"
        
        # 按照指定格式生成指引内容
        guidance_content = f"""假设你是算法测试专家。
现在需要生产测试样例以测试代码。
测试用例数据是一个列表List，其中的每个元素代表一次调用测试函数的输入，支持两种输入格式:
- 元组格式: (arg1, arg2, ...) - 适用于参数顺序明确的情况，仅有1个参数时则选用；
- 字典格式: {{"arg1": val1, "arg2": val2}} - 适用于参数名重要或可选参数的情况。
- 注意: 需要在外面再包裹一层List（哪怕只有1次测试）才是最终的测试数据结构。 
你需要写出 cases_generation 函数（不是直接写测试数据！），该函数返回上述格式的测试用例，模板如下：
```python3
def cases_generation(规模参数，随机种子等) -> List[Union[Tuple, Dict]]:
    # 生成测试样例的代码
    ……
    return test_cases
```
被测试的程序如下，需要分析被测函数的参数和返回值类型，以及函数的功能，以及复杂度，以此计算出测试数据的输出。：
```python3
{brute_code}
```"""

        # 将内容写入文件
        with open(ask_file, 'w', encoding='utf-8') as f:
            f.write(guidance_content)
        
        print(f"✅ 已生成测试用例指引，保存到: {ask_file}")
        return token

    def save_cases(self, cases_or_generator, file_path=None, *args, **kwargs):
        """保存测试用例，自动运行暴力算法获取expected结果
        
        参数:
        cases_or_generator: 可以是测试用例列表，也可以是生成测试用例的函数
        file_path: 保存的文件路径，如果为None，则使用与solution_file同名的json文件
        *args, **kwargs: 如果cases_or_generator是函数，这些参数将传递给该函数
        
        返回:
        保存的测试用例列表（包含expected结果）
        """
        # 确定保存路径
        if file_path is None:
            base_name = os.path.splitext(os.path.basename(self.solution_file))[0]
            file_path = f"{base_name}.json"
        
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        # 判断是函数还是测试用例列表
        if callable(cases_or_generator):
            # 是生成函数，调用它获取测试用例
            cases = cases_or_generator(*args, **kwargs)
            print(f"✅ 已通过生成函数创建 {len(cases)} 个测试用例")
        else:
            # 是测试用例列表
            cases = cases_or_generator
            print(f"✅ 已接收 {len(cases)} 个预定义测试用例")
        
        # 确保cases是列表
        if not isinstance(cases, list):
            raise ValueError("测试用例必须是列表类型")
        
        # 获取方法签名，用于验证参数
        temp_instance = self.Solution()
        bound_method = getattr(temp_instance, self.method_name)
        sig = inspect.signature(bound_method)
        
        # 处理每个测试用例，添加expected结果
        processed_cases = []
        failures = 0
        
        for idx, case in enumerate(cases):
            processed_case = {}
            
            if isinstance(case, tuple):
                # 元组格式，转换为字典格式
                param_names = list(sig.parameters.keys())[1:]  # 跳过self参数
                
                if len(case) > len(param_names):
                    print(f"⚠️  警告: 用例 #{idx+1} 参数数量({len(case)})超过方法定义({len(param_names)})")
                    continue
                
                input_dict = {param_names[i]: case[i] for i in range(len(case))}
                processed_case["input"] = input_dict
            elif isinstance(case, dict):
                # 字典格式
                if "input" in case:
                    processed_case = case.copy()
                else:
                    # 假设整个字典是input
                    processed_case["input"] = case
            else:
                print(f"⚠️  警告: 用例 #{idx+1} 格式不支持: {type(case)}，已跳过")
                continue
            
            # 确保有input字段
            if "input" not in processed_case:
                processed_case["input"] = {}
            
            # 运行暴力算法获取expected结果
            try:
                instance = self.Solution()
                if isinstance(processed_case["input"], dict):
                    # 验证参数是否匹配
                    try:
                        sig.bind(**processed_case["input"])
                    except TypeError as e:
                        print(f"⚠️  警告: 用例 #{idx+1} 参数不匹配: {e}，已跳过")
                        continue
                    
                    expected = self.method(instance, **processed_case["input"])
                else:
                    # 单个参数情况
                    expected = self.method(instance, processed_case["input"])
                processed_case["expected"] = expected
                print(f"✅ 用例 #{idx+1} 计算成功")
            except Exception as e:
                failures += 1
                processed_case["error"] = str(e)
                processed_case["traceback"] = traceback.format_exc()
                print(f"❌ 用例 #{idx+1} 计算失败: {str(e)}")
            
            processed_cases.append(processed_case)
        
        # 保存为JSON文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(processed_cases, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n📋 测试用例生成总结:")
        print(f"   总用例数: {len(cases)}")
        print(f"   成功用例: {len(processed_cases) - failures}")
        print(f"   失败用例: {failures}")
        print(f"💾 已保存测试用例到: {file_path}")
        return processed_cases