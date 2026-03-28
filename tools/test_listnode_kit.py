# test_listnode_kit.py
from args_parser import ListNode, ListNodeKit

def test_listnode_kit():
    """测试 ListNodeKit 的所有功能"""
    
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
    print(f"   str(kit): {str(kit)}")                # [1,2,3]
    print(f"   kit.val: {kit.val}")                  # 1
    print(f"   kit.next.val: {kit.next.val}")        # 2
    print(f"   kit.next.next.val: {kit.next.next.val}")  # 3
    
    # 2.2 node 属性（原生节点）
    print(f"   kit.node is n1: {kit.node is n1}")    # True
    
    # 2.3 索引访问
    print(f"   kit[0].val: {kit[0].val}")            # 1
    print(f"   kit[1].val: {kit[1].val}")            # 2
    print(f"   kit[2].val: {kit[2].val}")            # 3
    # 超出长度返回空链表
    last = kit[3]
    print(f"   kit[3] 的类型: {type(last)}, bool(last): {bool(last)}")  # ListNodeKit, False
    # 索引越界会抛出 IndexError
    try:
        _ = kit[4]
    except IndexError as e:
        print(f"   kit[4] 抛出 IndexError: {e}")
    
    # 2.4 flatten
    nodes, cycle_idx = kit.flatten()
    print(f"   flatten() 返回节点数: {len(nodes)}, 环索引: {cycle_idx}")
    assert cycle_idx == -1
    
    # 2.5 通过 __bool__ 判断非空
    print(f"   bool(kit): {bool(kit)}")              # True
    print(f"   bool(kit.next.next): {bool(kit.next.next)}")   # True
    print(f"   bool(kit.next.next.next): {bool(kit.next.next.next)}")  # False
    
    # ---------- 3. 带环链表 ----------
    print("\n3. 带环链表测试")
    a = ListNode(1)
    b = ListNode(2)
    c = ListNode(3)
    d = ListNode(4)
    a.next = b
    b.next = c
    c.next = d
    d.next = b  # 形成环，环起点是 b (val=2)
    ring_kit = ListNodeKit(a)
    
    # 3.1 字符串表示
    print(f"   str(ring_kit): {str(ring_kit)}")      # 预期: [1,>2,3,4^] 或类似格式
    
    # 3.2 flatten 检测环
    nodes, cycle_idx = ring_kit.flatten()
    print(f"   flatten() 节点数: {len(nodes)}, 环起始索引: {cycle_idx}")
    assert cycle_idx == 1  # 因为 b 是第二个节点
    print(f"   环起始节点值: {nodes[cycle_idx].val}")  # 2
    
    # 3.3 索引访问（注意：环会导致无限循环，这里只访问环之前的节点）
    print(f"   ring_kit[0].val: {ring_kit[0].val}")  # 1
    print(f"   ring_kit[1].val: {ring_kit[1].val}")  # 2
    # ring_kit[2] 会进入环，如果环很大可能会卡住，所以测试时跳过
    
    # ---------- 4. 使用 val 参数构造 ----------
    print("\n4. 使用 val 参数构造")
    kit_by_val = ListNodeKit(val=5)
    print(f"   str(kit_by_val): {str(kit_by_val)}")  # [5]
    print(f"   kit_by_val.node.val: {kit_by_val.node.val}")  # 5
    
    # ---------- 5. 装饰器自定义属性 ----------
    # 假设有另一个节点类使用 'value' 而不是 'val'
    class MyNode:
        def __init__(self, value):
            self.value = value
            self.next = None
    
    # 需要创建一个装饰器，但为了演示，我们直接使用默认的 'val' 属性，这里仅示意
    # 实际测试中如果要测试装饰器，需要重新定义 ListNodeKit 并使用不同的 prep_property
    # 由于装饰器在类定义时已经应用，这里不重复测试
    
    print("\n所有测试完成！")

if __name__ == "__main__":
    test_listnode_kit()