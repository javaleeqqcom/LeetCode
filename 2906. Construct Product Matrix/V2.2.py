"""
执行用时分布
228
ms
击败
6.67%
"""

import numpy as np
MOD = 12345

# 定义带模乘法的 ufunc
mod_mul = np.frompyfunc(lambda x, y: (x * y) % MOD, 2, 1)

def mod_cumprod_numpy(arr):
    # accumulate 会自动迭代并应用 mod_mul
    # 注意：需指定 dtype 为 object 或预转换，否则可能因类型限制报错
    res = mod_mul.accumulate(arr, dtype=int)
    # 若需首位为 1 的效果，可配合 np.insert 或调整切片
    return np.insert(res[:-1], 0, 1) 

class Solution:
    def constructProductMatrix(self, grid: List[List[int]]) -> List[List[int]]:
        m = len(grid)
        n = len(grid[0])
        sl = np.array(grid).flatten()
        
        sl_sp = mod_cumprod_numpy(sl)
        sl_rp = mod_cumprod_numpy(sl[::-1])[::-1] # 逆序
        
        product = (sl_sp * sl_rp) % MOD
        return product.reshape(m, n).tolist()