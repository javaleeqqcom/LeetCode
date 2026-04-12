try:from tools.args_parser import *
except:None

# 超出时间限制
# 24 / 55 个通过的测试用例

import heapq
from dataclasses import dataclass

def ch2xy(ch):
    i = ord(ch) - ord('A')
    return divmod(i,6)

def dis(pos1:Tuple[int,int]|None , pos2:Tuple[int,int]):
    if pos1 is None: return 0
    x1,y1 = pos1
    x2,y2 = pos2
    return abs(x1-x2)+abs(y1-y2)

@dataclass
class Qele:
    cum_dis: int
    word_i: int
    pos1: Optional[Tuple[int, int]]
    pos2: Optional[Tuple[int, int]]
    
    def __lt__(self, other):
        assert isinstance(other,Qele)
        if self.cum_dis < other.cum_dis:
            return True
        elif self.cum_dis == other.cum_dis:
            return self.word_i > other.word_i # word_i 越大返回越优
        else:
            return False
        
    def __repr__(self) -> str:
        return f"Qele{{d:{self.cum_dis},i:{self.word_i},p1:{self.pos1},p2:{self.pos2}}}"

class Solution:
    def minimumDistance(self, word: str) -> int:
        HQ = [Qele(0,0,None,None)]
        while HQ:
            cur = heapq.heappop(HQ)
            # print(cur)

            if cur.word_i == len(word):
                return cur.cum_dis

            cur_pos = ch2xy(word[cur.word_i])

            use1_dis =  cur.cum_dis + dis(cur.pos1,cur_pos)
            e1 = Qele(use1_dis , cur.word_i+1 , cur_pos, cur.pos2)
            # print(f"e1: {e1}")
            heapq.heappush( HQ, e1)
            
            use2_dis =  cur.cum_dis + dis(cur.pos2,cur_pos)
            e2 = Qele(use2_dis , cur.word_i+1 , cur.pos1, cur_pos)
            # print(f"e2: {e2}")
            heapq.heappush( HQ, e2)

        return -1
