try:from tools.args_parser import *
except:None

import numpy as np

class Solution:
    def hasValidPath(self, grid: List[List[int]]) -> bool:
        m,n = len(grid),len(grid[0])
        # 在 右、上、下 加一格 padding 并扁平化
        flatten = np.pad(grid, pad_width=((1,1),(0,1)), constant_values= 0).flatten()

        _n = n + 1  # 扁平化后每行的长度（包括右侧padding）
        # 直接定义每种街道类型的有效偏移量，包含0（起点特殊处理）
        dir_table = [
            set(),  # 0: 不可通行，用空集表示
            {-1, 1, 0},  # 1: 左右
            {-_n, _n, 0},  # 2: 上下
            {-1, _n, 0},  # 3: 左下
            {1, _n, 0},  # 4: 右下
            {-1, -_n, 0},  # 5: 左上
            {1, -_n, 0}  # 6: 右上
        ]
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
        return dfs(_n,0) # col_stride 是起点
