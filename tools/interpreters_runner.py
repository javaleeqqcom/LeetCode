def _execute_in_interpreter_worker(
    interpreter_id: int,
    student_code: str,
    method_name: str,
    group_queue_id: int,
    output_queue_id: int,
    tools_dir: str,
    custom_init_code: str,  # ← 新增：将导入代码作为字符串传递
) -> tuple:
    """
    模块级 worker 函数，在子解释器中执行测试用例
    所有参数必须是可共享的基本类型（字符串、整数）
    """
    print(f"线程{interpreter_id}：开始")

    # ========== 所有导入在子解释器内部完成 ==========
    import time
    import sys
    import io
    import types
    import traceback
    from pathlib import Path
    from concurrent import interpreters
    
    # 设置 sys.path
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    print(f"线程{interpreter_id}: sys.path 已设置")
    
    # 通过 ID 重建队列
    group_queue = interpreters.Queue(group_queue_id)
    output_queue = interpreters.Queue(output_queue_id)
    print(f"线程{interpreter_id}: 队列重建成功")

    # ========== 在子解释器中执行导入代码 ==========
    # 将 custom_init_code 作为字符串在子解释器中 exec
    custom_mod = types.ModuleType('custom_init')
    exec(custom_init_code, custom_mod.__dict__)
    
    # 从 custom_mod 中获取类型
    ListNode = custom_mod.__dict__.get('ListNode')
    TreeNode = custom_mod.__dict__.get('TreeNode')
    Optional = custom_mod.__dict__.get('Optional')
    List = custom_mod.__dict__.get('List')
    Dict = custom_mod.__dict__.get('Dict')
    
    print(f"线程{interpreter_id}：成功获取自定义类型")

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
            
            output_queue.put((group_id, results_buff))
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