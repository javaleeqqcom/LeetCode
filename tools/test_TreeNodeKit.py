# test_TreeNodeKit.py
import random
import sys
from typing import List, Optional, Tuple, Set

# 假设 args_parser 已经定义了 TreeNode 和 TreeNodeKit
from args_parser import TreeNode, TreeNodeKit


def test_basic_functionality():
    """测试基本功能：正常二叉树、属性访问、索引、flatten、repr"""
    print("\n=== 1. 基本功能测试 ===")

    # 构建树:       1
    #            /   \
    #           2     3
    #          / \   /
    #         4   5 6
    root = TreeNode(1)
    root.left = TreeNode(2)
    root.right = TreeNode(3)
    root.left.left = TreeNode(4)
    root.left.right = TreeNode(5)
    root.right.left = TreeNode(6)

    kit = TreeNodeKit(root)

    # __repr__
    print(f"repr(kit) = {repr(kit)}")
    assert "'0:1', '1:2', '2:3', '3:4', '4:5', '5:6'" in repr(kit)

    # 属性访问
    assert kit.val == 1
    assert kit.left.val == 2
    assert kit.right.val == 3
    assert kit.left.left.val == 4
    assert kit.left.right.val == 5
    assert kit.right.left.val == 6

    # 索引访问（层序索引）
    assert kit[0].val == 1
    assert kit[1].val == 2
    assert kit[2].val == 3
    assert kit[3].val == 4
    assert kit[4].val == 5
    assert kit[5].val == 6
    assert kit[6].node is None, "索引超出范围，但父节点存在，所以不应抛出异常"
    try:
        _ = kit[6*2+1]
        assert False, "应该抛出 IndexError"
    except IndexError:
        pass

    # flatten
    nodes, cycle_idx = kit.flatten()
    node_vals = [node.val for _, node in nodes]
    assert node_vals == [1, 2, 3, 4, 5, 6]
    assert cycle_idx is None

    # 空树
    empty = TreeNodeKit(None)
    assert bool(empty) is False
    try:
        empty.left
        assert False, "空树访问 left 应抛出 AttributeError"
    except AttributeError:
        pass
    try:
        empty.right
        assert False, "空树访问 right 应抛出 AttributeError"
    except AttributeError:
        pass
    assert empty[0].node is None,"空树索引应为 None"
    print("基本功能测试通过")


def test_cycle_detection():
    """测试环检测功能：自环、交叉环、多环节点"""
    print("\n=== 2. 环检测测试 ===")

    # 2.1 自环：右子节点指向自身
    root = TreeNode(1)
    root.right = root
    kit = TreeNodeKit(root)
    nodes, cycle_idx = kit.flatten()
    # 层序遍历: 根(1) -> 右子(根本身) 形成环
    assert cycle_idx == 0, f"自环起始索引应为0，实际{cycle_idx}"
    # 节点列表应该只有根节点（因为第二次遇到根时检测到环）
    assert len(nodes) == 1
    assert nodes[0][1] is root
    print("自环检测通过")

    # 2.2 交叉环：左子树指向右子树的一个节点（以堆1-index命名）
    # 构建树:   1
    #         / \
    #        2   3
    #       /   / \
    #      4   6   7
    # 让 4.right 指向 6（交叉环）
    n1 = TreeNode(1)
    n2 = TreeNode(2)
    n3 = TreeNode(3)
    n4 = TreeNode(4)
    n6 = TreeNode(6)
    n7 = TreeNode(7)
    n1.left = n2
    n1.right = n3
    n2.left = n4
    n3.left = n6
    n3.right = n7
    n4.right = n6  # 形成环，n6 同时被 n3.left 和 n4.right 引用

    kit = TreeNodeKit(n1)
    nodes, cycle_idx = kit.flatten()
    # 层序顺序: [1,2,3,4,5,6] 当遍历到 n4 时，n4.right 指向 n5，而 n5 已经出现过（在索引4）
    # 所以环起始索引应该是 n5 首次出现的索引，即 4（0-based）
    print(kit)
    assert cycle_idx == 5, f"交叉环起始索引应为5，实际{cycle_idx}"
    print("交叉环检测通过")

    # 2.3 多个环（复杂情况）：一个节点同时被多个节点指向
    a = TreeNode(10)
    b = TreeNode(20)
    c = TreeNode(30)
    a.left = b
    a.right = c
    b.left = a  # 指向根，形成环
    c.right = b  # 另一个指向 b
    kit = TreeNodeKit(a)
    nodes, cycle_idx = kit.flatten()
    # 层序：a(0), b(1), c(2) 当 b.left 访问 a 时，a 已经出现（索引0），环起始索引0
    assert cycle_idx == 0
    # 注意：当 c.right 访问 b 时，b 也已经出现，但此时环已经被检测到，不会再记录
    print("多环节点检测通过")

    print("环检测全部通过")


