# tools/solution_runner.py
import os
import inspect
from pathlib import Path
import logging
import json
import datetime,time
import inspect
from typing import Any, Callable, Dict, List, Tuple, Union, Optional, get_type_hints
try:
    from examples_parser import parse_test_cases
    from custom_init import input_parser_registry
except:
    from tools.examples_parser import parse_test_cases
    from tools.custom_init import input_parser_registry

def _convert_case_by_signature( case: Union[Dict, Tuple], sig: inspect.Signature) -> Union[Dict, Tuple]:
    """
    对单个测试用例（dict 或 tuple）执行类型转换。
    - dict：按键（参数名）匹配
    - tuple：按位置匹配参数顺序
    所有参数均尝试转换（registry 无匹配则直通原值）。
    """

    # 获取参数名列表（按顺序）
    param_names = list(sig.parameters.keys())
    type_hints = {}
    try:
        type_hints = get_type_hints(sig, globalns={}, localns={})
    except Exception:
        pass  # 忽略无法解析的类型注解

    if isinstance(case, dict):
        input_dict = case.get('input', {})
        converted = {}
        for name in param_names:
            if name not in input_dict:
                continue  # 跳过缺失参数（由 bind 检查合法性）
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
        # 补齐未提供但有默认值的参数？——不需要，tuple 应提供完整前缀
        return tuple(converted_values)

    else:
        raise ValueError(f"不支持的用例类型: {type(case)}")


def _sanitize_filename(name: str) -> str:
    """将字符串转换为安全的文件名（替换非法字符）"""
    for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        name = name.replace(ch, '_')
    return name.strip().rstrip('.')

def _get_unique_log_path(base_name: str) -> str:
    """生成不重复的日志路径，如 base.log, base.1.log, base.2.log..."""
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
    raise Exception("尝试次数过多，无法生成不重复的日志路径，请清理文件夹。")

class SolutionRunner:
    def __init__(self, obj_fun: Union[Callable, object]) -> None:
        """
        初始化 SolutionRunner。
        :param obj_fun: 可以是函数，也可以是一个类的实例（该类必须有且仅有一个非魔术方法）
        """
        if inspect.isfunction(obj_fun):
            self.obj_fun = obj_fun
        elif inspect.isclass(obj_fun):
            # 如果传入的是类（而非实例），自动实例化
            obj_fun = obj_fun()
            self._bind_method_from_instance(obj_fun)
        elif hasattr(obj_fun, '__class__'):
            # 传入的是类的实例
            self._bind_method_from_instance(obj_fun)
        else:
            raise TypeError("obj_fun 必须是函数、类或类的实例")

    def _bind_method_from_instance(self, instance: object) -> None:
        """从实例中提取唯一有效的成员方法"""
        methods = []
        for name, method in inspect.getmembers(instance, predicate=inspect.ismethod):
            if not (name.startswith('__') and name.endswith('__')):
                methods.append(method)
        if len(methods) != 1:
            raise ValueError(f"类实例必须有且仅有一个非魔术方法，当前找到 {len(methods)} 个: {[m.__name__ for m in methods]}")
        self.obj_fun = methods[0]

    def read_test_case(
        self,
        path_list: Union[str, os.PathLike, List[Union[str, Path]]],
        file_name_pattern: Optional[str] = None
    ) -> Dict[str, Union[Dict, Tuple]]:
        """
        读取并解析测试用例文件，在此阶段完成所有类型转换。
        """
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
        test_cases_dict = {}
        sig = inspect.signature(self.obj_fun)

        for file_path in all_files:
            try:
                parsed_list = parse_test_cases(str(file_path))
            except Exception as e:
                raise RuntimeError(f"解析测试文件失败: {file_path}") from e

            for i, raw_case in enumerate(parsed_list):
                rel_path = str(file_path.relative_to(cwd)) if cwd in file_path.parents else str(file_path)
                key = f"{rel_path}#{i+1}"

                # === 核心修改：在此处执行转换 ===
                converted_case = _convert_case_by_signature(raw_case, sig)

                # 验证绑定（使用转换后的值）
                if isinstance(converted_case, dict):
                    try:
                        sig.bind(**converted_case.get('input', {}))
                    except TypeError as e:
                        raise TypeError(f"测试用例参数与函数签名不匹配 ({key}): {e}")
                else:  # tuple
                    try:
                        sig.bind(*converted_case)
                    except TypeError as e:
                        raise TypeError(f"测试用例参数与函数签名不匹配 ({key}): {e}")

                test_cases_dict[key] = converted_case

        return test_cases_dict
    
    def run(
        self,
        test_cases: Dict[str, Union[Dict, Tuple]],
        log_suffix: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行所有测试用例，并可选记录日志。
        :param test_cases: 测试用例字典
        :param log_suffix: 日志文件名后缀（如 "_debug"），若为 None 则不记录日志
        :return: {key: result 或 exception}
        """
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

                def format_time_with_microseconds(record, datefmt=None):
                    # 仅输出 HH:MM:SS，微秒已通过 msecs 提供
                    return time.strftime("%H:%M:%S", time.localtime(record.created))

                formatter.formatTime = format_time_with_microseconds
                fh.setFormatter(formatter)
                logger.addHandler(fh)

                # 首条日志：记录完整日期、函数名、日志路径
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                func_name = getattr(self.obj_fun, '__name__', 'unknown_function')
                logger.info(f"[{today}] Running function '{func_name}' with test case key: {key}")
                logger.info(f"Log file: {log_file}")

            try:
                if isinstance(case, dict):
                    input_args = case.get('input', {})
                    if logger:
                        pretty_input = json.dumps(input_args, indent=2, ensure_ascii=False, default=str)
                        logger.info(f">>> INPUT\n{pretty_input}")

                    start_time = time.perf_counter()
                    result = self.obj_fun(**input_args)
                    elapsed = time.perf_counter() - start_time

                elif isinstance(case, tuple):
                    if logger:
                        pretty_input = json.dumps(list(case), indent=2, ensure_ascii=False, default=str)
                        logger.info(f">>> INPUT\n{pretty_input}")

                    start_time = time.perf_counter()
                    result = self.obj_fun(*case)
                    elapsed = time.perf_counter() - start_time

                else:
                    raise ValueError(f"Invalid test case format: {type(case)}")

                results[key] = result

                if logger:
                    pretty_result = json.dumps(result, indent=2, ensure_ascii=False, default=str)
                    logger.info(f"<<< OUTPUT (elapsed: {elapsed:.6f}s)\n{pretty_result}")

            except Exception as e:
                results[key] = e
                if logger:
                    logger.exception("\n!!! EXCEPTION OCCURRED:")

            finally:
                if logger:
                    # 安全关闭 handler
                    for handler in logger.handlers[:]:
                        handler.close()
                        logger.removeHandler(handler)

        return results