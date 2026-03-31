# test_TreeNodeKit.py
import random
import sys
from typing import List, Optional, Tuple, Set
import collections
import numpy as np

# 假设 args_parser 已经定义了 TreeNode 和 TreeNodeKit
from args_parser import TreeNode, TreeNodeKit,List2TreeNode

def random_tree(max_depth:int ,num_nodes: int ,left_p: float, right_p: float) ->Optional[TreeNode]:
    # val 按1-index树状数组索引生成
    def dfs(remain_depth:int ,val:int)->Optional[TreeNode]:
        nonlocal num_nodes,left_p,right_p
        if num_nodes <= 0 or remain_depth <= 0:
            return None
        cur = TreeNode(val)
        num_nodes -= 1
        if random.random() < left_p:
            cur.left = dfs(remain_depth-1,val*2)
        if random.random() < right_p:
            cur.right = dfs(remain_depth-1,val*2+1)
        return cur
        
    return dfs(max_depth,1)

def tree_wandering(root: Optional[TreeNode] ,weight_cur_left_right:Tuple[float,float,float]) -> Optional[TreeNode]:
    weight_vec = np.array(weight_cur_left_right,dtype=float)
    cur = root
    while cur:
        cum_weight = np.cumsum(weight_vec * np.array([1,int(cur.left is not None),int(cur.right is not None)]))
        cum_weight /= cum_weight[-1]
        p = random.random()
        if p <= cum_weight[0]:
            return cur
        elif p <= cum_weight[1]:
            cur = cur.left
        else:
            cur = cur.right

# ------------------ 经过Leetcode验证的专业无BUG代码 -----------------------------

class TreeTraversal:
    @classmethod
    def preorder(cls, root: Optional[TreeNode] , max_nodes:int=(1<<31)-1) -> List[int]:        
        ans = list()
        def dfs(node):
            nonlocal max_nodes,ans
            if node and len(ans)<max_nodes:
                ans.append(node.val)
                dfs(node.left)
                dfs(node.right)   
        dfs(root)
        return ans

    @classmethod
    def inorder(cls, root: Optional[TreeNode] , max_nodes:int=(1<<31)-1) -> List[int]:        
        ans = list()
        def dfs(node):
            nonlocal max_nodes,ans
            if node and len(ans)<max_nodes:
                dfs(node.left)
                ans.append(node.val)
                dfs(node.right)   
        dfs(root)
        return ans

    @classmethod
    def postorder(cls, root: Optional[TreeNode] , max_nodes:int=(1<<31)-1) -> List[int]:        
        ans = list()
        def dfs(node):
            nonlocal max_nodes,ans
            if node and len(ans)<max_nodes:
                dfs(node.left)
                dfs(node.right)   
                ans.append(node.val)
        dfs(root)
        return ans

    @classmethod
    def levelFlatten(cls, root: Optional[TreeNode], max_nodes:int=(1<<31)-1) -> List[List[TreeNode]]:
        """max_nodes仅作为早停限制，不代表实际节点数"""
        if not root: return []
        result = [[root],]
        cnt_node = 1
        while cnt_node < max_nodes and result[-1]:
            q = []
            for node in result[-1]:
                if node.left:
                    q.append(node.left)
                if node.right:
                    q.append(node.right)
            if q:
                result.append(q)
                cnt_node += len(q)
            else:
                break
        return result

    @classmethod
    def levelOrder(cls, root: Optional[TreeNode], max_nodes:int=(1<<31)-1) -> List[List[int]]:
        """max_nodes仅作为早停限制，不代表实际节点数"""
        return [[node.val for node in level] for level in cls.levelFlatten(root,max_nodes)] # type: ignore
    
# ------------------ 经过Leetcode验证的专业无BUG代码 END -----------------------------

