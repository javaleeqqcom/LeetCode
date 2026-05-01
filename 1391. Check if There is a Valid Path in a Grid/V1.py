try:from tools.args_parser import *
except:None

import numpy as np
from collections import defaultdict
STREET_DIRECTIONS = (
    "", # 0 表示不可通行
    "MLR",
    "MUD",
    "MLD",
    "MRD",
    "MLU",
    "MRU"
) # M 表示本来就在这儿
DIRECTIONS2X = defaultdict(int)
DIRECTIONS2X.update({'L':-1,'R':1,'M':0})
DIRECTIONS2Y = defaultdict(int)
DIRECTIONS2Y.update({'U':-1,'D':1,'M':0})
class Solution:
    def hasValidPath(self, grid: List[List[int]]) -> bool:
        m,n = len(grid),len(grid[0])
        # 加1圈 padding 并扁平化
        flatten = np.pad(grid, pad_width=1, constant_values= 0).flatten()
        # 将 STREET_DIRECTIONS 翻译为 flatten 可通行的索引增量
        dir_table = tuple(
            tuple(DIRECTIONS2X[c]+(n+2)*DIRECTIONS2Y[c] for c in s)
            for s in STREET_DIRECTIONS
        )
        # print(dir)
        target = (1+m)*(2+n)-2
        print(m+2,n+2,target)
        def dfs(index,step):
            print(index,step)
            dir = flatten[index]
            if 0 == dir:
                return False # 已访问或不可通行
            flatten[index] = 0 # 标记为已访问（本题已走过的节点若无法通往终点，则无论从哪个方向进入都无法通往终点）
            if -step not in dir_table[dir]:
                return False # 该节点入口不匹配
            if index == target:
                return True # 到达终点
            # 遍历后继节点
            for step in dir_table[dir]:
                if dfs(index+step,step):
                    return True
            # 搜索无果
            return False
        return dfs(n+3,0)
            
