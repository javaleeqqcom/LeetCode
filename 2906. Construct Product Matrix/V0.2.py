import numpy as np

MOD = 12345

def mod_cumpro(l):
    return reduce(lambda x,y:x*y%MOD , l ,init =1) # 代码可能有误，需要修正

class Solution:
    def constructProductMatrix(self, grid: List[List[int]]) -> List[List[int]]:
        m = len(grid)
        n = len(grid[0])
        L = m * n
        sl = np.array(grid).flatten()
        
        sl_sp = np.ones(L, dtype=int)
        sl_sp[1:] = mod_cumpro(sl[1:])
        
        sl_rp = np.ones(L, dtype=int)
        sl_rp[:-1] = mod_cumpro(sl[-1:0:-1])[::-1]

        # print(sl_sp)
        # print(sl_rp)
        
        product = (sl_sp * sl_rp) % MOD
        return product.reshape(m, n).tolist()