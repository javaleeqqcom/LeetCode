
from tools.args_parser import ListNode,ListNodeKit,List2ListNode,ListNode2List
def custom_caller(bind_func: Callable, args:_ARGS)->_BASE_TYPE:
    # 将测试用例 (head_list, pos) 转换为 Solution.detectCycle 所需的参数。
    # bind_func 返回的节点需要转化为位置值，-1 表示无环。
    head_list, pos = args
    assert isinstance(head_list, list), "args[0] 必须是 list"
    assert isinstance(pos,int) and -1<=pos<len(head_list), "args[1] 必须是 int，且在有效范围内"

    print("调用了 custom_caller !!!")
    # 特殊测试
    assert ListNodeKit(None)._node is None , "ListNodeKit(None)._node is None"
    assert False == bool(ListNodeKit(None)), "False == bool(ListNodeKit(None))"

    # 空链表
    if not head_list:
        return -1

    # 构造所有节点并排列为list（尽量利用 args_parser.py 已有函数简化设计）
    nodes,_ = ListNodeKit(List2ListNode(head_list)).flatten()

    # 根据 pos 设置环
    if pos != -1: # 有环
        nodes[-1].next = nodes[pos]

    # 调用学生提交的函数
    circle = bind_func(nodes[0])

    # 检查学生是否改变链表结构
    after = ListNodeKit(nodes[0]).flatten()
    # after = ListNodeKit.flatten(nodes[0])  # 也可以重载为类方法

    assert after[0] == nodes and after[1] == pos, "学生代码篡改了链表结构"

    # 计算环的相对位置
    if circle is None:
        return -1
    else:
        for res,cur in enumerate(nodes):
            if cur == circle:
                return res
        raise ValueError(f"{bind_func.__name__}返回值非法!")
