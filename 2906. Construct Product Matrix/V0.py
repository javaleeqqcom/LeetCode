MOD = 12345
np
class Solution:
    def constructProductMatrix(self, grid: List[List[int]]) -> List[List[int]]:
        m,n = grid的1、2维长度
        1. 用np将 grid 转为1维 sl
        2. 定义 f(sl)=[(sl[0]*sl[1]*...*sl[i-1])%MOD for i in ...] 用 np 的 reduce 实现
        sl_sp = f(sl)
        sl_rp = f(sl[::-1])[::-1] # 逆序
        sl_p = (sl_sp * sl_rp)%MOD
        return sl_p.reshap(m,n)