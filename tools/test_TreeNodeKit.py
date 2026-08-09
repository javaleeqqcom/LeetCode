# test_TreeNodeKit.py
# python -m tools.test_TreeNodeKit
import os
import random
import sys
from typing import List, Optional, Tuple, Set, Any,TypeVar, Dict
import numpy as np

# 假设 args_parser 已经定义了 TreeNode 和 TreeNodeKit
from .args_parser import TreeNode, TreeNodeKit,List2TreeNode

_CHECK_REAPET_TREE = True
_CHECK_EARLY = True

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

T = TypeVar('T')
def clip_instinct_val(val_list:List[T])->Tuple[List[T],int|None]:
    """去除 val_list 的重复值，返回(去重列表,首个重复值索引(None表示无重复))"""
    seen = {}
    for i,val in enumerate(val_list):
        if val not in seen:
            seen[val] = i
        else:
            return val_list[:i],seen[val]
    return val_list,None

# ------------------ 经过Leetcode验证的专业无BUG代码 -----------------------------

class TreeTraversal:
    def __init__(self,early_stop:bool=False) -> None:
        self.rep = []
        self.early_stop = early_stop

    def preorder(self, root: Optional['TreeNode']) -> List[int]:
        ans = list()
        seen = set()
        # 返回：是否提前终止
        def dfs(node)->bool:
            if node:
                if id(node) in seen:
                    self.rep.append(node.val)
                    return self.early_stop
                seen.add(id(node))
                ans.append(node.val)
                if dfs(node.left):
                    return self.early_stop
                if dfs(node.right):
                    return self.early_stop
            return False
        dfs(root)
        return ans

    def inorder(self, root: Optional['TreeNode']) -> List[int]:
        ans = list()
        seen = set()

        def dfs(node) -> bool:
            if node:
                if id(node) in seen:
                    self.rep.append(node.val)
                    return self.early_stop
                seen.add(id(node))
                if dfs(node.left):
                    return True
                ans.append(node.val)
                if dfs(node.right):
                    return True
            return False

        dfs(root)
        return ans

    def postorder(self, root: Optional['TreeNode']) -> List[int]:
        ans = list()
        seen = set()

        def dfs(node) -> bool:
            if node:
                if id(node) in seen:
                    self.rep.append(node.val)
                    return self.early_stop
                seen.add(id(node))
                if dfs(node.left):
                    return True
                if dfs(node.right):
                    return True
                ans.append(node.val)
            return False

        dfs(root)
        return ans

    def levelFlatten(self, root: Optional['TreeNode']) -> List[List['TreeNode']]:
        """层序遍历，返回每层节点的值序列，支持早停"""
        if not root:
            return []
        result = []
        queue = [root]
        seen = set()

        while queue:
            level_nodes = []
            next_queue = []
            for node in queue:
                if id(node) in seen:
                    self.rep.append(node.val)
                    if self.early_stop:
                        next_queue = []
                        break
                    continue
                seen.add(id(node))
                level_nodes.append(node)
                next_queue.extend(list(filter(bool,(node.left, node.right))))
            
            if level_nodes:
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
    assert kit.left.left.val == 4, f"\tkit.left.left.val = {kit.left.left.val}"
    assert kit.left.right.val == 5
    assert kit.right.left.val == 6

    # 索引访问（层序遍历）
    for i in range(6):
        assert kit[i].val == i+1,f"expected kit[{i}]={i+1}, got {kit[i].val}"
        
    try:
        _ = kit[6]
        assert False, "应该抛出 IndexError"
    except IndexError as e:
        print(f"捕获到 IndexError: {e}")
    except Exception as e:
        raise Exception(e)

    print(kit.to_str(full_traversal=True))

    # 索引访问（堆索引）
    for i in range(1,7):
        assert kit.get_heap(i).val == i,f"expected kit[{i}]={i}, got {kit[i].val}"
    for i in range(7,14):
        assert kit.get_heap(i,True).raw is None,f"expected kit[{i}] is null node, got .val={kit[i].val}"
        try:
            _ = kit.get_heap(i,False)
            assert False, "应该抛出 IndexError"
        except IndexError as e:
            print(f"捕获到 IndexError: {e}")
        except Exception as e:
            raise Exception(e)

    # flatten
    nodes, it_res = kit.flatten()
    node_vals = [node.val for node in nodes]
    assert node_vals == [1, 2, 3, 4, 5, 6]
    assert not it_res.revisit_nodes, "无环链表 rep_idx 应为空"

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
    nodes, it_res = kit.flatten()

    assert 1 == len(it_res.revisit_nodes)
    rep_idx = it_res.rep_nodes_idx[0]
    # 层序遍历: 根(1) -> 右子(根本身) 形成环
    assert rep_idx == 1, f"自环起始索引应为1，实际{rep_idx}"
    # 节点列表应该只有根节点（因为第二次遇到根时检测到环）
    assert len(nodes) == 1, kit
    assert nodes[0].raw is root
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
    nodes, it_res = kit.flatten()
    repeat_vid_nodes = it_res.rep_vid_nodes
    assert 1 == len(repeat_vid_nodes), kit
    rep_idx = repeat_vid_nodes[0][0]
    # 层序顺序: [1,2,3,4,5,6] 当遍历到 n4 时，n4.right 指向 n5，而 n5 已经出现过（在索引4）
    # 所以环起始索引应该是 n5 首次出现的索引，即 4（0-based）
    print(kit)
    assert rep_idx == 6, f"交叉环起始索引应为6，实际{rep_idx}"
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
    nodes, it_res = kit.flatten()
    rep_idx = it_res.rep_nodes_idx
    assert 2 == len(rep_idx), kit.to_str(full_traversal=True)
    # 层序：a(0), b(1), c(2) 当 b.left 访问 a 时，a 已经出现（索引0），环起始索引0
    assert rep_idx[0] == 1,f"rep_idx={rep_idx},树：\n{kit}"
    assert rep_idx[1] == 2,f"rep_idx={rep_idx},树：\n{kit}"
    print("多环节点检测通过")

    # 2.4 测试 __getitem__ 在遇到环时抛出 IndexError（含环信息）
    print("\n2.4 __getitem__ 环检测错误测试")
    # 构造一个简单的环：根节点右子指向自身（自环）
    root = TreeNode(100)
    root.right = root
    kit_self_cycle = TreeNodeKit(root)
    assert kit_self_cycle.get_heap(2,allowed_null=True).raw is None
    try:
        kit_self_cycle.get_heap(3)
        assert False, f"检测到重复节点时，应当停止遍历并抛出 IndexError, kit_self_cycle:\n{kit_self_cycle}"
    except IndexError as e:
        print(f"捕获到 IndexError: {e}")
    except Exception as e:
        raise Exception(e)

    # 2.5 测试 构造交叉环（前面 2.2 中的结构）并尝试访问超出安全长度的索引
    print("\n2.5 __getitem__ 交叉环测试")
    
    val_list = [1,2,3,4,None,6,7]
    head = List2TreeNode(val_list) # n1,n2,n3,n4,  n6,n7
    nodes,_ = TreeNodeKit(head).flatten()

    # 构造 n4->n3->n6->n2->n4 的交叉环
    nodes[3].left = nodes[2] # n4 指向 n3
    nodes[4].right = nodes[1] # n6 指向 n2

    kit_cross = TreeNodeKit(head)
    val_list = list(filter(bool,val_list))
    print(kit_cross.to_str(full_traversal=True))

    # 索引访问（层序遍历）
    for i in range(6):
        assert kit_cross[i].val == val_list[i],f"expected kit_cross[{i}]={i}, got {kit_cross[i].val}"

    # 索引访问（堆索引）
    for i in val_list:
        assert kit_cross.get_heap(i).val == i,f"expected kit_cross[{i}]={i}, got {kit_cross[i].val}"
    for i in [5,9,12,14,15]:
        assert kit_cross.get_heap(i,allowed_null=True).raw is None,f"expected kit_cross[{i}] is null node, got .val={kit_cross.get_heap(i).val} ,kit_cross:\n{kit_cross}"
    for i in [8,13]: # 在层序遍历中这些索引虽然是导向重复节点，但是由于不是其祖先节点，堆索引过程中未遍历，因此不会报错
        assert kit_cross.get_heap(i,allowed_null=True).val != i
        
    try:
        for i in [10,11,16]:
            _ = kit_cross.get_heap(i)
            assert False, f"kit_cross[{i}] 应该抛出 IndexError, kit.prep:\n{kit_cross}"
    except IndexError as e:
        print(f"捕获到 IndexError: {e}")
    except Exception as e:
        raise Exception(e)
    
    print("环检测全部通过")

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
    nodes, it_res = kit.flatten()
    rep_idx = it_res.rep_nodes_idx
    assert not rep_idx , f"rep_idx = {rep_idx}"
    assert len(nodes) == 3
    assert nodes[0].val == 100
    assert nodes[1].val == 100
    assert nodes[2].val == 100
    # 确认节点对象不同
    assert nodes[0] is not nodes[1]
    assert nodes[1] is not nodes[2]
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
    assert a.left is b, f"a.left<{type(a.left)}>.val={a.left.val} != b.val<{type(b)}>={b.val}"

    # 通过原始节点设置
    kit_a.right = b
    assert a.right is b

    # 测试 unwrap
    assert TreeNodeKit.unwrap(kit_a) == a

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

