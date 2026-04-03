# test_listnode_kit.py
import random
from args_parser import ListNode, ListNodeKit , List2ListNode
from args_parser_tools import ListNodeKitBase,KitBase
__MIX_TEST__ = False

def test_listnode_kit():
    """测试 ListNodeKit 的所有功能（基础 + 随机压力）"""
    
    # ---------- 1. 空链表 ----------
    empty = ListNodeKit(None)
    print("1. 空链表测试")
    print(f"   bool(empty): {bool(empty)}")          # False
    print(f"   str(empty): {str(empty)}")            # <ListNodeKit>:[] 
    try:
        _ = empty.next
    except AttributeError as e:
        print(f"   访问 empty.next 抛出 AttributeError: {e}")
    try:
        _ = empty[0]
    except IndexError as e:
        print(f"   访问 empty[0] 抛出 IndexError: {e}")
    
    # ---------- 2. 无环链表 ----------
    print("\n2. 无环链表测试")
    n1 = ListNode(1)
    n2 = ListNode(2)
    n3 = ListNode(3)
    n1.next = n2
    n2.next = n3
    kit = ListNodeKit(n1)
    
    # 2.1 基本属性
    print(f"   str(kit): {str(kit)}")                # <ListNodeKit>:[1,2,3]
    print(f"   kit.val: {kit.val}")                  # 1
    print(f"   kit.next.val: {kit.next.val}")        # 2
    print(f"   kit.next.next.val: {kit.next.next.val}")  # 3
    
    # 2.2 node 属性（原生节点）
    print(f"   kit.node is n1: {kit._node is n1}")    # True
    
    # 2.3 索引访问
    print(f"   kit[0].val: {kit[0].val}")            # 1
    print(f"   kit[1].val: {kit[1].val}")            # 2
    print(f"   kit[2].val: {kit[2].val}")            # 3
    last = kit[3]
    print(f"   kit[3] 的类型: {type(last)}, bool(last): {bool(last)}")  # ListNodeKit, False
    try:
        _ = kit[4]
    except IndexError as e:
        print(f"   kit[4] 抛出 IndexError: {e}")
    
    # 2.4 flatten
    nodes, cycle_idx = kit.flatten()
    print(f"   flatten() 返回节点数: {len(nodes)}, 环索引: {cycle_idx}")
    assert cycle_idx is None
    
    # 2.5 通过 __bool__ 判断非空
    print(f"   bool(kit): {bool(kit)}")              # True
    print(f"   bool(kit.next.next): {bool(kit.next.next)}")   # True
    print(f"   bool(kit.next.next.next): {bool(kit.next.next.next)}")  # False
    
    # 2.6 长链表截断打印测试
    long_link = ListNodeKit(List2ListNode(list(range(1,101))))
    print(long_link.to_str(max_len=99))

    # ---------- 3. 带环链表（使用示例中的构造方式）----------
    print("\n3. 带环链表测试")
    ring_link = ListNodeKit(val=1)
    b = ListNode(2)
    c = ListNode(3)
    d = ListNode(4)
    ring_link.next = b
    b.next = c
    c.next = d
    d.next = b                       # 环起点为 b (val=2)
    
    print(f"   str(ring_link): {str(ring_link)}")    # 预期: [1,>,2,3,4,^]
    nodes, cycle_idx = ring_link.flatten()
    print(f"   flatten() 节点数: {len(nodes)}, 环起始索引: {cycle_idx}")
    assert cycle_idx == 1
    print(f"   环起始节点值: {nodes[cycle_idx].val}")  # 2
    
    print(f"   ring_link[0].val: {ring_link[0].val}")  # 1
    print(f"   ring_link[1].val: {ring_link[1].val}")  # 2
    
    # ---------- 4. 使用 val 参数构造 ----------
    print("\n4. 使用 val 参数构造")
    kit_by_val = ListNodeKit(val=5)
    print(f"   str(kit_by_val): {str(kit_by_val)}")  # <ListNodeKit>:[5]
    print(f"   kit_by_val.node.val: {kit_by_val._node.val}")  # 5
    
    
    print("\n所有测试完成！")

