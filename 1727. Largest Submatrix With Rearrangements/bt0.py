try:from tools.custom_init import *
except:None

class Solution:
    def largestSubmatrix(self, matrix: List[List[int]]) -> int:
        m,n = len(matrix),len(matrix[0])
        res = 0
        for height in range(1,m+1):
            for y in range(m-height+1):
                # print(f"y={y},h={height}")
                width = 0
                for x in range(n):
                    if all(matrix[y+i][x] == 1 for i in range(height)):
                        width += 1
                res = max(res , height*width)
        return res

