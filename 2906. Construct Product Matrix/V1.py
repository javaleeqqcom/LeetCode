import numpy as np

MOD = 12345

def mod_cumprod(arr):
    res = [1]
    for x in arr:
        res.append(res[-1] * x % MOD)
    return res[:-1]

class Solution:
    def constructProductMatrix(self, grid: List[List[int]]) -> List[List[int]]:
        m = len(grid)
        n = len(grid[0])
        L = m * n
        sl = np.array(grid).flatten()
        
        sl_sp = np.array(mod_cumprod(sl))
        rev_sl = sl[::-1]
        rev_sl_sp = mod_cumprod(rev_sl)
        sl_rp = np.array(rev_sl_sp)[::-1]
        
        product = (sl_sp * sl_rp) % MOD
        return product.reshape(m, n).tolist()