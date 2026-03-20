def exchange_fun(input_case):
    """
    将测试用例 (head_list, pos) 转换为 Solution.detectCycle 所需的参数。
    返回 (args, kwargs)，其中 args 是 (head_node,) 。
    """
    head_list, pos = input_case

    # 空链表
    if not head_list:
        return (None,), {}

    # 构造所有节点
    nodes = [ListNode(val) for val in head_list]

    # 连接 next 指针
    for i in range(len(nodes) - 1):
        nodes[i].next = nodes[i + 1]

    # 根据 pos 设置环
    if pos != -1 and 0 <= pos < len(nodes):
        nodes[-1].next = nodes[pos]
    else:
        nodes[-1].next = None

    return (nodes[0],), {}