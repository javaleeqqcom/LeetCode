try:from tools.args_parser import *
except:None

import numpy as np

# 预定义每种街道类型允许的方向偏移
# 索引0: 不可通行 (无有效方向)
# 索引1-6: 每种街道类型的四个可能方向 (L, R, U, D)
# 每个元组包含四个值：(left_offset, right_offset, up_offset, down_offset)
# 0表示该方向不可通行，非0值表示在扁平化数组中的索引偏移量
STREET_DIRECTIONS = np.array([
    (0, 0, 0, 0),    # 0: 不可通行
    (-1, 1, 0, 0),   # 1: 左右
    (0, 0, -1, 1),   # 2: 上下
    (-1, 0, 0, 1),   # 3: 左下
    (0, 1, 0, 1),    # 4: 右下
    (-1, 0, -1, 0),  # 5: 左上
    (0, 1, -1, 0)    # 6: 右上
],dtype=np.int32)
class Solution:
    def hasValidPath(self, grid: List[List[int]]) -> bool:
        m,n = len(grid),len(grid[0])
        # 在 右、上、下 加一格 padding 并扁平化
        flatten = np.pad(grid, pad_width=((1,1),(0,1)), constant_values= 0).flatten()

        col_stride = n + 1  # 扁平化后每行的长度（包括右侧padding）
        # 将 STREET_DIRECTIONS 翻译为 flatten 可通行的索引增量
        dir_table = list(
            map(set,np.dot(
                STREET_DIRECTIONS , 
                np.diag([1,1,col_stride,col_stride])
                ).tolist())
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
            