def generate_random_list(node_count: int, create_cycle: bool = False):
    """
    生成随机单链表（无环或有环）。
    返回 (head_node, expected_cycle_start_node)，
    若无环则 expected_cycle_start_node 为 None。
    """
    if node_count <= 0:
        return None, None
    
    nodes = [ListNode(random.randint(0, 999)) for _ in range(node_count)]
    # 连接成链
    for i in range(node_count - 1):
        nodes[i].next = nodes[i+1]
    
    if not create_cycle:
        return nodes[0], None
    
    # 随机选择环的起点（可以是头节点，但不能是尾节点，因为尾节点的 next 指向其他节点才成环）
    # 环起点必须存在于节点列表中，且它的 next 指向某个之前的节点（包括自身）
    cycle_start_idx = random.randint(0, node_count - 1)
    # 随机选择环指向的目标索引（必须 <= cycle_start_idx，且不能是尾节点自身无环的情况）
    # 如果 cycle_start_idx == node_count-1，则目标可以是任何节点（包括自身），形成自环
    if cycle_start_idx == node_count - 1:
        target_idx = random.randint(0, node_count - 1)
    else:
        target_idx = random.randint(0, cycle_start_idx)
    
    # 让 cycle_start 节点的 next 指向 target 节点
    nodes[cycle_start_idx].next = nodes[target_idx]
    return nodes[0], nodes[target_idx]

def validate_list_flatten(head, expected_cycle_start_node):
    """验证 flatten 结果是否符合预期"""
    kit = ListNodeKit(head)
    nodes, cycle_idx = kit.flatten()
    
    if expected_cycle_start_node is None:
        # 期望无环
        assert cycle_idx is None, f"期望无环，但检测到环起始索引 {cycle_idx}"
        # 检查节点数是否正确（无环时节点数应等于原始节点数）
        # 注意：原始节点数需要从 head 遍历计算，但由于链表可能很长，我们可以在生成时记录 node_count
        # 这里简化：不检查节点数，因为生成函数已保证无重复节点
    else:
        # 期望有环
        assert cycle_idx is not None, "期望有环，但 flatten 返回 None"
        assert 0 <= cycle_idx < len(nodes), f"环起始索引 {cycle_idx} 越界"
        start_node = nodes[cycle_idx]
        assert start_node is expected_cycle_start_node, \
            f"环起始节点 {start_node.val} 不符合预期 {expected_cycle_start_node.val}"

def test_random_lists():
    """随机生成大量链表（包括有环和无环），验证 flatten 的正确性"""
    test_rounds = 1000
    max_nodes = 200
    
    for round_i in range(test_rounds):
        node_count = random.randint(1, max_nodes)
        # 30% 概率生成有环链表
        create_cycle = random.random() < 0.3
        head, cycle_start_node = generate_random_list(node_count, create_cycle)
        validate_list_flatten(head, cycle_start_node)
        
        # 对无环链表额外测试索引访问（随机抽几个索引）
        if not create_cycle:
            kit = ListNodeKit(head)
            # 随机测试索引
            for _ in range(5):
                idx = random.randint(0, node_count - 1)
                node_kit = kit[idx]
                assert node_kit._node is not None
                # 检查索引访问的值是否与直接遍历一致
                cur = head
                for _ in range(idx):
                    cur = cur.next
                assert node_kit._node.val == cur.val
            # 测试超出长度的索引
            try:
                _ = kit[node_count]
                # 应该返回空链表（不是抛出异常），因为 ListNodeKit 的设计是 kit[n] 返回空链表
                assert bool(kit[node_count]) is False
            except IndexError:
                # 根据实现，索引第 n 个节点应返回空链表，不应抛出异常，这里兼容性处理
                pass
            try:
                _ = kit[node_count + 1]
                assert False, "索引越界应该抛出 IndexError"
            except IndexError:
                pass
        
        # 对包含环的链表，测试 flatten 的环索引一致性（已在上方 validate 中完成）
        
        if (round_i + 1) % 200 == 0:
            print(f"   已完成 {round_i + 1}/{test_rounds} 轮随机测试")

def test_duplicate_values_no_cycle():
    """测试值重复但节点不同的情况，不应触发环检测"""
    print("\n6. 重复值（非环）测试")
    # 创建三个节点值相同但对象不同
    a = ListNode(100)
    b = ListNode(100)
    c = ListNode(100)
    a.next = b
    b.next = c
    kit = ListNodeKit(a)
    nodes, cycle_idx = kit.flatten()
    assert cycle_idx is None
    assert len(nodes) == 3
    # 确认节点对象不同
    assert nodes[0] is a
    assert nodes[1] is b
    assert nodes[2] is c
    print("   重复值测试通过")

