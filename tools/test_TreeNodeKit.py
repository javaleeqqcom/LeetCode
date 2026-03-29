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
    assert "'1:1', '2:2', '3:3', '4:4', '5:5', '6:6'" in repr(kit)

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
    assert cycle_idx == 1, f"自环起始索引应为1，实际{cycle_idx}"
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
    assert cycle_idx == 6, f"交叉环起始索引应为6，实际{cycle_idx}"
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
    assert cycle_idx == 1
    # 注意：当 c.right 访问 b 时，b 也已经出现，但此时环已经被检测到，不会再记录
    print("多环节点检测通过")

    print("环检测全部通过")


def random_tree_node_count(max_nodes: int = 100) -> int:
    """随机生成节点数，至少1个节点"""
    return random.randint(1, max_nodes)
import random
from typing import List, Optional, Tuple, Set, Dict
from args_parser import TreeNode, TreeNodeKit


def generate_random_tree(node_count: int, create_cycle: bool = False) -> Tuple[TreeNode, Optional[Set[int]], str]:
    """
    生成随机二叉树（保证连通），节点值随机整数 0-999。
    如果 create_cycle=True，则随机选取一个非根节点，将其左或右指针指向该节点的某个祖先（包括自身），形成环。
    返回 (根节点, 环起始节点id集合, 调试日志)
    """
    log_lines = []
    if node_count <= 0:
        raise ValueError("node_count must be > 0")

    nodes = [TreeNode(random.randint(0, 999)) for _ in range(node_count)]
    root = nodes[0]
    log_lines.append(f"生成 {node_count} 个节点，根节点 id={id(root)}")

    # ---- 构建连通树（无环） ----
    # 使用随机顺序连接，保证所有节点最终都被连接到根
    # 方法：维护一个“可用父节点”列表（初始为[root]），每次从中随机选取一个父节点，
    # 将下一个未连接的节点作为其左或右孩子（随机选择左右，若该位置已被占则尝试另一侧，若均占则重新选父节点）
    remaining = nodes[1:]  # 待连接的节点
    random.shuffle(remaining)
    parent_pool = [root]  # 可用的父节点（可能重复，因为每个节点可以有两个孩子）
    idx = 0
    while remaining and parent_pool:
        cur_parent = random.choice(parent_pool)
        child = remaining.pop(0)
        # 随机决定左或右，如果位置已被占则尝试另一侧，若均被占则跳过该父节点
        placed = False
        for _ in range(2):  # 最多尝试两次（左/右）
            side = random.choice(['left', 'right'])
            if side == 'left' and cur_parent.left is None:
                cur_parent.left = child
                placed = True
                break
            elif side == 'right' and cur_parent.right is None:
                cur_parent.right = child
                placed = True
                break
        if placed:
            parent_pool.append(child)  # 新节点成为潜在父节点
            log_lines.append(f"连接节点 {id(child)} 作为 {id(cur_parent)} 的 {side} 孩子")
        else:
            # 如果 cur_parent 两个孩子都已满，将其从池中移除（可选，但保留也无害）
            # 将孩子放回队首，换一个父节点重试
            remaining.insert(0, child)
            # 可选：从父池中移除 cur_parent 以避免无限循环（但先不移除，因为可能还有其他孩子）
            # 这里简单记录一下
            log_lines.append(f"节点 {id(cur_parent)} 已满，无法放置 {id(child)}，重新选择父节点")
    if remaining:
        # 理论上不应该有剩余，因为父池足够大（每个节点最多两个孩子），但保险处理
        log_lines.append(f"警告：仍有 {len(remaining)} 个节点未连接，强制附加到根")
        for orphan in remaining:
            # 随机附加到任意已有节点（尝试左右）
            for parent in parent_pool:
                if parent.left is None:
                    parent.left = orphan
                    log_lines.append(f"强制将 {id(orphan)} 作为 {id(parent)} 的左孩子")
                    break
                elif parent.right is None:
                    parent.right = orphan
                    log_lines.append(f"强制将 {id(orphan)} 作为 {id(parent)} 的右孩子")
                    break
            else:
                log_lines.append(f"无法连接孤立节点 {id(orphan)}，树不连通")
    # ---------------------------

    if not create_cycle:
        return root, None, "\n".join(log_lines)

    # ---- 构建父节点映射（用于查找祖先） ----
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
        log_lines.append("只有根节点，无法创建环")
        return root, set(), "\n".join(log_lines)
    cycle_source = random.choice(candidates)
    # 从该节点的祖先中随机选择一个目标（确保环能被立即检测）
    target = random.choice(list(ancestors[cycle_source]))
    side = 'left' if random.choice([True, False]) else 'right'
    if side == 'left':
        cycle_source.left = target
    else:
        cycle_source.right = target
    log_lines.append(f"创建环：节点 {id(cycle_source)} 的 {side} 指向祖先 {id(target)}（值 {target.val}）")
    # 验证环是否确实可达（检查 cycle_source 是否在根的可达集合中）
    # 通过重新 BFS 检查从根是否能访问到 cycle_source
    reachable = set()
    q = [root]
    while q:
        cur = q.pop(0)
        if cur in reachable:
            continue
        reachable.add(cur)
        if cur.left:
            q.append(cur.left)
        if cur.right:
            q.append(cur.right)
    if cycle_source not in reachable:
        log_lines.append(f"警告：环起点 {id(cycle_source)} 不在根可达集合中，环无效")
    return root, {id(target)}, "\n".join(log_lines)


def validate_flatten(kit: TreeNodeKit, expected_cycle_ids: Optional[Set[int]], log: str = ""):
    """验证 flatten 结果"""
    nodes, cycle_idx = kit.flatten()
    if not expected_cycle_ids:  # None 或空集都表示无环
        if cycle_idx is not None:
            raise AssertionError(f"期望无环，但检测到环起始索引 {cycle_idx}\n生成日志：\n{log}")
    else:
        if cycle_idx is None:
            # 输出详细的调试信息
            raise AssertionError(
                f"期望有环，但 flatten 返回 None\n"
                f"期望环起始节点 id 集合: {expected_cycle_ids}\n"
                f"生成日志：\n{log}\n"
                f"树结构简图：{kit}"
            )
        nodes_dict = dict(nodes)
        start_node = nodes_dict[cycle_idx]
        if id(start_node) not in expected_cycle_ids:
            raise AssertionError(
                f"环起始节点 id {id(start_node)} 不在预期集合 {expected_cycle_ids} 中\n"
                f"生成日志：\n{log}"
            )
        
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
        root, expected_cycle_ids,log = generate_random_tree(node_count, create_cycle)
        kit = TreeNodeKit(root)

        # 验证 flatten
        validate_flatten(kit, expected_cycle_ids,log)

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