def test_random_tree(seed=42, times=200, illegal_links=20, show_progress=False):
    """随机生成二叉树并随机添加非法链接，验证遍历与环检测。

    历史默认值为 10_000 棵树、每棵最多 100 次破坏（约百万轮复合
    遍历），容易被误判为死循环。默认改为适合日常回归的规模；完整
    压力测试仍可通过环境变量在脚本入口恢复。
    """
    if times <= 0 or illegal_links <= 0:
        raise ValueError("times 和 illegal_links 必须为正整数")
    print("\n=== 6. 随机树 + 非法链接测试 ===")
    random.seed(seed)
    for i in range(times):
        if show_progress:
            print(f"random test {i}", end="\r")
        left_p = random.random()
        right_p = random.random()
        root = random_tree(8, 20, left_p, right_p)   # 生成合法二叉树
        kit = TreeNodeKit(root)
        # 获取 kit 的 flatten 结果（自动环检测）
        nodes, it_res = kit.flatten(early_stop=False)
        nodes_dict = {}
        rep_nodes = [] # 初始为合法树，无需停止索引

        for j in range(illegal_links):  # 非法链接次数上限
            if not nodes_dict:
                nodes_dict:Dict[int, TreeNode] = {node.visit_index: node.raw for node in nodes if node.raw}
            # 第一次必是合法树，因此只需从第二次开始添加非法链接（重复节点或环）
            if j>0 and len(nodes)>1: # 至少要有两个节点，才增加非法链接。否则只有一个节点的情况下，只能无限形成自环，而自环已在基础测试中通过，无需再测。
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
                nodes, it_res = kit.flatten(early_stop=False)
                rep_nodes = it_res.revisit_nodes
                nodes_dict = {node.visit_index: node.raw for node in nodes if node.raw}  

            # 层序遍历（展平后 val 列表）
            traver = TreeTraversal()
            level_vals_expected = [val for level in traver.levelOrder(root) for val in level]
            level_vals_actual   = [node.val for node in nodes]
            assert level_vals_expected == level_vals_actual, f"expected :{level_vals_expected}\nlevel_actual :{level_vals_actual}\n{kit.to_str(full_traversal=True)}"

            # 测试用例检测到的重复键值
            excepted_rep_val = traver.rep[0] if traver.rep else None

            level_kit = [node.val for node in nodes]

            # 验证环起始索引与重复值一致
            if excepted_rep_val is not None:
                assert rep_nodes, "应有环但 flatten 未检测到"
                assert excepted_rep_val in set(node.val for _,node in rep_nodes), f"重复值与环起始节点值不匹配，rep.val={excepted_rep_val},but:\n{kit.to_str(full_traversal=True)}"
            else:
                assert not rep_nodes, f"无环但 flatten 报告有环, stop_idx={[node.visit_index for node in rep_nodes]}\n{kit.to_str(full_traversal=True)}"

            assert level_vals_actual == level_kit, f"层序遍历序列不一致\nstd = {level_vals_actual}\nreal = {level_kit}\n{kit.to_str(full_traversal=True)}"

            # 3. 验证 __iter__（默认层序）与 flatten 结果一致
            assert level_kit == [node.val for node in nodes], "__iter__ 与 flatten 不一致"

            if _CHECK_REAPET_TREE or 0==j: # 是否测试有重复节点的树
                # 前序/中序/后序（使用递归遍历，因为此时树无环）
                pre_expected  = TreeTraversal().preorder(root)
                pre_actual    = [node.val for node in kit.NLR_iter()]
                assert pre_expected == pre_actual, f"expected: {pre_expected}\nactual: {pre_actual}\n{kit.to_str(full_traversal=True)}"

                in_expected   = TreeTraversal().inorder(root)
                in_actual     = [node.val for node in kit.LNR_iter()]
                assert in_expected == in_actual, f"expected: {in_expected}\nin_actual = {in_actual}\n{kit.to_str(full_traversal=True)}"

                post_expected = TreeTraversal().postorder(root)
                post_actual   = [node.val for node in kit.LRN_iter()]
                assert post_expected == post_actual, f"expected: {post_expected}\nactual: {post_actual}\n{kit.to_str(full_traversal=True)}"

            if _CHECK_EARLY  and j>0: # j==0 时是完整树，没有必要测早停
                # 层序遍历
                level_expected = [val for level in TreeTraversal(True).levelOrder(root) for val in level]
                level_actual = [node.val for node in kit.layer_iter(True)]
                assert level_expected == level_actual, f"early: expected: {level_expected}\nactual: {level_actual}\n{kit.to_str(full_traversal=True)}"

                # 前序/中序/后序 早停版（使用递归遍历，因为此时树无环）
                pre_expected  = TreeTraversal(True).preorder(root)
                pre_actual    = [node.val for node in kit.NLR_iter(True)]
                assert pre_expected == pre_actual, f"early: expected: {pre_expected}\nactual: {pre_actual}\n{kit.to_str(full_traversal=True)}"

                in_expected   = TreeTraversal(True).inorder(root)
                in_actual     = [node.val for node in kit.LNR_iter(True)]
                assert in_expected == in_actual, f"early: expected: {in_expected}\nin_actual = {in_actual}\n{kit.to_str(full_traversal=True)}"

                post_expected = TreeTraversal(True).postorder(root)
                post_actual   = [node.val for node in kit.LRN_iter(True)]
                assert post_expected == post_actual, f"early: expected: {post_expected}\nactual: {post_actual}\n{kit.to_str(full_traversal=True)}"

    print(" + ".join(filter(bool,["随机树" , "非法链接" , "前序/中序/后序" if _CHECK_REAPET_TREE else "" , "早停" if _CHECK_EARLY else ""])) + "测试全部通过")

if __name__ == "__main__":
    import time
    test_basic_functionality()
    test_cycle_detection()
    test_duplicate_values()
    test_setters_and_unwrap()

    begin = time.time()
    test_random_tree(
        times=int(os.getenv("TREE_TEST_TIMES", "200")),
        illegal_links=int(os.getenv("TREE_TEST_LINKS", "20")),
        show_progress=os.getenv("TREE_TEST_PROGRESS", "0") == "1",
    )
    end = time.time()
    print(f"test_random_tree cost: {end-begin:.3f}s")

    print("\n🎉 所有测试通过！")
