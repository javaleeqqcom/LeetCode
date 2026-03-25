import numpy as np

MOD = 12345

class Solution:
    def constructProductMatrix(self, grid: List[List[int]]) -> List[List[int]]:
        m = len(grid)
        n = len(grid[0])
        L = m * n
        sl = np.array(grid).flatten()
        
        sl_sp = np.ones(L, dtype=int)
        if L > 0:
            sl_sp[1:] = np.cumprod(sl[:-1], dtype=int) % MOD
        
        rev_sl = sl[::-1]
        rev_sl_sp = np.ones(L, dtype=int)
        if L > 0:
            rev_sl_sp[1:] = np.cumprod(rev_sl[:-1], dtype=int) % MOD
        sl_rp = rev_sl_sp[::-1]

        print(sl_sp)
        print(sl_rp)
        
        product = (sl_sp * sl_rp) % MOD
        return product.reshape(m, n).tolist()