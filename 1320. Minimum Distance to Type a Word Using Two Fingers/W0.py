try:from tools.args_parser import *
except:None

def ch2i(ch):
    i = ord(ch) - ord('A')
    return i

def dis(pos1:int|None , pos2:int):
    if pos1 is None: return 0
    return sum(divmod(abs(pos1-pos2),6))

def dfs(word, posA, posB):
    if not word:return 0
    cur = ch2i(word[0])
    return min(
        dis(posA,cur) + dfs(word[1:],cur,posB),
        dis(posB,cur) + dfs(word[1:],posA,cur)
    )

class Solution:
    def minimumDistance(self, word: str) -> int:
        res = dfs(word,None,None)
        return res