def random_tree_node_count(max_nodes: int = 100) -> int:
    """随机生成节点数，至少1个节点"""
    return random.randint(1, max_nodes)

import random
from typing import List, Optional, Tuple, Set, Dict
from args_parser import TreeNode, TreeNodeKit


def generate_random_tree(node_count: int, create_cycle: bool = False) -> Tuple[TreeNode, Optional[Set[int]] ,str]:
    """
    生成随机二叉树（不一定完全），节点值随机整数 0-999。
    如果 create_cycle=True，则随机选取一个非根节点，将其左或右指针指向该节点的某个祖先（包括自身），形成环。
    返回 (根节点, 环起始节点id集合) 用于验证，若无环则返回 (根节点, None) 或 (根节点, 空集) 表示无环。
    """
    log_lines = [] # 保存调试信息

    if node_count <= 0:
        raise ValueError("node_count must be > 0")

    nodes = [TreeNode(random.randint(0, 999)) for _ in range(node_count)]
    root = nodes[0]

    # 构建树（连通，无环）
    idx = 1
    queue = [root]
    while queue and idx < node_count:
        cur = queue.pop(0)
        if idx < node_count and random.random() < 0.7:
            cur.left = nodes[idx]
            queue.append(nodes[idx])
            idx += 1
        if idx < node_count and random.random() < 0.7:
            cur.right = nodes[idx]
            queue.append(nodes[idx])
            idx += 1

    if not create_cycle:
        return root, None

    # 构建父节点映射（用于查找祖先）
    parent: Dict[TreeNode, Optional[TreeNode]] = {root: None}
    queue = [root]
    while queue:
        cur = queue.pop(0)
        if cur.left:
            parent[cur.left] = cur
            queue.append(cur.left)
        if cur.right:
            parent[cur.right] = cur
            queue.append(cur.right)

    # 获取每个节点的祖先集合（包括自身）
    ancestors = {}
    for node in nodes:
        anc = set()
        cur = node
        while cur:
            anc.add(cur)
            cur = parent.get(cur)
        ancestors[node] = anc

    # 选择非根节点作为环起点
    candidates = [n for n in nodes if n is not root]
    if not candidates:
        return root, set()  # 只有根，无法创建环，返回空集表示无环
    cycle_source = random.choice(candidates)
    # 从该节点的祖先中随机选择一个目标（确保环能被立即检测）
    target = random.choice(list(ancestors[cycle_source]))
    if random.choice([True, False]):
        cycle_source.left = target
    else:
        cycle_source.right = target

    # log_lines 需要在中间适当的加入内容
    return root, {id(target)} , "\n".join(log_lines)


def validate_flatten(kit: TreeNodeKit, expected_cycle_ids: Optional[Set[int]] = None):
    """验证 flatten 结果：无环时 cycle_idx 应为 None；有环时 cycle_idx 不为 None，且起始节点 id 在 expected_cycle_ids 中"""
    nodes, cycle_idx = kit.flatten()
    if not expected_cycle_ids:  # None 或空集都表示无环
        assert cycle_idx is None, f"期望无环，但检测到环起始索引 {cycle_idx}"
    else:
        assert cycle_idx is not None, f"期望有环，但 flatten 返回 None。TreeNode如下：\n{kit}" # 后续需要补充 \n生成函数log如下：{log}
        assert 0 <= cycle_idx < len(nodes), f"环起始索引 {cycle_idx} 无效"
        start_node = nodes[cycle_idx][1]
        assert id(start_node) in expected_cycle_ids, \
            f"环起始节点 id {id(start_node)} 不在预期集合 {expected_cycle_ids} 中"

