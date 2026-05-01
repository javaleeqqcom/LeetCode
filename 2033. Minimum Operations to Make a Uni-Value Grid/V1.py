try: from tools.args_parser import *
except:pass

import numpy as np
class Solution:
    def minOperations(self, grid: List[List[int]], x: int) -> int:
        L = np.sort(np.array(grid,dtype=np.int32).flatten())
        # 先用同余分组，看看能不能整除
        R = L % x
        if not all(R == R[0]):
            return -1 # 非同余，必定无解
        # 否则可以整除，求中位数位置的值即可（禁用偶数个中位数取平均的情况，以确保 m %x == L%x）
        m = L[len(L)//2]
        assert all((L-m)%x == 0)
        return int(np.abs((L-m)//x).sum())