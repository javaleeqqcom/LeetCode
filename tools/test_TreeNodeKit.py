# test_TreeNodeKit.py
import random
import sys
from typing import List, Optional, Tuple, Set
import collections
import numpy as np

# 假设 args_parser 已经定义了 TreeNode 和 TreeNodeKit
from args_parser import TreeNode, TreeNodeKit,List2TreeNode

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

def clip_distinct(val_list)->List,int:
    # 返回 List：无重复最长前缀子数组
    # 其中 int 是重复的 val 值，若全集无重为None
    ...

def test_random_tree():
    """不测试 val 重复的情况，因为迭代函数与 val 完全无关。不测试有向环的情况，因为只要能检测重复值，就充分证明能检测有向环"""

    times = 10000
    for i in range(times):
        left_p = random.random() # 左子树生长概率
        right_p = random.random() # 右子树生长概率
        root = random_tree(100,10**6,left_p, right_p) # 生成随机树
        kit = TreeNodeKit(root)
        idx_nodes,stop_idx = kit.flatten()

        assert stop_idx is None, "合法二叉树的 stop_idx 应为None"

        # 先验证层序遍历的 flatten 是否正确
        level_flatten = TreeTraversal.levelFlatten(root) 
        assert level_flatten == [node.val for _,node in idx_nodes]

        # 层序遍历
        assert level_flatten == [node.val for idx,node in kit]

        # 先序遍历
        assert TreeTraversal.preorder(root)  == [node.val for idx,node in kit.NLR_iter()]

        # 中序遍历
        ...
        # 后序遍历
        ...

        # 非法树测试
        nodes_dict = dict(idx_nodes)
        reachable_idxs = list(nodes_dict.keys())
        max_nodes = len(level_flatten)
        min_nodes = max(1,int(random.random() * max_nodes)) # 至少要有 1 个，否则只剩下 root 会死循环
        while len(reachable_idxs) > min_nodes:
            # 构造非法链接
            cur = nodes_dict[random.choice(reachable_idxs)]
            tail = nodes_dict[random.choice(reachable_idxs)]
            if random.random()<=0.5:
                cur.left = tail
            else:
                cur.right = tail

            # 验证 flatten
            # 用 clip_distinct 截取最长无重复前缀作为标准输出，注意设置 max_nodes 以防有环时无限循环。
            level_flatten,duplicate_val = clip_distinct(TreeTraversal.levelFlatten(root ,max_nodes) )
            kit_cur,stop_idx = kit.flatten()

            if duplicate_val is not None:
                assert duplicate_val == nodes_dict[stop_idx].val
            else:
                assert stop_idx is None

            assert level_flatten == [node.val for _,node in kit_cur]

            # 层序遍历
            # 与 kit.?_iter 等的 val 进行比较，TreeNodeKit 的 iter 自带查重检测，首次重复节点停止
            assert level_flatten == [node.val for _,node in kit]
            
            # 先序遍历
            NLR_flatten,_ = clip_distinct(TreeTraversal.preorder(root))
            assert NLR_flatten == [node.val for _,node in kit.NLR_iter()]

            # 中序遍历
            ...
            # 后序遍历
            ...

            # 下一轮的可达节点索引集合更新（此时 kit_cur 已经通过检验）
            reachable_idxs = [idx for idx,node in kit_cur]

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