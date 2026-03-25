import numpy as np
from functools import reduce
MOD = 12345

def mod_cumprod(arr):
    res = np.ones_like(arr)
    for i,a in enumerate(arr[:-1]):
        res[i+1] = (res[i]*a) % MOD
    return res

class Solution:
    def constructProductMatrix(self, grid: List[List[int]]) -> List[List[int]]:
        m = len(grid)
        n = len(grid[0])
        L = m * n
        sl = np.array(grid).flatten()
        
        sl_sp = mod_cumprod(sl)
        sl_rp = mod_cumprod(sl[::-1])[::-1] # 逆序
        
        product = (sl_sp * sl_rp) % MOD
        return product.reshape(m, n).tolist()