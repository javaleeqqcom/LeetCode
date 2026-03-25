
from tools.args_parser import ListNode,List2ListNode,index_ListNode
def custom_caller(bind_func: Callable, args:_ARGS)->_BASE_TYPE:

    """
    将测试用例 (head_list, pos) 转换为 Solution.detectCycle 所需的参数。
    返回 (args, kwargs)，其中 args 是 (head_node,) 。
    """
    head_list, pos = args
    assert isinstance(head_list, list)
    assert isinstance(pos,int) and -1<=pos<len(head_list)

    print("调用了 custom_caller !!!")

    # 空链表
    if not head_list:
        return -1

    # 构造所有节点
    nodes = List2ListNode(head_list)

    # 根据 pos 设置环
    if pos != -1: # 有环
        index_ListNode(nodes,pos).next = nodes

    return bind_func(nodes)