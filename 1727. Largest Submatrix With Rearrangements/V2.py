try:from args_parser import *
except:None
# 超出时间限制
# 49 / 59 个通过的测试用例

class Solution:
    def largestSubmatrix(self, matrix: List[List[int]]) -> int:
        m,n = len(matrix),len(matrix[0])

        # def count_consecutive(i,j):
        #     ans = 0
        #     for k in range(i,m):
        #         if matrix[k][j] == 1:
        #             ans += 1
        #         else:
        #             break
        #     return ans

        # 用类似前缀和的方法将 count_consecutive 的结果存储在矩阵中
        #  matrix[i][j] <- count_consecutive(i,j)
        for i in range(m-2,-1,-1): # 从倒数第2行开始向前遍历，因为倒数第一行原 matrix[m-1][j] 只能是 1,0 恰好等于 count_consecutive(m-1,j)
            for j in range(n):
                if 0!=matrix[i][j]:
                    matrix[i][j] += matrix[i+1][j] # 累积得到 count_consecutive(i,j)
                # 为 0 则不变，不算连续了，不能累积

        res = 0
        for i in range(m):
            heights = sorted(matrix[i],reverse=True)
            print(f"i={i}, hs={heights}")
            for width in range(1,n+1):
                res = max(res, width * heights[width - 1])
        return res

