try: from tools.args_parser import *
except:pass

import numpy as np
class Solution:
    def minOperations(self, grid: List[List[int]], x: int) -> int:
        L = np.array(grid,dtype=np.int32).flatten()
        # 先检查是否同余
        if not all((L-L[0])%x == 0):
            return -1 # 非同余，必定无解
        # 否则可以整除，求中位数即可（无需确保整除）
        m = np.median(L)
        return int(np.abs(L-m).sum()//x)