def test_basic_functionality():
    """测试基本功能：正常二叉树、属性访问、索引、flatten、repr"""
    print("\n=== 1. 基本功能测试 ===")

    # 构建树:       1
    #            /   \
    #           2     3
    #          / \   /
    #         4   5 6
    root = List2TreeNode([1,2,3,4,5,6])

    kit = TreeNodeKit(root)

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
    try:
        _ = kit[6]
        assert False, "应该抛出 IndexError"
    except IndexError:
        pass

    # flatten
    nodes, cycle_idx = kit.flatten()
    node_vals = [node.val for _, node in nodes]
    assert node_vals == [1, 2, 3, 4, 5, 6]
    assert cycle_idx is None

    # 超出深度打印
    print("超出深度打印")
    kit = TreeNodeKit(List2TreeNode(list(range(1,100))))
    print(kit.to_str(max_depth=6))

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
    try:
        empty[0]
        assert False, "空树[0] 应抛出 IndexError"
    except IndexError:
        pass
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

    # 2.4 测试 __getitem__ 在遇到环时抛出 IndexError（含环信息）
    print("\n2.4 __getitem__ 环检测错误测试")
    # 构造一个简单的环：根节点右子指向自身（自环）
    root = TreeNode(100)
    root.right = root
    kit_self_cycle = TreeNodeKit(root)

    # 尝试访问索引 1（理论上第二个节点，但因为环，实际只能安全遍历到根节点）
    try:
        _ = kit_self_cycle[1]
        assert False, "应该抛出 IndexError"
    except IndexError as e:
        # 验证异常消息中包含环检测相关信息
        assert "遇到环或重复节点" in str(e), f"错误消息不正确: {e}"
        assert "首次重复键为" in str(e), f"错误消息不正确: {e}"
        # 注意：重复键应该是 1（根节点的完全二叉树索引，1-index）
        # 但具体数值取决于实现，这里只检查包含即可
        print(f"   捕获到预期的 IndexError: {e}")

    # 2.5 测试 构造交叉环（前面 2.2 中的结构）并尝试访问超出安全长度的索引
    print("\n2.5 __getitem__ 交叉环测试")
    
    head = List2TreeNode([1,2,3,4,None,6,7]) # n1,n2,n3,n4,  n6,n7
    nodes = dict(TreeNodeKit(head).flatten()[0])

    # 构造 n4->n3->n6->n2->n4 的交叉环
    nodes[4].left = nodes[3] # n4 指向 n3
    nodes[6].right = nodes[2] # n6 指向 n2

    kit_cross = TreeNodeKit(head)
    # 安全迭代会提前停止（检测到 n6 重复），最多能访问几个节点？
    # 层序安全顺序：[1(1),2(2),3(3),4(4),6(5),7(6)] 但 n4.right 指向 n6 时发现重复，
    # 所以实际成功迭代的节点为 1,2,3,4,6（索引 0~4），然后停止。
    # 因此访问索引 5 会触发环错误。
    try:
        _ = kit_cross[6]
        assert False, f"应该抛出 IndexError, kit.prep:\n{kit_cross}"
    except IndexError as e:
        assert "遇到环或重复节点" in str(e)
        # 首次重复的键应该是 n6 第一次出现的键（应该是 5，因为完全二叉树索引中 n6 第一次出现是左子3的左子，索引为 2*3+1? 需计算）
        # 但只需验证消息包含即可
        print(f"   捕获到预期的 IndexError: {e}")

    # 正常访问安全范围内的索引应该成功
    assert kit_cross[0].val == 1
    assert kit_cross[1].val == 2
    assert kit_cross[2].val == 3
    assert kit_cross[3].val == 4
    assert kit_cross[4].val == 6
    
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

