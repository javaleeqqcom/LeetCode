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
DIR2X = defaultdict(int)
DIR2X.update({'L':-1,'R':1}) # U、D 会当成 0
DIR2Y = defaultdict(int)
DIR2Y.update({'U':-1,'D':1})
class Solution:
    def hasValidPath(self, grid: List[List[int]]) -> bool:
        m,n = len(grid),len(grid[0])
        # 在 右、上、下 加一格 padding 并扁平化
        flatten = np.pad(grid, pad_width=((1,1),(0,1)), constant_values= 0).flatten()
        # 将 STREET_DIRECTIONS 翻译为 flatten 可通行的索引增量
        dir_table = tuple(
            tuple(DIR2X[c]+(1+n)*DIR2Y[c] for c in s)
            for s in STREET_DIRECTIONS
        )
        # print(dir_table)
        target = (1+m)*(1+n)-2 # 终点在 flatten 的索引
        # print(m+2,n+1,target)
        def dfs(index,step):
            # print(index,step)
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
        return dfs(n+1,0) # n+1 是起点
            
