try:from tools.args_parser import *
except:None

def ch2xy(ch):
    i = ord(ch) - ord('A')
    return (i // 6, i%6)

def dis(pos1:Tuple[int,int]|None , pos2:Tuple[int,int]):
    if pos1 is None: return 0
    x1,y1 = pos1
    x2,y2 = pos2
    return abs(x1-x2)+abs(y1-y2)

def dfs(word, posA, posB):
    if not word:return 0
    cur_pos = ch2xy(word[0])
    return min(
        dis(posA,cur_pos) + dfs(word[1:],cur_pos,posB),
        dis(posB,cur_pos) + dfs(word[1:],posA,cur_pos)
    )

class Solution:
    def minimumDistance(self, word: str) -> int:
        return dfs(word,None,None)
