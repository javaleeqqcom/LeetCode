# tools/solution_runner.py
import os
import inspect
from pathlib import Path
import logging
import json
from typing import Any, Callable, Dict, List, Tuple, Union, Optional
try:
    from examples_parser import parse_test_cases
except:
    from tools.examples_parser import parse_test_cases


def _sanitize_filename(name: str) -> str:
    """将字符串转换为安全的文件名（替换非法字符）"""
    # 替换常见非法字符（Windows/Linux/macOS）
    for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        name = name.replace(ch, '_')
    return name.strip().rstrip('.')


def _get_case_logger(key: str) -> logging.Logger:
    """为给定 key 返回一个专用的 logger，日志写入 {key}.log"""
    logger_name = f"case_logger_{key}"
    logger = logging.getLogger(logger_name)

    # 防止重复添加 handler（避免日志重复）
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        logger.propagate = False  # 不向 root logger 传播

        # 创建文件 handler
        safe_key = _sanitize_filename(key)
        log_file = f"{safe_key}.log"
        fh = logging.FileHandler(log_file, mode='w', encoding='utf-8')

        # 自定义格式：仅时间戳（毫秒精度）
        formatter = logging.Formatter(fmt='%(asctime)s', datefmt='%H:%M:%S.%f')
        # 截断微秒到毫秒（%f 是6位，我们取前3位）
        old_format = formatter.formatTime
        def format_time_with_millis(record, datefmt=None):
            ct = old_format(record, datefmt)
            # ct 格式如 '14:30:45.123456' -> 截为 '14:30:45.123'
            if '.' in ct:
                main, micro = ct.rsplit('.', 1)
                ct = f"{main}.{micro[:3]}"
            return ct
        formatter.formatTime = format_time_with_millis

        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


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
        path_list: Union[str, Path, List[Union[str, Path]]],
        file_name_pattern: Optional[str] = None
    ) -> Dict[str, Union[Dict, Tuple]]:
        """
        读取并解析测试用例文件。
        :param path_list: 文件或文件夹路径（或路径列表）
        :param file_name_pattern: 用于 glob 匹配的模式，如 "P1234.*"
        :return: {相对路径: 解析后的测试用例}
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

        # 获取工作目录用于生成相对路径
        cwd = Path.cwd()
        test_cases_dict = {}

        sig = inspect.signature(self.obj_fun)

        for file_path in all_files:
            try:
                parsed_list = parse_test_cases(str(file_path))
            except Exception as e:
                raise RuntimeError(f"解析测试文件失败: {file_path}") from e

            for i, case in enumerate(parsed_list):
                # 构造唯一 key：文件名 + 行号（避免同文件多用例冲突）
                rel_path = str(file_path.relative_to(cwd)) if cwd in file_path.parents else str(file_path)
                key = f"{rel_path}#{i+1}"

                # 检查参数匹配
                if isinstance(case, dict):
                    input_args = case.get('input', {})
                    try:
                        sig.bind(**input_args)
                    except TypeError as e:
                        raise TypeError(f"测试用例参数与函数签名不匹配 ({key}): {e}")
                elif isinstance(case, tuple):
                    try:
                        sig.bind(*case)
                    except TypeError as e:
                        raise TypeError(f"测试用例参数与函数签名不匹配 ({key}): {e}")
                else:
                    raise ValueError(f"未知的测试用例格式: {type(case)}")

                test_cases_dict[key] = case

        return test_cases_dict

    def run(self, test_cases: Dict[str, Union[Dict, Tuple]], auto_log: bool = True) -> Dict[str, Any]:
        """
        执行所有测试用例。
        :param test_cases: 由 read_test_case 返回的字典
        :param auto_log: 是否自动记录每个用例的输入/输出到 .log 文件
        :return: {测试用例 key: 函数返回值}
        """
        results = {}
        for key, case in test_cases.items():
            logger = None
            if auto_log:
                logger = _get_case_logger(key)

            try:
                if isinstance(case, dict):
                    input_args = case.get('input', {})
                    if logger:
                        pretty_input = json.dumps(input_args, indent=2, ensure_ascii=False, default=str)
                        logger.info(f"\n{pretty_input}")

                    result = self.obj_fun(**input_args)

                    if logger:
                        pretty_result = json.dumps(result, indent=2, ensure_ascii=False, default=str)
                        logger.info(f"\n{pretty_result}")

                elif isinstance(case, tuple):
                    if logger:
                        pretty_input = json.dumps(list(case), indent=2, ensure_ascii=False, default=str)
                        logger.info(f"\n{pretty_input}")

                    result = self.obj_fun(*case)

                    if logger:
                        pretty_result = json.dumps(result, indent=2, ensure_ascii=False, default=str)
                        logger.info(f"\n{pretty_result}")

                else:
                    raise ValueError(f"无效的测试用例格式: {type(case)}")

                results[key] = result

            except Exception as e:
                results[key] = e
                if logger:
                    logger.exception("\n执行时发生异常:")  # 会记录 traceback
                # 或者只记录错误信息：
                # logger.error(f"\nException: {str(e)}")

        return results