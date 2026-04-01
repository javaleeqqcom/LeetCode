# test_TreeNodeKit.py
import random
import sys
from typing import List, Optional, Tuple, Set
import collections
import numpy as np

# 假设 args_parser 已经定义了 TreeNode 和 TreeNodeKit
from args_parser import TreeNode, TreeNodeKit,List2TreeNode
from args_parser_tools import LayeredTraversal

def random_tree(max_depth:int ,num_nodes: int ,left_p: float, right_p: float) ->Optional[TreeNode]:
    """
    生成随机二叉树，节点值按完全二叉树索引（1-index）赋值，保证值唯一。
    - max_depth: 最大深度（根深度为1）
    - num_nodes: 最大节点数（实际节点数可能小于此值，因为概率剪枝）
    - left_p:  左子节点生成概率
    - right_p: 右子节点生成概率
    """
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

# ------------------ 辅助函数：为无环树随机添加一个环 ------------------
def add_random_cycle(root: TreeNode, node_set: Set[TreeNode]) -> Tuple[TreeNode, Set[int]]:
    """
    随机选择树中一个非根节点，将其 left 或 right 指针指向该节点的某个祖先（包括自身），形成环。
    返回 (根节点, 环起始节点id集合) 以便验证。
    """
    # 构建父节点映射
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
    for node in node_set:
        anc = set()
        cur = node
        while cur:
            anc.add(cur)
            cur = parent.get(cur)
        ancestors[node] = anc

    # 选择非根节点作为环起点
    candidates = [n for n in node_set if n is not root]
    if not candidates:
        return root, set()
    cycle_source = random.choice(candidates)
    # 从该节点的祖先中随机选择一个目标
    target = random.choice(list(ancestors[cycle_source]))
    side = 'left' if random.choice([True, False]) else 'right'
    if side == 'left':
        cycle_source.left = target
    else:
        cycle_source.right = target
    return root, {id(target)}

# ------------------ 经过Leetcode验证的专业无BUG代码 -----------------------------

