from bt0 import Solution
import random

def test_cases_generator(random_case_num: int, max_n: int = 10000):
    """
    生成测试用例，每个用例是一个元组 (head: List[int], pos: int)
    head 为链表节点值的列表，pos 为环的起始索引（-1 表示无环）
    """
    res = []

    # ----- 固定边界用例 -----
    fixed_cases = [
        ([], -1),                     # 空链表
        ([1], -1),                    # 单节点无环
        ([1], 0),                     # 单节点自环
        ([1, 2], -1),                 # 两节点无环
        ([1, 2], 0),                  # 两节点环指向头
        ([1, 2], 1),                  # 两节点环指向尾（尾自环）
        ([3, 2, 0, -4], 1),           # 示例1
        ([1, 2], 0),                  # 示例2
        ([1], -1),                     # 示例3
        ([0] * 10, 5),                 # 重复值，环在中间
        ([i for i in range(100)], 99), # 长链表，环指向尾
        ([i for i in range(100)], 0),  # 长链表，环指向头
        ([i for i in range(100)], 50), # 长链表，环指向中间
    ]
    for head_list, pos in fixed_cases:
        res.append((head_list, pos))

    # ----- 随机用例 -----
    for _ in range(random_case_num):
        # 链表长度：允许为0，均匀分布
        n = random.randint(0, max_n)
        # 生成随机值（范围任意，这里取 -10^5 ~ 10^5）
        head_list = [random.randint(-100000, 100000) for _ in range(n)]

        if n == 0:
            pos = -1
        else:
            # 以 50% 概率决定是否有环
            if random.random() < 0.5:
                pos = -1
            else:
                pos = random.randint(0, n - 1)

        res.append((head_list, pos))

    return [{"input":case,"expected":case[1]} for case in res]