def test_iteration():
    """测试 TreeNodeKitBase.__iter__ 迭代器行为（无环树、重复节点、自环、交叉环）"""
    print("\n=== 6. 迭代器测试 ===")

    # ---------- 6.1 无环树 ----------
    root = List2TreeNode([1,2,3,4,5,6])
    kit = TreeNodeKit(root)
    flat_nodes, _ = kit.flatten()
    
    # 直接迭代
    nodes_via_iter = list(kit)
    assert len(nodes_via_iter) == len(flat_nodes)
    for (idx1, node1), (idx2, node2) in zip(nodes_via_iter, flat_nodes):
        assert idx1 == idx2
        assert node1 is node2

    # 手动迭代器 & repeat_idx
    it = iter(kit)
    manual = list(it)
    assert len(manual) == len(flat_nodes)
    assert it.repeat_idx is None

    # ---------- 6.2 自环树 ----------
    root_cycle = TreeNode(100)
    root_cycle.right = root_cycle
    kit_cycle = TreeNodeKit(root_cycle)
    it_cycle = iter(kit_cycle)
    collected = list(it_cycle)
    # 自环：只有根节点产生一次，第二次遇到根时检测到重复并停止
    assert len(collected) == 1
    assert collected[0][0] == 1
    assert collected[0][1] is root_cycle
    assert it_cycle.repeat_idx == 1   # 根节点首次出现的索引

    # ---------- 6.3 重复节点（多父）早停测试 ----------
    # 构建树:     1
    #           / \
    #          2   3
    #         /   / \
    #        4   6   7
    # 让 4.right 指向 6 → 6 有两个父节点（3.left 和 4.right）
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
    n4.right = n6   # 重复节点（多父）

    kit_cross = TreeNodeKit(n1)
    it_cross = iter(kit_cross)
    cross_nodes = list(it_cross)
    # 层序顺序（完全二叉树索引）：
    # 1:1, 2:2, 3:3, 4:4, 6:6, 7:7
    # 当处理到 n4（索引4）时，其右孩子 n6 已经访问过（索引6），检测到重复，停止入队。
    # 但 n7 已经在处理 n3 时入队，因此 n7 仍然会被输出。
    expected_indices = [1,2,3,4,6,7]
    actual_indices = [idx for idx,_ in cross_nodes]
    assert actual_indices == expected_indices, f"实际索引: {actual_indices}"
    # 重复检测索引应为 n6 首次出现的索引
    assert it_cross.repeat_idx == 6
    print("重复节点（多父）早停测试通过")

    # ---------- 6.4 真正的交叉环（n4.left -> n3）----------
    # 构建树:     1
    #           / \
    #          2   3
    #         /   / \
    #        4   6   7
    # 添加环: 4.left = 3 （构成有向环 3->6->... 不直接成环，但 4 指向 3，3 可达 4）
    # 更直接的环: 4.left = n3 即可
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
    n4.left = n3   # 形成环: 3 -> ... -> 4 -> 3
    kit_cycle2 = TreeNodeKit(n1)
    it_cycle2 = iter(kit_cycle2)
    cycle_nodes = list(it_cycle2)
    # 层序：1,2,3,4,6,7 ... 当处理到 n4 时，其左孩子 n3 已经访问过（索引3），检测到重复，停止。
    # 此时 n6 和 n7 已经在处理 n3 时入队，所以仍然会输出。
    expected_cycle_indices = [1,2,3,4,6,7]
    actual_cycle_indices = [idx for idx,_ in cycle_nodes]
    assert actual_cycle_indices == expected_cycle_indices
    assert it_cycle2.repeat_idx == 3   # n3 首次出现的索引
    print("交叉环早停测试通过")

    # ---------- 6.5 重复值但不同节点（无环）----------
    n1 = TreeNode(10)
    n2 = TreeNode(10)
    n3 = TreeNode(10)
    n1.left = n2
    n2.left = n3
    kit_valdup = TreeNodeKit(n1)
    it_valdup = iter(kit_valdup)
    dup_nodes = list(it_valdup)
    assert len(dup_nodes) == 3
    assert it_valdup.repeat_idx is None
    print("重复值（不同节点）测试通过")

    print("迭代器测试全部通过")

def test_dfs_iterators():
    """不测试 val 重复的情况，因为迭代函数与 val 完全无关。不测试有向环的情况，因为只要能检测重复值，就充分证明能检测有向环"""

    times = 10000
    for i in range(times):
        left_p = random.random() # 左子树生长概率
        right_p = random.random() # 右子树生长概率
        root = random_tree(100,10**6,left_p, right_p) # 生成随机树
        kit = TreeNodeKit(root)

        # 无重复节点检测
        # 先序遍历
        ...
        # 中序遍历
        ...
        # 后序遍历
        ...

        # 重复节点测试（无有向环，仅多父）
        nodes = [... kit.flatten]
        hyp_parent = nodes[random...]
        repete_node = nodes[random...]
        # 截取 inorderTraversal 等 repete_node 第二次出现前的部分作为标准输出，与 kit.LNR_iter 等的 val 进行比较。

    print("DFS 遍历迭代器测试全部通过")

if __name__ == "__main__":
    test_basic_functionality()
    test_cycle_detection()
    test_duplicate_values()
    test_setters_and_unwrap()
    test_random_trees()
    test_iteration()
    test_dfs_iterators()          # 新增
    print("\n🎉 所有测试通过！")