class TreeTraversal:
    def __init__(self) -> None:
        self.rep = []

    def preorder(self, root: Optional['TreeNode']) -> List[int]:
        ans = list()
        seen = set()
        def dfs(node):
            if node:
                if id(node) in seen:
                    self.rep.append(node.val)
                    return
                seen.add(id(node))
                ans.append(node.val)
                dfs(node.left)
                dfs(node.right)
        dfs(root)
        return ans

    def inorder(self, root: Optional['TreeNode']) -> List[int]:
        ans = list()
        seen = set()
        def dfs(node):
            if node:
                if id(node) in seen:
                    self.rep.append(node.val)
                    return
                seen.add(id(node))
                dfs(node.left)
                ans.append(node.val)
                dfs(node.right)
        dfs(root)
        return ans

    def postorder(self, root: Optional['TreeNode']) -> List[int]:
        ans = list()
        seen = set()
        def dfs(node):
            if node:
                if id(node) in seen:
                    self.rep.append(node.val)
                    return
                seen.add(id(node))
                dfs(node.left)
                dfs(node.right)
                ans.append(node.val)
        dfs(root)
        return ans

    def levelFlatten(self, root: Optional['TreeNode']) -> List[List[TreeNode]]:
        """层序遍历，返回每层节点的值序列"""
        if not root: return []
        result = []
        queue = [root]
        seen = {id(root)}
        
        while queue:
            level_nodes = []
            next_queue = []
            for node in queue:
                level_nodes.append(node)
                for child in [node.left, node.right]:
                    if child:
                        if id(child) in seen:
                            self.rep.append(child.val)
                            continue
                        seen.add(id(child))
                        next_queue.append(child)
            result.append(level_nodes)
            queue = next_queue
        return result
    
    def levelOrder(self, root: Optional[TreeNode]) -> List[List[int]]:
        """max_nodes仅作为早停限制，不代表实际节点数"""
        return [[node.val for node in level] for level in self.levelFlatten(root)] # type: ignore
    

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
    print(kit)

    # 属性访问
    assert kit.val == 1
    assert kit.left.val == 2
    assert kit.right.val == 3
    assert kit.left.left.val == 4
    assert kit.left.right.val == 5
    assert kit.right.left.val == 6

    # 索引访问（层序遍历）
    for i in range(6):
        assert kit[i].val == i+1,f"expected kit[{i}]={i}, got {kit[i].val}"
        
    try:
        _ = kit[6]
        assert False, "应该抛出 IndexError"
    except IndexError as e:
        assert "超出" in str(e)

    # 索引访问（堆索引）
    for i in range(1,7):
        assert kit.get_heap(i).val == i,f"expected kit[{i}]={i}, got {kit[i].val}"
    for i in range(7,14):
        assert kit.get_heap(i).node is None,f"expected kit[{i}] is null node, got .val={kit[i].val}"
    try:
        _ = kit.get_heap(14)
        assert False, "应该抛出 IndexError"
    except IndexError as e:
        assert "超出" in str(e)

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
    if cycle_idx != 1:
        it = LayeredTraversal(root)
        try:
            while True:
                idx,node = next(it)
                print(f"val={node.val}, idx={idx} , queue.len = {len(it._queue)}")
        except:
            print(f"it.seen={it._seen}")


    # 层序遍历: 根(1) -> 右子(根本身) 形成环
    assert cycle_idx == 1, f"自环起始索引应为1，实际{cycle_idx}"
    # 节点列表应该只有根节点（因为第二次遇到根时检测到环）
    assert len(nodes) == 1, kit
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
    assert cycle_idx == 1,kit
    # 注意：当 c.right 访问 b 时，b 也已经出现，但此时环已经被检测到，不会再记录
    print("多环节点检测通过")

    # 2.4 测试 __getitem__ 在遇到环时抛出 IndexError（含环信息）
    print("\n2.4 __getitem__ 环检测错误测试")
    # 构造一个简单的环：根节点右子指向自身（自环）
    root = TreeNode(100)
    root.right = root
    kit_self_cycle = TreeNodeKit(root)
    assert kit_self_cycle.get_heap(2).node is None
    try:
        kit_self_cycle.get_heap(3)
        assert False, f"检测到重复节点时，应当停止遍历并抛出 IndexError, kit_self_cycle:\n{kit_self_cycle}"
    except IndexError as e:
        print(e)

    # 2.5 测试 构造交叉环（前面 2.2 中的结构）并尝试访问超出安全长度的索引
    print("\n2.5 __getitem__ 交叉环测试")
    
    val_list = [1,2,3,4,None,6,7]
    head = List2TreeNode(val_list) # n1,n2,n3,n4,  n6,n7
    nodes = dict(TreeNodeKit(head).flatten()[0])

    # 构造 n4->n3->n6->n2->n4 的交叉环
    nodes[4].left = nodes[3] # n4 指向 n3
    nodes[6].right = nodes[2] # n6 指向 n2

    kit_cross = TreeNodeKit(head)
    val_list = list(filter(bool,val_list))
    print(kit_cross)

    # 索引访问（层序遍历）
    for i in range(6):
        assert kit_cross[i].val == val_list[i],f"expected kit_cross[{i}]={i}, got {kit_cross[i].val}"

    # 索引访问（堆索引）
    for i in val_list:
        assert kit_cross.get_heap(i).val == i,f"expected kit_cross[{i}]={i}, got {kit_cross[i].val}"
    for i in [5,9,12,14,15]:
        assert kit_cross.get_heap(i).node is None,f"expected kit_cross[{i}] is null node, got .val={kit_cross.get_heap(i).val} ,kit_cross:\n{kit_cross}"
    for i in [8,13]: # 在层序遍历中这些索引虽然是导向重复节点，但是由于不是其祖先节点，堆索引过程中未遍历，因此不会报错
        assert kit_cross.get_heap(i).val != i
        
    try:
        for i in [10,11,16]:
            _ = kit_cross.get_heap(i)
            assert False, f"kit_cross[{i}] 应该抛出 IndexError, kit.prep:\n{kit_cross}"
    except IndexError as e:
        print(e)

    print("环检测全部通过")

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

def clip_distinct(val_list):
    """返回最长无重复前缀列表和第一个重复的值（若无重复则为None）"""
    seen = set()
    res = []
    dup = None
    for v in val_list:
        if v in seen:
            if dup is None:
                dup = v
        else:
            seen.add(v)
            res.append(v)
    return res, dup