def test_iter():
    """测试 ListNodeKit 的 __iter__ 方法（安全迭代）"""
    print("\n5.========== 测试 __iter__ 方法 ==========")
    from args_parser import List2ListNode

    # 1. 空链表迭代
    empty = ListNodeKit(None)
    items = list(empty)
    assert items == [], "空链表迭代应返回空列表"
    print("   空链表迭代测试通过")

    # 2. 无环链表迭代
    head = List2ListNode([10, 20, 30])
    kit = ListNodeKit(head)
    collected = [(idx, node.val) for idx, node in kit]
    expected = [(0, 10), (1, 20), (2, 30)]
    assert collected == expected, f"无环链表迭代结果错误: {collected} != {expected}"
    print("   无环链表迭代测试通过")

    # 3. 有环链表迭代（检测重复节点并提前停止）
    # 构造环: 1 -> 2 -> 3 -> 2 (环)
    a = ListNode(1)
    b = ListNode(2)
    c = ListNode(3)
    a.next = b
    b.next = c
    c.next = b  # 环起点为 b (val=2)
    kit_ring = ListNodeKit(a)

    it = iter(kit_ring)          # 获取 SafeIter 实例
    collected = []
    for idx, node in it:
        collected.append((idx, node.val))
    # 迭代应在遇到重复节点 b 时停止，不会输出索引3
    assert collected == [(0, 1), (1, 2), (2, 3)], f"有环链表迭代结果错误: {collected}"
    # 检查 repeat_idx 属性
    assert it.repeat_indices == [1], f"repeat_idx 应为 1，实际为 {it.repeat_indices}"
    print("   有环链表迭代（环检测）测试通过")

    # 4. 重复值但无环链表（不应触发环检测）
    d = ListNode(100)
    e = ListNode(100)
    f = ListNode(100)
    d.next = e
    e.next = f
    kit_dup = ListNodeKit(d)
    collected_dup = [(idx, node.val) for idx, node in kit_dup]
    assert collected_dup == [(0, 100), (1, 100), (2, 100)], "重复值无环链表被错误检测为环"
    print("   重复值无环链表迭代测试通过")

