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
    # 长度为 n 的链表，索引第 n 个节点返回空链表
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
    
    # ---------- 3. 带环链表（使用示例中的构造方式）----------
    print("\n3. 带环链表测试")
    # 使用 val 参数直接构造包装类，并手动设置 next 关系
    ring_link = ListNodeKit(val=1)   # 包装类，内部包含一个值为 1 的节点
    b = ListNode(2)
    c = ListNode(3)
    d = ListNode(4)
    ring_link.next = b               # 包装类的 next 映射为原生类的 next
    b.next = c
    c.next = d
    d.next = b                       # 形成环，环起点为 b (val=2)
    
    # 3.1 字符串表示（应包含环标记）
    print(f"   str(ring_link): {str(ring_link)}")    # 预期: <ListNodeKit>:[1,>,2,3,4,^]
    
    # 3.2 flatten 检测环
    nodes, cycle_idx = ring_link.flatten()
    print(f"   flatten() 节点数: {len(nodes)}, 环起始索引: {cycle_idx}")
    assert cycle_idx == 1  # 因为 b 是第二个节点（索引从 0 开始）
    print(f"   环起始节点值: {nodes[cycle_idx].val}")  # 2
    
    # 3.3 索引访问（只访问环之前的节点，避免无限循环）
    print(f"   ring_link[0].val: {ring_link[0].val}")  # 1
    print(f"   ring_link[1].val: {ring_link[1].val}")  # 2
    # 注意：ring_link[2] 会进入环，可能导致无限循环，此处跳过
    
    # ---------- 4. 使用 val 参数构造 ----------
    print("\n4. 使用 val 参数构造")
    kit_by_val = ListNodeKit(val=5)
    print(f"   str(kit_by_val): {str(kit_by_val)}")  # <ListNodeKit>:[5]
    print(f"   kit_by_val.node.val: {kit_by_val.node.val}")  # 5
    
    print("\n所有测试完成！")

if __name__ == "__main__":
    test_listnode_kit()