def test_random_tree(seed = 42):
    """随机生成二叉树并随机添加非法链接，验证 TreeNodeKit 的遍历与环检测正确性"""
    print("\n=== 6. 随机树 + 非法链接测试 ===")
    random.seed(seed)
    times = 10000
    for i in range(times):
        print(f"random test {i}",end="\r")
        left_p = random.random()
        right_p = random.random()
        root = random_tree(10, 800, left_p, right_p)   # 生成合法二叉树
        kit = TreeNodeKit(root)
        # 获取 kit 的 flatten 结果（自动环检测）
        idx_nodes_lst, stop_idx = kit.flatten()
        nodes_dict = None

        for j in range(100): # 非法链接次数上限                # 索引 -> 节点
            if nodes_dict is None:
                nodes_dict = dict(idx_nodes_lst)    
            # 第一次必是合法树，因此只需从第二次开始添加非法链接（重复节点或环）
            if j>0 and len(idx_nodes_lst)>1: # 至少要有两个节点，才增加非法链接。否则只有一个节点的情况下，只能无限形成自环，而自环已在基础测试中通过，无需再测。
                reachable_idxs = list(nodes_dict.keys())
                # 随机选择两个可达节点（可能相同），让一个指向另一个
                assert all(idx in nodes_dict for idx in reachable_idxs), f"交集/实际: {len(set(reachable_idxs)&set(nodes_dict.keys()))}/{len(reachable_idxs)}"
                cur  = nodes_dict[random.choice(reachable_idxs)]
                tail = nodes_dict[random.choice(reachable_idxs)]
                if random.random() <= 0.5:
                    cur.left = tail
                else:
                    cur.right = tail
                    
                # 获取 kit 的 flatten 结果（自动环检测）
                idx_nodes_lst, stop_idx = kit.flatten()
                nodes_dict = dict(idx_nodes_lst)     

            # 层序遍历（展平后 val 列表）
            traver = TreeTraversal()
            level_vals_expected = [val for level in traver.levelOrder(root) for val in level]
            level_vals_actual   = [node.val for _, node in idx_nodes_lst]
            assert level_vals_expected == level_vals_actual, f"expected :{level_vals_expected}\nlevel_actual :{level_vals_actual}\n{kit}"

            # 测试用例检测到的重复键值
            excepted_rep_val = traver.rep[0] if traver.rep else None

            level_kit = [node.val for _, node in idx_nodes_lst]

            # 验证环起始索引与重复值一致
            if excepted_rep_val is not None:
                assert stop_idx is not None, "应有环但 flatten 未检测到"
                assert excepted_rep_val == nodes_dict[stop_idx].val, f"重复值与环起始节点值不匹配，rep.val={excepted_rep_val},but:\n{kit}"
            else:
                assert stop_idx is None, f"无环但 flatten 报告有环, stop_idx={stop_idx}\n{kit}"

            assert level_vals_actual == level_kit, f"层序遍历序列不一致\nstd = {level_vals_actual}\nreal = {level_kit}\n{kit}"

            # 3. 验证 __iter__（默认层序）与 flatten 结果一致
            assert level_kit == [node.val for _, node in kit], "__iter__ 与 flatten 不一致"

            # # 前序/中序/后序（使用递归遍历，因为此时树无环）
            # pre_expected  = traver.preorder(root)
            # pre_actual    = [node.val for _, node in kit.NLR_iter()]
            # assert pre_expected == pre_actual, f"expected: {pre_expected}\nactual: {pre_actual}\n{kit}"

            # in_expected   = traver.inorder(root)
            # in_actual     = [node.val for _, node in kit.LNR_iter()]
            # assert in_expected == in_actual, f"expected: {in_expected}\nin_actual = {in_actual}\n{kit}"

            # post_expected = traver.postorder(root)
            # post_actual   = [node.val for _, node in kit.LRN_iter()]
            # assert post_expected == post_actual, f"expected: {post_expected}\nactual: {post_actual}\n{kit}"

    print("随机树 + 非法链接测试全部通过")

if __name__ == "__main__":
    test_basic_functionality()
    test_cycle_detection()
    test_duplicate_values()
    test_setters_and_unwrap()
    test_random_tree()
    print("\n🎉 所有测试通过！")