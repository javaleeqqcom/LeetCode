假设你是一位交编程的老师，需要学生在 leetcode 平台上练习 Python 编程。
为了方便排除错误和调试，你需要编写一套自动读取测试样例并进行测试的程序，只做 Python 语言的编程。
附件所示是一套程序，但是该程序有问题，当采用自定义类时，生成测试数据的程序与执行测试的Solution 用的类是同名但不同内存地址：
```
(base) PS D:\Users\java_lee\Documents\GitHub\LeetCode\test> python .\run_solution.py .\82_V0.py .\82q1.txt
Traceback (most recent call last):
  File "D:\Users\java_lee\Documents\GitHub\LeetCode\test\run_solution.py", line 259, in <module>
    main()
  File "D:\Users\java_lee\Documents\GitHub\LeetCode\test\run_solution.py", line 240, in main
    printed, result = capture_print_and_result(func, obj, **converted_args)
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\Users\java_lee\Documents\GitHub\LeetCode\test\run_solution.py", line 144, in capture_print_and_result
    result = func(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^
  File ".\82_V0.py", line 12, in deleteDuplicates
    assert isinstance(pred,ListNode)
           ^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError
```
如上执行所示。
现在需要改造该工程，放弃采用命令行调用的想法，而是采用 import 模块的方式进行测试。
- tools/test_examples_parser.py ：提供将 txt 中的测试样例数据智能转换为元组列表的功能。（学生不可修改，调试完毕后设为只读）
- tools/base_init.py ：模仿 leetcode 中给代码自动添加的库文件。（学生一般不需要修改）
- tools/custom_init.py ：模仿 leetcode 中特定题目的自定义类，如链表、树等，并提前写好 __repr__ 方法，以便在调试时打印出对象信息。
- Q123_V1.py （示例名称）：学生答题的代码（可以拷贝到 leecode 的测试框架中运行，无需修改）
- Q123_Brute.py （示例名称）：（可选）学生暴力破解的代码
- Q123_case.txt（示例名称）：学生答题的测试样例数据文件，不过类名需要改为 Brute 类，以免与 Solution 类冲突。
- run_solution.py : 用于执行学生答题的代码，并调用 test_examples_parser.py 自动读取如 Q123_case.txt 的测试样例数据文件，进行测试。若测试样例数据文件包含正确结果，则会自动比较输出与预期结果并给出。若学生写了暴力代码，可以输入暴力代码文件名，自动比较被测代码是否正确。

现在先请根据附件中的代码进行简化，得到 test_examples_parser.py，并写一个 tools/parser_test.py 对其进行测试。其余代码都基于此，故暂时不写，等测试成功后再补充。