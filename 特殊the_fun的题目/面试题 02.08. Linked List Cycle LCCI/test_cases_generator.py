import random
from typing import List, Dict, Union

def test_cases_generator(random_case_num: int, max_n: int = 1000) -> List[Dict[str, Union[Dict[str, List[int]], int]]]:
    """
    生成测试用例，每个用例包含输入字典（head 链表数组，pos 环起始索引）和期望输出（pos 索引）。
    固定用例覆盖边界情况，随机用例覆盖一般情况。
    """
    res = []

    # ========== 固定边界用例 ==========
    # 空链表
    res.append({"input": {"head": [], "pos": -1}, "expected": -1})
    # 单节点无环
    res.append({"input": {"head": [1], "pos": -1}, "expected": -1})
    # 单节点自环
    res.append({"input": {"head": [1], "pos": 0}, "expected": 0})
    # 两个节点无环
    res.append({"input": {"head": [1, 2], "pos": -1}, "expected": -1})
    # 两个节点，环在开头（尾节点指向头）
    res.append({"input": {"head": [1, 2], "pos": 0}, "expected": 0})
    # 两个节点，尾节点自环
    res.append({"input": {"head": [1, 2], "pos": 1}, "expected": 1})
    # 题目示例1
    res.append({"input": {"head": [3, 2, 0, -4], "pos": 1}, "expected": 1})
    # 题目示例2
    res.append({"input": {"head": [1, 2], "pos": 0}, "expected": 0})
    # 题目示例3
    res.append({"input": {"head": [1], "pos": -1}, "expected": -1})
    # 多节点，环在中间
    res.append({"input": {"head": [1, 2, 3, 4, 5], "pos": 2}, "expected": 2})
    # 环在开头
    res.append({"input": {"head": [1, 2, 3, 4, 5], "pos": 0}, "expected": 0})
    # 环在末尾（尾节点自环）
    res.append({"input": {"head": [1, 2, 3, 4, 5], "pos": 4}, "expected": 4})
    # 所有节点值相同，环在任意位置
    res.append({"input": {"head": [7, 7, 7, 7, 7], "pos": 3}, "expected": 3})
    # 包含负数
    res.append({"input": {"head": [-5, -3, 0, 2, 8], "pos": 1}, "expected": 1})

    # ========== 随机用例 ==========
    for _ in range(random_case_num):
        # 随机生成链表长度（1 ~ max_n）
        n = random.randint(1, max_n)
        # 随机生成节点值（范围 -10^9 ~ 10^9，这里简化为 -1000 ~ 1000）
        head = [random.randint(-1000, 1000) for _ in range(n)]
        # 随机决定是否有环，概率各半
        if random.random() < 0.5:
            pos = -1
        else:
            pos = random.randint(0, n - 1)
        res.append({"input": {"head": head, "pos": pos}, "expected": pos})

    return res