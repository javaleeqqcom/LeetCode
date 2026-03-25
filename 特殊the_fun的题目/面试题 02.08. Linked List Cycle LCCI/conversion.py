
from tools.args_parser import ListNode,List2ListNode,index_ListNode,ListNode2List,ListNode_flatten
def custom_caller(bind_func: Callable, args:_ARGS)->_BASE_TYPE:
    # 将测试用例 (head_list, pos) 转换为 Solution.detectCycle 所需的参数。
    # bind_func 返回的节点需要转化为位置值，-1 表示无环。
    head_list, pos = args
    assert isinstance(head_list, list)
    assert isinstance(pos,int) and -1<=pos<len(head_list)

    print("调用了 custom_caller !!!")

    # 空链表
    if not head_list:
        return -1

    # 构造所有节点并排列为list（尽量利用 args_parser.py 已有函数简化设计）
    nodes = ListNode_flatten(List2ListNode(head_list),len(head_list))

    # 根据 pos 设置环
    if pos != -1: # 有环
        nodes[-1].next = nodes[pos]

    # 调用学生提交的函数
    circle = bind_func(nodes[0])

    # 检查学生是否改变链表结构
    assert ListNode_flatten(nodes[0],len(head_list)) == nodes

    # 计算环的相对位置
    if circle is None:
        return -1
    else:
        for res,cur in enumerate(nodes):
            if cur == circle:
                return res
        raise ValueError(f"{bind_func.__name__}返回值非法!")
