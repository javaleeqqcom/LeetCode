MOD = 12345

class Solution:
    def constructProductMatrix(self, grid: List[List[int]]) -> List[List[int]]:
        m = len(grid)
        n = len(grid[0])
        sl = [a for v in grid for a in v]
        
        # 逆序求累乘表
        sl_p = [1]*len(sl)
        for i in range(len(sl)-1,0,-1):
            sl_p[i-1] = (sl_p[i]*sl[i])%MOD
        
        # 顺序覆盖累乘表
        cu = 1
        for i,a in enumerate(sl[:-1],1):
            cu = (cu * a)%MOD
            sl_p[i] = (sl_p[i] * cu)%MOD

        return [sl_p[n*i:n*(i+1)] for i in range(m)]