def test_flatten_methods():
    """专门测试 flatten 方法的调用方式和 stop_index 的所有可能值"""
    print("\n6.========== 测试 flatten 方法 ==========")

    # ---------- 准备无环链表 ----------
    # 1 -> 2 -> 3 -> 4 -> 5
    n1 = ListNode(1)
    n2 = ListNode(2)
    n3 = ListNode(3)
    n4 = ListNode(4)
    n5 = ListNode(5)
    n1.next = n2
    n2.next = n3
    n3.next = n4
    n4.next = n5
    head = n1
    kit = ListNodeKit(head)

    # 1.1 实例调用 flatten()，无环正常结束
    nodes, stop = kit.flatten()
    assert stop is None, f"无环链表正常结束应为 None，实际 {stop}"
    assert len(nodes) == 5
    print("✓ 实例调用 flatten() 正常结束，stop=None")

    # 1.2 实例调用 flatten(max_len=3)，提前达到 max_len
    nodes, stop = kit.flatten(max_len=3)
    assert stop == 3, f"max_len=3 应返回 stop=3，实际 {stop}"
    assert len(nodes) == 3
    print("✓ 实例调用 flatten(max_len=3) 提前终止，stop=3")

    # 1.3 实例调用 flatten(max_len=10)，max_len 大于实际长度，正常结束
    nodes, stop = kit.flatten(max_len=10)
    assert stop is None, f"max_len 大于链表长度应正常结束，实际 {stop}"
    assert len(nodes) == 5
    print("✓ 实例调用 flatten(max_len=10) 正常结束，stop=None")

    # ---------- 类调用方式（将 head 作为第一个参数）----------
    # 2.1 类调用 flatten(head)
    print(f"type(head)={type(head)}")
    assert isinstance(head, ListNode)

    
    nodes2, stop2 = ListNodeKit.flatten(head)
    assert stop2 is None
    assert len(nodes2) == 5
    # 节点对象应与原始相同
    assert nodes2[0] is n1 and nodes2[-1] is n5
    print("✓ 类调用 ListNodeKit.flatten(head) 正常结束")

    # 2.2 类调用 flatten(head, max_len=3)
    nodes2, stop2 = ListNodeKit.flatten(head, max_len=3)
    assert stop2 == 3
    assert len(nodes2) == 3
    print("✓ 类调用 ListNodeKit.flatten(head, max_len=3) 提前终止")

    # 2.3 末端成环，实例调用 flatten(max_len=5)，提前达到 max_len
    print(type(kit[4]))
    assert kit[4] and not hasattr(kit[4].next._node, '_node'), f"kit[4].next = kit[0] 操作前正常"

    kit[0].val = 1234
    kit[0].next = kit[1]._node  

    assert not hasattr(kit[2].next._node, '_node'), f"kit[2].next 没有问题"

    kit[4].next = kit[0]  
    assert not hasattr(kit[4].next._node, '_node'), f"关键错误！ kit[4].next 指向了包装类！"

    nodes, stop = kit.flatten(max_len=5)
    assert stop == 0, f"由于环位置是 0 应返回 stop=5，实际 {stop}"

    assert len(nodes) == 5
    print("✓ 实例调用 flatten(max_len=5) 提前终止，stop=5")

    # ---------- 有环链表 ----------
    # 构造环：1 -> 2 -> 3 -> 4 -> 5 -> 3  (环起始节点为 3，索引为 2)
    # 注意：环起始索引基于 flatten 返回的列表顺序，从 0 开始计数
    n1 = ListNode(1)
    n2 = ListNode(2)
    n3 = ListNode(3)
    n4 = ListNode(4)
    n5 = ListNode(5)
    n1.next = n2
    n2.next = n3
    n3.next = n4
    n4.next = n5
    n5.next = n3   # 形成环，环起点是 n3 (val=3)
    cycle_head = n1
    cycle_kit = ListNodeKit(cycle_head)

    if __MIX_TEST__:
        n5.next = cycle_kit[1]   # 非法赋值，将 ListNodeKit 强行赋给 ListNode，检查是否死循环
        nodes, stop = cycle_kit.flatten(max_len=100)
        assert stop == 1, f"max_len=100 应检测到环起始索引 1，实际 {stop}, 说明混用 ListNodeKit 和 ListNode 将导致环检测失效。"

    # 3.1 实例调用 flatten()，检测到环
    nodes, stop = cycle_kit.flatten()
    assert stop == 2, f"环起始索引应为 2，实际 {stop}"
    assert len(nodes) > 2
    assert nodes[stop] is n3
    print("✓ 有环链表 flatten() 正确返回环起始索引")

    # 3.2 实例调用 flatten(max_len=1)，max_len 小于环起始索引，提前终止
    nodes, stop = cycle_kit.flatten(max_len=1)
    assert stop == 1, f"max_len=1 应返回 stop=1，实际 {stop}"
    assert len(nodes) == 1
    print("✓ 有环链表 flatten(max_len=1) 提前终止，未触发环检测")

    # 3.3 实例调用 flatten(max_len=5)，max_len 大于环起始索引，触发环检测
    nodes, stop = cycle_kit.flatten(max_len=5)
    assert stop == 2, f"max_len=5 仍应检测到环起始索引 2，实际 {stop}"
    print("✓ 有环链表 flatten(max_len=5) 仍正确检测环")

    print("========== flatten 方法测试全部通过 ==========\n")

def temp():
    n1 = ListNode(17)
    n2 = ListNode(31)
    kit1 = ListNodeKitBase(n1)
    kit2 = ListNodeKitBase(n2)
    print(1)
    print(f"kit1.val = {kit1.val}")
    print(2)
    kit1.next = kit2
    print(3)
    assert not hasattr(kit1.next._node , "_node"),"kit1合法赋值"
    print(4)
    kit1.next = kit2._node
    print(5)
    assert not hasattr(kit1.next._node , "_node"),"kit1非法赋值"
    print(6)
    kit2.next = kit1.next
    print(7)
    assert not hasattr(kit2.next._node , "_node"),"kit2非法赋值1"
    print(8)
    kit1.next._node = kit2._node
    print(9)
    assert not hasattr(kit1.next._node , "_node"),"kit1非法赋值3"
    print(10)
    print(f"kit1.val = {kit1.val}")
    print(11)
    print(f"kit2.val = {kit2.val}")
    print(12)
    kit1._node.next = kit2
    print(13)
    assert not hasattr(kit1.next._node , "_node"),"kit1非法赋值4"
    print(14)

if __name__ == "__main__":
    # temp()
    # exit(0)

    # 先运行原有基础测试
    test_listnode_kit()
    # 额外运行重复值测试（避免被随机测试掩盖）
    test_duplicate_values_no_cycle()
    # 新增迭代器测试
    test_iter()
    # 新增 flatten 专项测试
    test_flatten_methods()

    # ---------- 5. 随机压力测试（新增）----------
    print("\n7. 随机压力测试（1000 轮，最大节点数 200）")
    random.seed(42)  # 可复现
    test_random_lists()
    print("   随机压力测试通过")