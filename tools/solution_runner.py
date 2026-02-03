from examples_parser import ?
from typing import List, Any, Union

class SolutionRunner:
    def __init__(self, obj_fun : Union[ClassOBJ,function] ) -> None:
        if obj_fun 是 类的对象：
            成员函数列表 = filter(不是__xx__类型的函数，get成员函数(obj_fun))
            if 1== len(成员函数列表):
                self.obj_fun = 成员函数列表[0]
            else:
                raise ValueError("类中必须且只能有一个非 __xx__ 类型的成员函数")
        elif obj_fun 是 函数：
            self.obj_fun = obj_fun
        else:
            raise TypeError

    def read_test_case(path_list: Pathlike or List[Pathlike], file_name_pattern = None: Union[str,None]) -> Dict[Union[Dict,Tuple]]:
        # 读取测试用例文件并解析
        # file_name_pattern 常用于筛选对应的测试用例文件，如 P1234.* ，可以筛选 P1234_case1.txt, P1234_case2.txt
        # file_name_pattern 为None 则不筛选

        # 当 path_list （或者 path_list 中的元素）为文件夹时，则按 file_name_pattern 搜索符合的文件
        # 当 path_list  （或者 path_list 中的元素）为文件时，则按 file_name_pattern 进行筛选

        res = dict()
        for path in 筛选后的相对工作目录的路径文件列表:
            初始解析 = 解析器(path) # Union[Dict,Tuple]
            检查 初始解析 与self.obj_fun 的参数是否匹配
            
            if 匹配:
               res[path] = 初始解析
            else:
                如果不匹配，抛出异常（以后实现自动转换，如 List 转 ListNode，但目前不考虑）

        return res

    def run(self, test_cases :  Dict[Union[Dict,Tuple]]) -> None:
        # 分析 self.obj_fun 的参数个数及类型
        
        for 相对路径path, case in test_cases.items():
            if case 是 dict:
                返回值.add 调用(self.obj_fun(**case) , 日志= f"{相对路径}.log")
            elif case 是 tuple:
                返回值.add 调用(self.obj_fun(*case) ,日志= f"{相对路径}.log")
        return 执行的返回值