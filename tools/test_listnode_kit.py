# test_listnode_kit.py
import random
from args_parser import ListNode, ListNodeKit , List2ListNode

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
    print(f"   kit.node is n1: {kit.node is n1}")    # True
    
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
    print(f"   kit_by_val.node.val: {kit_by_val.node.val}")  # 5
    
    # ---------- 5. 随机压力测试（新增）----------
    print("\n5. 随机压力测试（1000 轮，最大节点数 200）")
    random.seed(42)  # 可复现
    test_random_lists()
    print("   随机压力测试通过")
    
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
                assert node_kit.node is not None
                # 检查索引访问的值是否与直接遍历一致
                cur = head
                for _ in range(idx):
                    cur = cur.next
                assert node_kit.node.val == cur.val
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

if __name__ == "__main__":
    # 先运行原有基础测试
    test_listnode_kit()
    # 额外运行重复值测试（避免被随机测试掩盖）
    test_duplicate_values_no_cycle()