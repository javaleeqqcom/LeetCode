try:from tools.args_parser import *
except:None

from itertools import pairwise

def ch2i(ch):
    return ord(ch) - ord('A')

def dis(pos1:int , pos2:int):
    x1,y1 = divmod(pos1,6)
    x2,y2 = divmod(pos2,6)
    return abs(x1-x2)+abs(y1-y2)

class Solution:
    def minimumDistance(self, word: str) -> int:
        # 原版 dp2[i][j] 表示手指1在 i，手指2在 j 的累积最优距离。由对称性可知，dp[i][j] == dp[j][i]
        dp = [0] * 26 # dp[i] 表示为当下未移动的手，是在位置 i 的累积最优距离（上一次移动到手只能在上一个字母位置）
        for a,b in pairwise(word):
            j,k = ch2i(a),ch2i(b) # 上一次和这一次字母位置
            # 情况一：还是移动上一个手指（相当于原 dp2[i][j] + dis(j,k) -> dp2[i][k]）
            dp1 = [dp[i] + dis(j,k) for i in range(26)]
            # 情况二：移动另一个手指（则未移动到手指位置变成 j）
            for i in range(26):
                dp1[j] = min(dp1[j], dp[i] + dis(i,k)) # dp2[i][j] + dis(i,k) -> dp2[k][j]
            dp = dp1
            
            # print(f"dp: {dp}")
        return min(dp)
