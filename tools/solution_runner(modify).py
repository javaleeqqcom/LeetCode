# tools/solution_runner.py
...
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
    status_list,                # Manager.list 代理，主进程用于监控
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

    # ✅ 新增：当前正在执行的用例信息（本地变量，信号处理器安全访问）
    current_case_info = None

    # ✅ 信号处理器：使用本地变量，避免接触 Manager 代理
    def sigterm_handler(signum, frame):
        nonlocal current_case_info   # 声明引用外部变量
        if current_case_info:
            cid = current_case_info.get('cid', '?')
            # 构造 TLE 结果
            result = current_case_info.copy()
            result.update({
                'error': 'Time Limit Exceeded (TLE)',
                'traceback': 'Process terminated due to timeout',
            })
            log_lines = [
                f"Worker {worker_id} terminated due to TLE",
                f"CID: {cid}",
                f">>> INPUT\n{_compacted_json.dumps(current_case_info.get('input'), indent=2)}",
            ]
            # 写入日志文件（_log_result 为模块顶层函数，安全）
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
                assert isinstance(qval, _IN_QELE), f"Queue value must be {_IN_QELE}"
            except Empty:
                if _GLOBAL_GROUP_QUEUE.empty():
                    break
                time.sleep(0.001)
                continue

            results_buff = []
            wrong_count = 0
            cases = _GLOBAL_CASES[qval.start:qval.end]

            for case in cases:
                # ✅ 先保存当前用例到本地变量（信号处理器安全）
                current_case_info = case
                # 再更新共享状态（主进程监控用，可能因代理锁阻塞但不影响信号处理器）
                status_list[worker_id] = (case['cid'], time.time())

                result, log_lines = _execute_dict_case(caller, instance_or_function, case)

                if 'error' in result:
                    error_log_path = _log_result(result, log_lines, "ERROR_", log_path)
                    if skip_error:
                        print(f"\n跳过报错用例（日志: {error_log_path}）")
                        wrong_count += 1
                    else:
                        # 发生错误时，保留当前状态供主进程查看
                        status_list[worker_id] = (case['cid'], time.time(), "ERROR")
                        early_stop_event.set()
                        raise Exception(f"执行报错（日志: {error_log_path}）：\n{result['error']}")
                elif _is_wrong(result):
                    if log_wrong:
                        _log_result(result, log_lines, "Wrong_", log_path)
                    wrong_count += 1

                results_buff.append(result)

            # 完成一组后清除当前用例信息（可选）
            current_case_info = None
            status_list[worker_id] = None

            _GLOBAL_OUTPUT_QUEUE.put(_OUT_QELE(qval.group_id, wrong_count, results_buff))
            process_case_num += len(results_buff)
            if __DEBUG__:
                print(f"\n解释器 {worker_id}: 完成组 {qval.group_id} ({len(results_buff)} 个用例)", end="")

    except Exception as e:
        early_stop_event.set()
        raise Exception(f"\n解释器 {worker_id}: 顶层异常 {type(e).__name__}: {e}")
    finally:
        current_case_info = None
        status_list[worker_id] = None

    end_time = time.time()
    if __DEBUG__:
        print(f"解释器 {worker_id}: 处理 {process_case_num} 个用例耗时：{end_time - start_time:.3f}s")
    return (worker_id, process_case_num, end_time - start_time)

class SolutionRunner:
    ...
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
            ...
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
                                status_list[wid] = None # 避免重复触发
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
    ...