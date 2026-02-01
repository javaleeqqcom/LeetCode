假设你是一位教编程的老师，需要学生在 leetcode 平台上练习 Python 编程。
为了方便排除错误和调试，你需要编写一套自动读取测试样例并进行测试的程序，只做 Python 语言的编程。
现在需要改造该工程，放弃采用命令行调用的想法，而是采用 import 模块的方式进行测试。
- tools/examples_parser.py ：提供将 txt 中的测试样例数据智能转换为Python对象的功能。（学生不可修改，调试完毕后设为只读）
- tools/base_init.py ：模仿 leetcode 中给代码自动添加的库文件。（学生一般不需要修改）
- tools/custom_init.py ：模仿 leetcode 中特定题目的自定义类，如链表、树等，并提前写好 __repr__ 方法，以便在调试时打印出对象信息。
- Q123_V1.py （示例名称）：学生答题的代码（可以拷贝到 leecode 的测试框架中运行，无需修改，注意学生代码不 import custom_init.py 等，因为这些复制到 leetcode 肯定会报错（无此文件报错））
- Q123_Brute.py （示例名称）：（可选）学生暴力破解的代码
- Q123_case.txt（示例名称）：学生答题的测试样例数据文件，不过类名需要改为 Brute 类，以免与 Solution 类冲突。
- run_solution.py : 用于执行学生答题的代码，并调用 examples_parser.py 自动读取如 Q123_case.txt 的测试样例数据文件，进行测试。若测试样例数据文件包含正确结果，则会自动比较输出与预期结果并给出。若学生写了暴力代码，可以输入暴力代码文件名，自动比较被测代码是否正确。

现在成功比较 parser_test.py，下一步实现 null 转化为 None 的识别，因为 leetcode 中不只是 python 语言，所以其数组空指针用 null 表示。
修改方案：
1. 在测试中增加空指针的情况，并且要将 python 格式的 None 替换为 null （注意不是字符串）
2. 在 examples_parser.py 分割行后，先将非字符串的所有 null 替换为 None，以便 ast 解析时正确识别。