def test_random_trees():
    """随机生成大量二叉树（包括有环和无环），验证 flatten 的正确性和稳定性"""
    print("\n=== 3. 随机树压力测试（最多100节点，多轮随机）===")
    random.seed(42)  # 固定种子以便复现

    test_rounds = 200
    max_nodes = 100

    for round_i in range(test_rounds):
        node_count = random_tree_node_count(max_nodes)
        # 70% 概率生成无环树，30% 概率生成有环树
        create_cycle = random.random() < 0.3
        root, expected_cycle_ids = generate_random_tree(node_count, create_cycle)
        kit = TreeNodeKit(root)

        # 验证 flatten
        try:
            validate_flatten(kit, expected_cycle_ids)
        except AssertionError as e:
            print(f"第 {round_i+1} 轮失败: node_count={node_count}, create_cycle={create_cycle}")
            print(f"错误详情: {e}")
            # 可选：打印树结构以便调试
            # print(repr(kit))
            raise

        # 额外验证：如果无环，层序遍历节点数应该等于 node_count（因为树中所有节点都是原始节点，没有重复）
        if not create_cycle:
            nodes, _ = kit.flatten()
            # 注意：flatten 返回的节点列表可能包含 None？不会，因为 flatten 只加入非空节点
            # 但我们的随机树可能有些节点没有孩子，但所有节点都在 nodes 中
            # 由于可能有些节点未被引用？不会，生成树时保证了所有节点都被连接到根（通过队列）
            assert len(nodes) == node_count, f"节点数不匹配: flatten 得到 {len(nodes)}, 期望 {node_count}"

        # 测试索引访问（仅限于无环树，否则可能死循环）
        if not create_cycle:
            # 随机测试几个索引
            for _ in range(5):
                idx = random.randint(0, node_count - 1)
                try:
                    node_kit = kit[idx]
                    # 确保节点存在
                    assert node_kit.node is not None
                except IndexError:
                    # 可能因为树不完全，索引不存在（例如只有左子树，某些层序位置是空）
                    pass

        if (round_i + 1) % 50 == 0:
            print(f"已完成 {round_i + 1}/{test_rounds} 轮随机测试")

    print("随机树压力测试全部通过")


def test_duplicate_values():
    """测试值重复但节点不同的情况，不应触发环检测"""
    print("\n=== 4. 重复值（非环）测试 ===")
    # 创建三个不同节点但值相同
    n1 = TreeNode(100)
    n2 = TreeNode(100)
    n3 = TreeNode(100)
    n1.left = n2
    n2.left = n3
    kit = TreeNodeKit(n1)
    nodes, cycle_idx = kit.flatten()
    assert cycle_idx is None
    assert len(nodes) == 3
    assert nodes[0][1].val == 100
    assert nodes[1][1].val == 100
    assert nodes[2][1].val == 100
    # 确认节点对象不同
    assert nodes[0][1] is not nodes[1][1]
    assert nodes[1][1] is not nodes[2][1]
    print("重复值测试通过")


def test_setters_and_unwrap():
    """测试 left/right setter 以及 unwrap 行为"""
    print("\n=== 5. Setter 和 unwrap 测试 ===")
    a = TreeNode(1)
    b = TreeNode(2)
    kit_a = TreeNodeKit(a)
    kit_b = TreeNodeKit(b)

    # 通过包装类设置 left
    kit_a.left = kit_b
    assert a.left.node is b, f"a.left<{type(a.left.node)}>={a.left.val} != b.val<{type(b)}>={b.val}"

    # 通过原始节点设置
    kit_a.right = b
    assert a.right is b

    # 测试 unwrap（通过 __eq__ 间接使用）
    assert kit_a == a
    assert kit_a != b

    # 测试设置 None
    kit_a.left = None
    assert a.left is None

    print("Setter 和 unwrap 测试通过")


if __name__ == "__main__":
    test_basic_functionality()
    test_cycle_detection()
    test_duplicate_values()
    test_setters_and_unwrap()
    test_random_trees()
    print("\n🎉 所有测试通过！")