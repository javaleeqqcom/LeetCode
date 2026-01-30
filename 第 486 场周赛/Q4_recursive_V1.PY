# 调试开关
__DEBUG__ = True

from math import comb

def fbinary(m, k):
    """求 0<x<2^m 中 count_1(x)==k 的个数"""
    # 11...11(2进制m个1)中选k个的可能性（特别排除k=0,x=0的情况
    return comb(m,k) if 0< k <= m else 0

class Solution:
    def nthSmallest(self, n: int, k: int) -> int:
        """返回一个整数，表示其二进制表示中 恰好 包含 k 个 1 的第 n 小的正整数。"""
        if __DEBUG__:
            print(f"n={n}, k={k}")
        if n <= 0 or k <= 0:
            return 0
        m0 = k-1
        y0 = fbinary(m0, k)
        while True:
            y1 = fbinary(m0 + 1, k)
            if y1 >= n:
                break
            m0 += 1
            y0 = y1
        if __DEBUG__:
            print(f"m={m0}, y={y0}")
        # 此时 y0 < n <= y1，意味着第 n 个数在 [2**m0, 2**(m0+1)) 中
        return (2 ** m0) + self.nthSmallest(n - y0, k - 1)

# 测试用例
if __name__ == "__main__" and __DEBUG__:
    obj = Solution()
    n = 4
    k = 2
    res = obj.nthSmallest(n, k)
    print(f"{res} = {bin(res)}")  # 输出: 9 = 0b1001