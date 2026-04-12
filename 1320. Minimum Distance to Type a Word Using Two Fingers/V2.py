try:from tools.args_parser import *
except:None

def ch2i(ch):
    i = ord(ch) - ord('A')
    return i

def dis(pos1:int|None , pos2:int):
    if pos1 is None: return 0
    x1,y1 = divmod(pos1,6)
    x2,y2 = divmod(pos2,6)
    return abs(x1-x2)+abs(y1-y2)

INF = (1<<31)-1
class Solution:
    def minimumDistance(self, word: str) -> int:
        row0 = [INF]*26
        i0 = ch2i(word[0])
        row0[i0] = 0 # 第一个不用移动手指，所以设为0
        dp0 = [row0 if i!=i0 else [0]*26  for i in range(26)]
        for ch in word:
            i_ch = ch2i(ch)
            dp1 = [[INF]*26 for _ in range(26)]
            # 第一个手指移动
            for j in range(26):
                dp1[i_ch][j] = min(dp0[i][j]+dis(i,i_ch) for i in range(26))
            # 第二个手指移动
            for i in range(26):
                dp1[i][i_ch] = min(dp0[i][j] + dis(j,i_ch) for j in range(26))
            dp0 = dp1
        return min(min(row) for row in dp0)
