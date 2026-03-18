try:from tools.custom_init import *
except:None
# 超出时间限制
# 49 / 59 个通过的测试用例

class Solution:
    def largestSubmatrix(self, matrix: List[List[int]]) -> int:
        m,n = len(matrix),len(matrix[0])
        def count_consecutive(i,j):
            ans = 0
            for k in range(i,m):
                if matrix[k][j] == 1:
                    ans += 1
                else:
                    break
            return ans

        res = 0
        for i in range(m):
            heights = sorted([count_consecutive(i,j) for j in range(n)],reverse=True)
            print(f"i={i}, hs={heights}")
            for width in range(1,n+1):
                res = max(res, width * heights[width - 1])
        return res

