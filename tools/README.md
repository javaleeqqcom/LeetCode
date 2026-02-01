假设你是一位教编程的老师，需要学生在 leetcode 平台上练习 Python 编程。
为了方便排除错误和调试，你需要编写一套自动读取测试样例并进行测试的程序，只做 Python 语言的编程。
现在需要改造该工程，放弃采用命令行调用的想法，而是采用 import 模块的方式进行测试。
- tools/examples_parser.py ：提供将 txt 中的测试样例数据智能转换为Python对象的功能。（学生不可修改，调试完毕后设为只读）
- tools/base_init.py ：模仿 leetcode 中给代码自动添加的库文件。（学生一般不需要修改）
- tools/custom_init.py ：模仿 leetcode 中特定题目的自定义类，如链表、树等，并提前写好 __repr__ 方法，以便在调试时打印出对象信息。
- Q123_V1.py （示例名称）：学生答题的代码（可以拷贝到 leecode 的测试框架中运行，无需修改，注意学生代码不 import custom_init.py 等，因为这些复制到 leetcode 肯定会报错（无此文件报错））
- Q123_Brute.py （示例名称）：（可选）学生暴力破解的代码
- Q123_case.txt（示例名称）：学生答题的测试样例数据文件，不过类名需要改为 Brute 类，以免与 Solution 类冲突。
- run_solution.py : 用于执行学生答题的代码，并调用 test_examples_parser.py 自动读取如 Q123_case.txt 的测试样例数据文件，进行测试。若测试样例数据文件包含正确结果，则会自动比较输出与预期结果并给出。若学生写了暴力代码，可以输入暴力代码文件名，自动比较被测代码是否正确。

目前需要先测试 examples_parser.py 程序是否完全符合要求，通过 parser_test.py 进行测试。
目前问题：
```
人工判断 原始转txt 和 examples_parser.py 转换的对象转json 是一致的，为何 parser_test.py 认为不一致？