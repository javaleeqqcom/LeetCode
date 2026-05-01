import random
import string
from typing import List, Dict, Tuple, Any

# Type aliases (provided by the test framework)
_CASE = Dict[str, Any]
_BASE_TYPE = Any

def _has_cycle(grid: List[List[str]]) -> bool:
    """
    独立的环检测算法，用于生成期望输出。
    使用 DFS + parent 节点检测，正确性 O(m*n)。
    """
    if not grid or not grid[0]:
        return False
    m, n = len(grid), len(grid[0])
    visited = [[False] * n for _ in range(m)]
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    def dfs(i: int, j: int, pi: int, pj: int, ch: str) -> bool:
        if not (0 <= i < m and 0 <= j < n) or grid[i][j] != ch:
            return False
        if visited[i][j]:
            # 访问过且不是 parent，说明遇到了环
            return True
        visited[i][j] = True
        for di, dj in dirs:
            ni, nj = i + di, j + dj
            # 跳过 parent 格子
            if ni == pi and nj == pj:
                continue
            if dfs(ni, nj, i, j, ch):
                return True
        return False

    for i in range(m):
        for j in range(n):
            if not visited[i][j]:
                if dfs(i, j, -1, -1, grid[i][j]):
                    return True
    return False


def test_cases_generator(random_case_num: int, max_m: int = 20, max_n: int = 20) -> List[_CASE]:
    """
    生成测试用例。
    :param random_case_num: 随机样例的数量
    :param max_m: 网格最大行数
    :param max_n: 网格最大列数
    :return: 符合框架要求的测试用例列表
    """
    cases = []

    # ========== 1. 固定用例（覆盖边界和典型场景） ==========
    fixed_inputs = [
        # 示例 1：有环（2x2 正方形及更大）
        ([["a","a","a","a"],
          ["a","b","b","a"],
          ["a","b","b","a"],
          ["a","a","a","a"]], True),
        # 示例 2：有环（非矩形环）
        ([["c","c","c","a"],
          ["c","d","c","c"],
          ["c","c","e","c"],
          ["f","c","c","c"]], True),
        # 示例 3：无环
        ([["a","b","b"],
          ["b","z","b"],
          ["b","b","a"]], False),
        # 单单元格，不可能有环
        ([["a"]], False),
        # 1x2，不能构成环（长度至少4）
        ([["x","x"]], False),
        # 2x1
        ([["y"],["y"]], False),
        # 2x2 全相同字符 -> 有环
        ([["z","z"],["z","z"]], True),
        # 2x3 全相同字符 -> 有环 (e.g. (0,0)->(0,1)->(1,1)->(1,0))
        ([["a","a","a"],["a","a","a"]], True),
        # 3x1 全相同 -> 无环（路径长度不够）
        ([["b"],["b"],["b"]], False),
        # 不同字符的矩形，无环
        ([["a","b","c"],
          ["d","e","f"],
          ["g","h","i"]], False),
        # 大环：3x3 全相同 -> 有环
        ([["x","x","x"],
          ["x","x","x"],
          ["x","x","x"]], True),
        # 多个字符块，但无环
        ([["a","a","b"],
          ["a","b","b"],
          ["b","b","c"]], False),
    ]

    for idx, (grid, expected) in enumerate(fixed_inputs):
        cases.append({
            "input": (grid,),          # grid 作为元组的唯一元素
            "expected": expected,
            "cid": f"fixed_{idx}"
        })

    # ========== 2. 随机生成用例 ==========
    # 为了避免生成非常大的网格导致学生超时，此处 max_m / max_n 上限为 20，
    # 但可以通过函数参数灵活调整。
    letters = string.ascii_lowercase

    for i in range(random_case_num):
        # 随机决定行数和列数（至少 1，不超过上限）
        m = random.randint(1, max_m)
        n = random.randint(1, max_n)

        # 随机填充字符
        grid = [[random.choice(letters) for _ in range(n)] for _ in range(m)]

        # 利用独立检测函数获取期望输出
        expected = _has_cycle(grid)

        cases.append({
            "input": (grid,),
            "expected": expected,
            "cid": f"random_{i}"
        })

    return cases
